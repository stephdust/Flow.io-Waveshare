#include <cassert>
#include <cstdint>
#include "../../src/Modules/Network/ModbusIpServerModule/ModbusMbapCodec.h"
#include "../../src/Modules/Network/ModbusIpServerModule/ModbusIpProfiles.h"
using namespace flowio::modbus_ip;
int main() {
 uint8_t adu[kMaxAduBytes]{};
 const uint8_t request[]{0x03,0x00,0x34,0x00,0x01};
 const auto size=encodeAdu(adu,sizeof(adu),0x1234,4,request,sizeof(request));
 assert(size==12);
 MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
 assert(decodeAdu(adu,size,header,pdu,pduSize));
 assert(header.transactionId==0x1234&&header.unitId==4&&pduSize==5);
 assert(!decodeAdu(adu,size-1,header,pdu,pduSize));
 adu[3]=1;assert(!decodeAdu(adu,size,header,pdu,pduSize));adu[3]=0;
 adu[5]=1;assert(!decodeAdu(adu,size,header,pdu,pduSize));adu[5]=6;
 assert(encodeAdu(adu,5,1,1,request,sizeof(request))==0);
 ProfileTable profiles;
 SerialProfile even19200{19200,1,1};
 assert(profiles.set(4,even19200));
 SerialProfile actual{};
 assert(profiles.get(4,actual));
 assert(actual.baud==19200&&actual.parity==1&&actual.stopBits==1);
 assert(!profiles.set(0,even19200));
 assert(!profiles.set(248,even19200));
 assert(!profiles.set(5,SerialProfile{9600,3,1}));
 assert(profiles.erase(4));
 assert(!profiles.get(4,actual));
 return 0;
}
