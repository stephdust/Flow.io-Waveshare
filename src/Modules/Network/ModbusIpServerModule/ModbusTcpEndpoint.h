#pragma once
#include <WiFi.h>
#include <new>
#include "ModbusIpTransactionBridge.h"
#include "ModbusTcpFramer.h"
namespace flowio::modbus_ip {
// Single-client cooperative TCP transport. The shared RS485 scheduler remains
// the only bus owner; this endpoint never opens or configures a UART.
class TcpEndpoint {
public:
 using ResolveProfile=bool (*)(void*,uint8_t,SerialProfile&);
 bool begin(uint16_t port) {
  if(server_)return port==port_;
  if(!port)return false;
  server_=new(std::nothrow) WiFiServer(port);
  if(!server_)return false;
  server_->begin();port_=port;return true;
 }
 void stop() {
  bridge_.cancel();client_.stop();
  if(server_){server_->stop();delete server_;server_=nullptr;}
  port_=0;framer_.reset();
 }
 void tick(const ModbusMasterService& service,ResolveProfile resolve,void* ctx,
           uint8_t ownerId,uint32_t timeoutMs) {
  if(!server_)return;
  if(!client_||!client_.connected()) {
   // A disconnected socket may evaluate false even while its RTU request
   // is still pending. Always release the previous client's transaction
   // before accepting a new client to prevent cross-client replies.
   bridge_.cancel();
   client_.stop();
   framer_.reset();
   WiFiClient incoming=server_->accept();
   if(incoming)client_=incoming;
  }
  if(!client_||!client_.connected())return;
  bridge_.tick();
  if(bridge_.state()==TransactionBridge::State::ResponseReady){
   std::size_t length=0;
   if(bridge_.takeResponse(tx_,sizeof(tx_),length)){
    if(client_.write(tx_,length)!=length){client_.stop();framer_.reset();return;}
   }
  }
  // Do not consume a second ADU while the scheduler transaction is pending.
  if(bridge_.busy())return;
  // Read only up to the end of the current ADU. Any pipelined bytes stay
  // in the socket until the current RTU transaction has completed.
  std::size_t budget=64;
  while(budget--&&client_.available()>0) {
   const int next=client_.read();
   if(next<0)break;
   const uint8_t byte=static_cast<uint8_t>(next);
   std::size_t consumed=0;
   const auto status=framer_.push(&byte,1,consumed);
   if(status==TcpFramer::FeedResult::Invalid||
      status==TcpFramer::FeedResult::Overflow){client_.stop();framer_.reset();return;}
   if(status!=TcpFramer::FeedResult::Complete)continue;
   MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
   if(decodeAdu(framer_.data(),framer_.size(),header,pdu,pduSize)){
    RegisterRequest request{};
    const auto validation=parseRegisterRequest(header.unitId,pdu,pduSize,request);
    SerialProfile profile{};
    const bool profileFound=validation==ParseResult::Ok&&resolve&&
                            resolve(ctx,header.unitId,profile);
    if(profileFound) {
     bridge_.start(framer_.data(),framer_.size(),profile,ownerId,timeoutMs,service);
    }else{
     uint8_t exception[2]{};
     const uint8_t code=validation==ParseResult::Ok?0x0a:requestExceptionCode(validation);
     const auto pduLen=encodeException(pdu[0],code,exception,sizeof(exception));
     const auto length=pduLen?encodeAdu(tx_,sizeof(tx_),header.transactionId,
                                         header.unitId,exception,pduLen):0;
     if(length)client_.write(tx_,length);
    }
   }
   framer_.reset();
   if(bridge_.busy())break;
  }
 }
 bool listening()const{return server_!=nullptr;}
private:
 WiFiServer* server_=nullptr;
 WiFiClient client_{};
 TcpFramer framer_{};
 TransactionBridge bridge_{};
 uint16_t port_=0;
 uint8_t tx_[kMaxAduBytes]{};
};
}
