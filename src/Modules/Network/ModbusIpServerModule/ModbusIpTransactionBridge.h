#pragma once
#include <cstddef>
#include <cstdint>
#include "Core/Services/IModbusMaster.h"
#include "ModbusIpSchedulerAdapter.h"
#include "ModbusMbapCodec.h"
namespace flowio::modbus_ip {
// One in-flight request per bridge instance. Network transports own sockets,
// datagram endpoints and framing; the bridge never touches the physical UART.
class TransactionBridge {
public:
 enum class State : uint8_t { Idle, Pending, ResponseReady };
 bool busy() const { return state_!=State::Idle; }
 State state() const { return state_; }
 bool start(const uint8_t* adu,std::size_t size,const SerialProfile& profile,
            uint8_t ownerId,uint32_t timeoutMs,const ModbusMasterService& service) {
  if(state_!=State::Idle||!service.submit||!service.poll)return false;
  MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
  if(!decodeAdu(adu,size,header,pdu,pduSize))return false;
  RegisterRequest request{};
  const auto parsed=parseRegisterRequest(header.unitId,pdu,pduSize,request);
  header_=header;request_=request;
  if(parsed!=ParseResult::Ok) {
   const uint8_t code=requestExceptionCode(parsed);
   return prepareException_(pdu[0],code);
  }
  ModbusRequest outgoing{};
  if(!makeSchedulerRequest(request,profile,ownerId,timeoutMs,outgoing))
   return prepareException_(request.function,3);
  uint16_t transactionId=MODBUS_TRANSACTION_INVALID;
  const ModbusResultCode result=service.submit(service.ctx,&outgoing,&transactionId);
  if(result!=MODBUS_RESULT_OK||transactionId==MODBUS_TRANSACTION_INVALID)
   return prepareException_(request.function,gatewayExceptionCode(result));
  service_=&service;transactionId_=transactionId;ownerId_=ownerId;state_=State::Pending;
  return true;
 }
 void tick() {
  if(state_!=State::Pending||!service_)return;
  ModbusResponse response{};
  const ModbusResultCode polled=service_->poll(service_->ctx,transactionId_,&response);
  if(polled==MODBUS_RESULT_NOT_READY)return;
  if(polled!=MODBUS_RESULT_OK){
   prepareException_(request_.function,gatewayExceptionCode(polled));return;
  }
  if(response.state==MODBUS_TRANSACTION_QUEUED)return;
  if(response.result==MODBUS_RESULT_EXCEPTION){
   if(response.slaveAddress!=request_.unitId||
      (response.function!=request_.function&&response.function!=(request_.function|0x80U))){
    prepareException_(request_.function,4);return;
   }
   prepareException_(request_.function,response.exceptionCode?response.exceptionCode:4);return;
  }
  if(response.state!=MODBUS_TRANSACTION_COMPLETE||response.result!=MODBUS_RESULT_OK){
   prepareException_(request_.function,gatewayExceptionCode(static_cast<ModbusResultCode>(response.result)));return;
  }
  if(response.slaveAddress!=request_.unitId||response.function!=request_.function){
   prepareException_(request_.function,4);return;
  }
  if((request_.function==3||request_.function==4)&&response.registerCount!=request_.count){
   prepareException_(request_.function,4);return;
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
  uint8_t pdu[2]{};
  const auto size=encodeException(function,code,pdu,sizeof(pdu));
  return size&&setResponse_(pdu,size);
 }
 bool setResponse_(const uint8_t* pdu,std::size_t size) {
  responseLength_=encodeAdu(response_,sizeof(response_),header_.transactionId,header_.unitId,pdu,size);
  state_=responseLength_?State::ResponseReady:State::Idle;
  return responseLength_!=0;
 }
 void reset_() {
  state_=State::Idle;service_=nullptr;transactionId_=MODBUS_TRANSACTION_INVALID;
  responseLength_=0;ownerId_=0;
 }
 State state_=State::Idle;
 MbapHeader header_{};
 RegisterRequest request_{};
 const ModbusMasterService* service_=nullptr;
 uint16_t transactionId_=MODBUS_TRANSACTION_INVALID;
 uint8_t ownerId_=0;
 uint8_t response_[kMaxAduBytes]{};
 std::size_t responseLength_=0;
};
}
