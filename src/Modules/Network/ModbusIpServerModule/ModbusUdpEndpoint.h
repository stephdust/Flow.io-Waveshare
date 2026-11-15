#pragma once
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
           uint8_t ownerId,uint32_t timeoutMs) {
  if(!listening_)return;
  bridge_.tick();
  if(bridge_.state()==TransactionBridge::State::ResponseReady) {
   std::size_t length=0;
   if(bridge_.takeResponse(tx_,sizeof(tx_),length)&&
      udp_.beginPacket(remote_,remotePort_)) {
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
  if(bridge_.busy()) {
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
                          resolve(ctx,header.unitId,profile);
  if(!profileFound) {
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
  if(bridge_.start(rx_,received,profile,ownerId,timeoutMs,service)){
   remote_=sender;remotePort_=senderPort;
  }
 }
 bool listening()const{return listening_;}
private:
 WiFiUDP udp_{};
 TransactionBridge bridge_{};
 IPAddress remote_{};
 uint16_t remotePort_=0,port_=0;
 bool listening_=false;
 uint8_t rx_[kMaxAduBytes]{};
 uint8_t tx_[kMaxAduBytes]{};
};
}
