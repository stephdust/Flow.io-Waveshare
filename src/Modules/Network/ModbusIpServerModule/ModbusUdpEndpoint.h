#ifndef FLOW_MODBUS_IP_VERBOSE_TRACE
#define FLOW_MODBUS_IP_VERBOSE_TRACE 0
#endif
#if FLOW_MODBUS_IP_VERBOSE_TRACE
#define FLOW_MODBUS_IP_TRACE(...) Serial.printf(__VA_ARGS__)
#else
#define FLOW_MODBUS_IP_TRACE(...) do {} while (0)
#endif
#pragma once
#include <Arduino.h>
#include <WiFiUdp.h>
#include "ModbusIpTransactionBridge.h"
namespace flowio::modbus_ip {
// Cooperative UDP endpoint. One request at a time; the reply is always sent
// to the source IP and port of the accepted datagram.
class UdpEndpoint {
public:
 using ResolveProfile = bool (*)(void* ctx,uint8_t unitId,SerialProfile& out);
 bool begin(uint16_t port) {
  if(listening_)return port_==port;
  if(!port||!udp_.begin(port))return false;
  port_=port;listening_=true;return true;
 }
 void stop() {
  bridge_.cancel();udp_.stop();listening_=false;port_=0;
 }
 void tick(const ModbusMasterService& service,ResolveProfile resolve,void* ctx,
           uint8_t ownerId,uint32_t timeoutMs,uint8_t fixedUnitId=0,
           ReadCache* cache=nullptr,uint32_t cacheTtlMs=800,bool silentTimeout=false) {
  if(!listening_)return;
  bridge_.tick(millis());
  if(bridge_.state()==TransactionBridge::State::ResponseReady) {
   std::size_t length=0;
   if(bridge_.takeResponse(tx_,sizeof(tx_),length)&&
      udp_.beginPacket(remote_,remotePort_)) {
    FLOW_MODBUS_IP_TRACE("[Modbus UDP:%u] TX bytes=%u tid=%u unit=%u fc=%u\n",
      static_cast<unsigned>(port_),static_cast<unsigned>(length),
      static_cast<unsigned>(readBe16(tx_)),static_cast<unsigned>(tx_[6]),
      static_cast<unsigned>(tx_[7]));
    udp_.write(tx_,length);udp_.endPacket();
   }
  }
  const int available=udp_.parsePacket();
  if(available<=0)return;
  // Always drain rejected datagrams to avoid retaining stale packets.
  if(available>static_cast<int>(sizeof(rx_))) {
   while(udp_.available()>0)udp_.read();
   return;
  }
  const IPAddress sender=udp_.remoteIP();
  const uint16_t senderPort=udp_.remotePort();
  const int received=udp_.read(rx_,static_cast<int>(sizeof(rx_)));
  if(received!=available)return;
  MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
  if(!decodeAdu(rx_,received,header,pdu,pduSize))return;
  FLOW_MODBUS_IP_TRACE("[Modbus UDP:%u] RX tid=%u unit=%u fc=%u bytes=%u\n",
    static_cast<unsigned>(port_),static_cast<unsigned>(header.transactionId),
    static_cast<unsigned>(header.unitId),static_cast<unsigned>(pdu[0]),
    static_cast<unsigned>(received));
  if(bridge_.busy()) {
   if(silentTimeout)return;
   // UDP callers cannot observe a silent queue drop. Report Modbus
   // exception 0x06 (server device busy) without disturbing the current
   // RS485 transaction or its original response destination.
   uint8_t exception[2]{};
   const std::size_t pduLen=encodeException(pdu[0],0x06,exception,sizeof(exception));
   const std::size_t length=pduLen?encodeAdu(tx_,sizeof(tx_),header.transactionId,
                                               header.unitId,exception,pduLen):0;
   if(length&&udp_.beginPacket(sender,senderPort)){
    udp_.write(tx_,length);udp_.endPacket();
   }
   return;
  }
  RegisterRequest request{};
  const auto validation=parseRegisterRequest(header.unitId,pdu,pduSize,request);
  SerialProfile profile{};
  const bool profileFound=validation==ParseResult::Ok&&resolve&&
                          resolve(ctx,fixedUnitId?fixedUnitId:header.unitId,profile);
  if(!profileFound) {
   if(silentTimeout)return;
   // Invalid Modbus requests get protocol errors; unknown profiles get 0x0A.
   // Neither condition is allowed to touch the shared RS485 bus.
   uint8_t exception[2]{};
   const uint8_t code=validation==ParseResult::Ok?0x0a:requestExceptionCode(validation);
   const std::size_t pduLen=encodeException(pdu[0],code,exception,sizeof(exception));
   const std::size_t length=pduLen?encodeAdu(tx_,sizeof(tx_),header.transactionId,
                                               header.unitId,exception,pduLen):0;
   if(length&&udp_.beginPacket(sender,senderPort)){
    udp_.write(tx_,length);udp_.endPacket();
   }
   return;
  }
  if(bridge_.start(rx_,received,profile,ownerId,timeoutMs,service,fixedUnitId,
                   cache,millis(),cacheTtlMs,silentTimeout,&logEvent_,this)){
   remote_=sender;remotePort_=senderPort;
  }
 }
 bool listening()const{return listening_;}
private:
 static void logEvent_(void* ctx,TransactionBridge::Event event,uint8_t unit,uint8_t fc) {
  const auto* self=static_cast<UdpEndpoint*>(ctx);
  const char* label="";
  switch(event){
   case TransactionBridge::Event::CacheHit:label="CACHE HIT";break;
   case TransactionBridge::Event::CacheMiss:label="CACHE MISS";break;
   case TransactionBridge::Event::RtuTimeout:label="RTU TIMEOUT";break;
   case TransactionBridge::Event::ModbusException:label="MODBUS EXCEPTION";break;
  }
  FLOW_MODBUS_IP_TRACE("[Modbus %s:%u] %s unit=%u fc=%u\n",
   "UDP",static_cast<unsigned>(self->port_),
   label,static_cast<unsigned>(unit),static_cast<unsigned>(fc));
 }
 WiFiUDP udp_{};
 TransactionBridge bridge_{};
 IPAddress remote_{};
 uint16_t remotePort_=0,port_=0;
 bool listening_=false;
 uint8_t rx_[kMaxAduBytes]{};
 uint8_t tx_[kMaxAduBytes]{};
};
}
