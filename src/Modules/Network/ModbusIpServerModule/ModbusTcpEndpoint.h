#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <new>
#include "ModbusIpTransactionBridge.h"
#include "ModbusTcpFramer.h"
namespace flowio::modbus_ip {
// Up to four independent TCP clients per port. The shared RS485 scheduler
// remains the only bus owner; this endpoint never configures a UART.
class TcpEndpoint {
public:
 using ResolveProfile=bool (*)(void*,uint8_t,SerialProfile&);
 static constexpr uint8_t MaxClients=4;
 bool begin(uint16_t port) {
  if(server_)return port==port_;
  if(!port)return false;
  server_=new(std::nothrow) WiFiServer(port);
  if(!server_)return false;
  server_->begin();port_=port;return true;
 }
 void stop() {
  for(auto& slot:slots_)disconnect_(slot);
  if(server_){server_->stop();delete server_;server_=nullptr;}
  port_=0;nextSlot_=0;
 }
 void tick(const ModbusMasterService& service,ResolveProfile resolve,void* ctx,
           uint8_t ownerId,uint32_t timeoutMs,uint8_t fixedUnitId=0,
           ReadCache* cache=nullptr,uint32_t cacheTtlMs=800,bool silentTimeout=false) {
  if(!server_)return;
  // Each socket has its own frame buffer, transaction bridge and scheduler owner.
  // A pending request on one socket must not block the other clients.
  for(auto& slot:slots_) {
   if(slot.client&&!slot.client.connected())disconnect_(slot);
  }
  WiFiClient incoming=server_->accept();
  if(incoming){
   Slot* freeSlot=nullptr;
   for(auto& slot:slots_)if(!slot.client){freeSlot=&slot;break;}
   if(freeSlot)freeSlot->client=incoming;
   else incoming.stop();
  }
  const uint32_t now=millis();
  for(auto& slot:slots_){
   if(!slot.client||!slot.client.connected())continue;
   slot.bridge.tick(now);
   if(slot.bridge.state()==TransactionBridge::State::ResponseReady){
    std::size_t length=0;
    if(slot.bridge.takeResponse(slot.tx,sizeof(slot.tx),length)){
     Serial.printf("[Modbus TCP:%u] TX bytes=%u tid=%u unit=%u fc=%u\n",
       static_cast<unsigned>(port_),static_cast<unsigned>(length),
       static_cast<unsigned>(readBe16(slot.tx)),static_cast<unsigned>(slot.tx[6]),
       static_cast<unsigned>(slot.tx[7]));
     if(slot.client.write(slot.tx,length)!=length){disconnect_(slot);continue;}
    }
   }
  }
  // Rotate the first serviced client to avoid starving higher-index slots.
  for(uint8_t n=0;n<MaxClients;++n){
   const uint8_t index=static_cast<uint8_t>((nextSlot_+n)%MaxClients);
   auto& slot=slots_[index];
   if(!slot.client||!slot.client.connected()||slot.bridge.busy())continue;
   std::size_t budget=64;
   while(budget--&&slot.client.available()>0){
    const int next=slot.client.read();
    if(next<0)break;
    const uint8_t byte=static_cast<uint8_t>(next);
    std::size_t consumed=0;
    const auto status=slot.framer.push(&byte,1,consumed);
    if(status==TcpFramer::FeedResult::Invalid||
       status==TcpFramer::FeedResult::Overflow){disconnect_(slot);break;}
    if(status!=TcpFramer::FeedResult::Complete)continue;
    MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
    if(decodeAdu(slot.framer.data(),slot.framer.size(),header,pdu,pduSize)){
     Serial.printf("[Modbus TCP:%u] RX tid=%u unit=%u fc=%u bytes=%u\n",
       static_cast<unsigned>(port_),static_cast<unsigned>(header.transactionId),
       static_cast<unsigned>(header.unitId),static_cast<unsigned>(pdu[0]),
       static_cast<unsigned>(slot.framer.size()));
     RegisterRequest request{};
     const auto validation=parseRegisterRequest(header.unitId,pdu,pduSize,request);
     SerialProfile profile{};
     const bool profileFound=validation==ParseResult::Ok&&resolve&&
                             resolve(ctx,fixedUnitId?fixedUnitId:header.unitId,profile);
     if(profileFound){
      slot.bridge.start(slot.framer.data(),slot.framer.size(),profile,
                        static_cast<uint8_t>(ownerId+index),timeoutMs,service,fixedUnitId,
                        cache,now,cacheTtlMs,silentTimeout,&logEvent_,this);
     }else if(!silentTimeout){
      uint8_t exception[2]{};
      const uint8_t code=validation==ParseResult::Ok?0x0a:requestExceptionCode(validation);
      const auto pduLen=encodeException(pdu[0],code,exception,sizeof(exception));
      const auto length=pduLen?encodeAdu(slot.tx,sizeof(slot.tx),header.transactionId,
                                         header.unitId,exception,pduLen):0;
      if(length&&slot.client.write(slot.tx,length)!=length){disconnect_(slot);break;}
     }
    }
    slot.framer.reset();
    if(slot.bridge.busy())break;
   }
  }
  nextSlot_=static_cast<uint8_t>((nextSlot_+1)%MaxClients);
 }
 bool listening()const{return server_!=nullptr;}
private:
 static void logEvent_(void* ctx,TransactionBridge::Event event,uint8_t unit,uint8_t fc) {
  const auto* self=static_cast<TcpEndpoint*>(ctx);
  const char* label="";
  switch(event){
   case TransactionBridge::Event::CacheHit:label="CACHE HIT";break;
   case TransactionBridge::Event::CacheMiss:label="CACHE MISS";break;
   case TransactionBridge::Event::RtuTimeout:label="RTU TIMEOUT";break;
   case TransactionBridge::Event::ModbusException:label="MODBUS EXCEPTION";break;
  }
  Serial.printf("[Modbus %s:%u] %s unit=%u fc=%u\n",
   "TCP",static_cast<unsigned>(self->port_),
   label,static_cast<unsigned>(unit),static_cast<unsigned>(fc));
 }
 WiFiServer* server_=nullptr;
 struct Slot {
  WiFiClient client{};
  TcpFramer framer{};
  TransactionBridge bridge{};
  uint8_t tx[kMaxAduBytes]{};
 };
 static void disconnect_(Slot& slot){
  slot.bridge.cancel();slot.client.stop();slot.framer.reset();
 }
 Slot slots_[MaxClients]{};
 uint8_t nextSlot_=0;
 uint16_t port_=0;
};
}
