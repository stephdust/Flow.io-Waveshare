#include <cassert>
#include <cstdint>
#include "../../src/Modules/Network/ModbusIpServerModule/ModbusIpRegisterCodec.h"
using namespace flowio::modbus_ip;
int main(){
 RegisterRequest r{};
 const uint8_t read[]={3,0,0x34,0,2};
 assert(parseRegisterRequest(4,read,sizeof(read),r)==ParseResult::Ok);
 assert(r.unitId==4&&r.count==2&&r.address==0x34);
 uint8_t pdu[70]{};
 const uint16_t values[]={0x1234,0xabcd};
 assert(encodeRegisterResponse(r,values,pdu,sizeof(pdu))==6);
 assert(pdu[0]==3&&pdu[1]==4&&pdu[2]==0x12&&pdu[5]==0xcd);
 const uint8_t write[]={16,0,0x20,0,2,4,0x12,0x34,0xab,0xcd};
 assert(parseRegisterRequest(4,write,sizeof(write),r)==ParseResult::Ok);
 assert(r.values[0]==0x1234&&r.values[1]==0xabcd);
 assert(encodeRegisterResponse(r,nullptr,pdu,sizeof(pdu))==5);
 assert(pdu[0]==16&&pdu[4]==2);
 const uint8_t bad[]={16,0,0x20,0,2,3,0x12,0x34,0xab,0xcd};
 assert(parseRegisterRequest(4,bad,sizeof(bad),r)==ParseResult::Malformed);
 assert(parseRegisterRequest(0,read,sizeof(read),r)==ParseResult::InvalidUnit);
 const uint8_t unsupported[]={1,0,0,0,1};
 assert(parseRegisterRequest(4,unsupported,sizeof(unsupported),r)==ParseResult::UnsupportedFunction);
 assert(requestExceptionCode(ParseResult::Ok)==0);
 assert(requestExceptionCode(ParseResult::UnsupportedFunction)==1);
 assert(requestExceptionCode(ParseResult::Malformed)==3);
 assert(requestExceptionCode(ParseResult::InvalidQuantity)==3);
 assert(requestExceptionCode(ParseResult::InvalidUnit)==3);
 assert(encodeException(3,11,pdu,sizeof(pdu))==2&&pdu[0]==0x83&&pdu[1]==11);
 return 0;
}
