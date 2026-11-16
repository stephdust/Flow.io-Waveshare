#pragma once
#include <cstddef>
#include <cstdint>
#include <Arduino.h>
#include "Core/Services/IModbusMaster.h"
#include "ModbusIpSchedulerAdapter.h"
#include "ModbusIpReadCache.h"
#include "ModbusMbapCodec.h"
namespace flowio::modbus_ip {
// One in-flight request per bridge instance. Network transports own sockets,
// datagram endpoints and framing; the bridge never touches the physical UART.
class TransactionBridge {
public:
 enum class Event : uint8_t { CacheHit,CacheMiss,RtuTimeout,ModbusException };
 using EventCallback=void (*)(void*,Event,uint8_t,uint8_t);
 enum class State : uint8_t { Idle, Pending, ResponseReady };
 bool busy() const { return state_!=State::Idle; }
 State state() const { return state_; }
 bool start(const uint8_t* adu,std::size_t size,const SerialProfile& profile,
            uint8_t ownerId,uint32_t timeoutMs,const ModbusMasterService& service,
            uint8_t fixedUnitId=0,ReadCache* cache=nullptr,uint32_t nowMs=0,
            uint32_t cacheTtlMs=800,bool silentTimeout=false,
            EventCallback onEvent=nullptr,void* eventCtx=nullptr) {
  if(state_!=State::Idle||!service.submit||!service.poll)return false;
  MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
  if(!decodeAdu(adu,size,header,pdu,pduSize))return false;
  RegisterRequest request{};
  const auto parsed=parseRegisterRequest(header.unitId,pdu,pduSize,request);
  header_=header;
  if(fixedUnitId>=1&&fixedUnitId<=247)request.unitId=fixedUnitId;
  request_=request;
  Serial.printf("[Modbus IP] RX unit=%u fc=%u addr=%u count=%u timeout=%lu ms\n",
    static_cast<unsigned>(request.unitId),static_cast<unsigned>(request.function),
    static_cast<unsigned>(request.address),static_cast<unsigned>(request.count),
    static_cast<unsigned long>(timeoutMs));
  cache_=cache;profile_=profile;cacheTtlMs_=cacheTtlMs;
  silentTimeout_=silentTimeout;nowMs_=nowMs;
  onEvent_=onEvent;eventCtx_=eventCtx;
  if(parsed!=ParseResult::Ok) {
   if(silentTimeout_){reset_();return true;}
   const uint8_t code=requestExceptionCode(parsed);
   return prepareException_(pdu[0],code);
  }
  if(cache_&&request.kind==RequestKind::ReadRegisters&&request.count>ReadCache::MaxRegisters)
   Serial.printf("[Modbus IP] CACHE BYPASS count=%u limit=%u\n",
     static_cast<unsigned>(request.count),static_cast<unsigned>(ReadCache::MaxRegisters));
  if(cache_&&request.kind==RequestKind::ReadRegisters&&request.count<=ReadCache::MaxRegisters){
   uint16_t cached[32]{};
   if(cache_->lookup(request,profile,nowMs,cacheTtlMs_,cached)){
    emit_(Event::CacheHit);
    uint8_t pduOut[2U+2U*MODBUS_MAX_REGISTERS_PER_REQUEST]{};
    const auto n=encodeRegisterResponse(request,cached,pduOut,sizeof(pduOut));
    return n&&setResponse_(pduOut,n);
   }
   emit_(Event::CacheMiss);
  }
  // A write makes prior reads potentially stale even before its RTU acknowledgement.
  if(cache_&&request.kind!=RequestKind::ReadRegisters)cache_->invalidate(request.unitId);
  ModbusRequest outgoing{};
  if(!makeSchedulerRequest(request,profile,ownerId,timeoutMs,outgoing)) {
   if(silentTimeout_){reset_();return true;}
   return prepareException_(request.function,3);
  }
  uint16_t transactionId=MODBUS_TRANSACTION_INVALID;
  const ModbusResultCode result=service.submit(service.ctx,&outgoing,&transactionId);
  if(result!=MODBUS_RESULT_OK||transactionId==MODBUS_TRANSACTION_INVALID){
   if(result==MODBUS_RESULT_TIMEOUT||result==MODBUS_RESULT_EXPIRED)emit_(Event::RtuTimeout);
   if(silentTimeout_){
    reset_();return true;
   }
   return prepareException_(request.function,gatewayExceptionCode(result));
  }
  service_=&service;transactionId_=transactionId;ownerId_=ownerId;state_=State::Pending;
  submittedAtMs_=nowMs;
  Serial.printf("[Modbus IP] SCHEDULER ACCEPTED tx=%u unit=%u addr=%u count=%u\n",
    static_cast<unsigned>(transactionId_),static_cast<unsigned>(request_.unitId),
    static_cast<unsigned>(request_.address),static_cast<unsigned>(request_.count));
  return true;
 }
 void tick(uint32_t nowMs=0) {
  nowMs_=nowMs;
  if(state_!=State::Pending||!service_)return;
  ModbusResponse response{};
  const ModbusResultCode polled=service_->poll(service_->ctx,transactionId_,&response);
  if(polled==MODBUS_RESULT_NOT_READY)return;
  if(polled!=MODBUS_RESULT_OK){
   Serial.printf("[Modbus IP] SCHEDULER ERROR tx=%u code=%u elapsed=%lu ms\n",
     static_cast<unsigned>(transactionId_),static_cast<unsigned>(polled),
     static_cast<unsigned long>(nowMs-submittedAtMs_));
   if(polled==MODBUS_RESULT_TIMEOUT||polled==MODBUS_RESULT_EXPIRED)emit_(Event::RtuTimeout);
   if(silentTimeout_){
    reset_();return;
   }
   prepareException_(request_.function,gatewayExceptionCode(polled));return;
  }
  if(response.state==MODBUS_TRANSACTION_QUEUED)return;
  Serial.printf("[Modbus IP] SCHEDULER RESULT tx=%u state=%u code=%u elapsed=%lu ms\n",
    static_cast<unsigned>(transactionId_),static_cast<unsigned>(response.state),
    static_cast<unsigned>(response.result),static_cast<unsigned long>(nowMs-submittedAtMs_));
  if(response.result==MODBUS_RESULT_EXCEPTION){
   if(silentTimeout_){reset_();return;}
   if(response.slaveAddress!=request_.unitId||
      (response.function!=request_.function&&response.function!=(request_.function|0x80U))){
    prepareException_(request_.function,4);return;
   }
   prepareException_(request_.function,response.exceptionCode?response.exceptionCode:4);return;
  }
  if(response.state!=MODBUS_TRANSACTION_COMPLETE||response.result!=MODBUS_RESULT_OK){
   if(response.result==MODBUS_RESULT_TIMEOUT||response.result==MODBUS_RESULT_EXPIRED)emit_(Event::RtuTimeout);
   if(silentTimeout_){
    reset_();return;
   }
   prepareException_(request_.function,gatewayExceptionCode(static_cast<ModbusResultCode>(response.result)));return;
  }
  if(response.slaveAddress!=request_.unitId||response.function!=request_.function||
     response.registerAddress!=request_.address){
   Serial.printf("[Modbus IP] INVALID RESPONSE tx=%u unit=%u/%u fc=%u/%u addr=%u/%u\n",
     static_cast<unsigned>(transactionId_),static_cast<unsigned>(response.slaveAddress),
     static_cast<unsigned>(request_.unitId),static_cast<unsigned>(response.function),
     static_cast<unsigned>(request_.function),static_cast<unsigned>(response.registerAddress),
     static_cast<unsigned>(request_.address));
   prepareException_(request_.function,4);return;
  }
  if((request_.function==3||request_.function==4)&&response.registerCount!=request_.count){
   Serial.printf("[Modbus IP] INVALID COUNT tx=%u got=%u expected=%u\n",
     static_cast<unsigned>(transactionId_),static_cast<unsigned>(response.registerCount),
     static_cast<unsigned>(request_.count));
   prepareException_(request_.function,4);return;
  }
  if(cache_){
   if(request_.kind==RequestKind::ReadRegisters&&request_.count<=ReadCache::MaxRegisters)
    cache_->store(request_,profile_,nowMs_,response.values);
   else cache_->invalidate(request_.unitId);
  }
  uint8_t pdu[2U+2U*MODBUS_MAX_REGISTERS_PER_REQUEST]{};
  const std::size_t pduLength=encodeRegisterResponse(request_,response.values,pdu,sizeof(pdu));
  if(!pduLength||!setResponse_(pdu,pduLength))prepareException_(request_.function,4);
 }
 bool takeResponse(uint8_t* out,std::size_t capacity,std::size_t& size) {
  if(state_!=State::ResponseReady||!out||capacity<responseLength_)return false;
  for(std::size_t i=0;i<responseLength_;++i)out[i]=response_[i];
  size=responseLength_;reset_();return true;
 }
 void cancel() {
  if(state_==State::Pending&&service_&&service_->cancelOwner)
   service_->cancelOwner(service_->ctx,ownerId_);
  reset_();
 }
private:
 bool prepareException_(uint8_t function,uint8_t code) {
  if(silentTimeout_){
   Serial.printf("[Modbus IP] SILENT DROP tx=%u unit=%u fc=%u code=%u\n",
     static_cast<unsigned>(transactionId_),static_cast<unsigned>(request_.unitId),
     static_cast<unsigned>(function),static_cast<unsigned>(code));
   reset_();return true;
  }
  emit_(Event::ModbusException);
  uint8_t pdu[2]{};
  const auto size=encodeException(function,code,pdu,sizeof(pdu));
  return size&&setResponse_(pdu,size);
 }
 bool setResponse_(const uint8_t* pdu,std::size_t size) {
  responseLength_=encodeAdu(response_,sizeof(response_),header_.transactionId,header_.unitId,pdu,size);
  state_=responseLength_?State::ResponseReady:State::Idle;
  return responseLength_!=0;
 }
 void emit_(Event event){if(onEvent_)onEvent_(eventCtx_,event,request_.unitId,request_.function);}
 void reset_() {
  state_=State::Idle;service_=nullptr;transactionId_=MODBUS_TRANSACTION_INVALID;
  responseLength_=0;ownerId_=0;cache_=nullptr;onEvent_=nullptr;eventCtx_=nullptr;
 }
 State state_=State::Idle;
 MbapHeader header_{};
 RegisterRequest request_{};
 ReadCache* cache_=nullptr;
 SerialProfile profile_{};
 uint32_t cacheTtlMs_=800;
 uint32_t nowMs_=0;
 uint32_t submittedAtMs_=0;
 bool silentTimeout_=false;
 EventCallback onEvent_=nullptr;
 void* eventCtx_=nullptr;
 const ModbusMasterService* service_=nullptr;
 uint16_t transactionId_=MODBUS_TRANSACTION_INVALID;
 uint8_t ownerId_=0;
 uint8_t response_[kMaxAduBytes]{};
 std::size_t responseLength_=0;
};
}
