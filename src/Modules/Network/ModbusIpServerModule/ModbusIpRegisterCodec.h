#pragma once
#include <cstddef>
#include <cstdint>
#include "ModbusMbapCodec.h"
namespace flowio::modbus_ip {
// Supported by Flow.io's current shared RS485 master service. Other function
// codes require a deliberate extension of IModbusMaster and its RTU codec.
enum class RequestKind : uint8_t { ReadRegisters, WriteSingleRegister, WriteRegisters };
struct RegisterRequest {
 RequestKind kind=RequestKind::ReadRegisters;
 uint8_t function=0;
 uint8_t unitId=0;
 uint16_t address=0;
 uint16_t count=0;
 uint16_t values[32]{};
};
enum class ParseResult : uint8_t { Ok, Malformed, UnsupportedFunction, InvalidUnit, InvalidQuantity };
inline ParseResult parseRegisterRequest(uint8_t unitId,const uint8_t* pdu,std::size_t size,RegisterRequest& out) {
 if(unitId<1||unitId>247)return ParseResult::InvalidUnit;
 if(!pdu||size<1)return ParseResult::Malformed;
 const uint8_t fc=pdu[0];
 if(fc!=3&&fc!=4&&fc!=6&&fc!=16)return ParseResult::UnsupportedFunction;
 if(size<5)return ParseResult::Malformed;
 RegisterRequest parsed{};parsed.function=fc;parsed.unitId=unitId;
 parsed.address=readBe16(pdu+1);
 if(fc==6){
  if(size!=5)return ParseResult::Malformed;
  parsed.kind=RequestKind::WriteSingleRegister;parsed.count=1;parsed.values[0]=readBe16(pdu+3);
 } else {
  if(size<5)return ParseResult::Malformed;
  parsed.count=readBe16(pdu+3);
  if(parsed.count==0||parsed.count>32||static_cast<uint32_t>(parsed.address)+parsed.count>65536U)return ParseResult::InvalidQuantity;
  if(fc==16){
   if(size!=static_cast<std::size_t>(6+2*parsed.count)||pdu[5]!=2*parsed.count)return ParseResult::Malformed;
   parsed.kind=RequestKind::WriteRegisters;
   for(uint16_t i=0;i<parsed.count;++i)parsed.values[i]=readBe16(pdu+6+2*i);
  }else{
   if(size!=5)return ParseResult::Malformed;
   parsed.kind=RequestKind::ReadRegisters;
  }
 }
 out=parsed;return ParseResult::Ok;
}
// Validate the Modbus function before looking up the RTU serial profile.
// A request with an unsupported function is invalid regardless of whether
// the target device has been registered in Flow.io.
inline uint8_t requestExceptionCode(ParseResult result) {
 switch(result) {
  case ParseResult::Ok:return 0;
  case ParseResult::UnsupportedFunction:return 1; // Illegal function
  case ParseResult::Malformed:
  case ParseResult::InvalidUnit:
  case ParseResult::InvalidQuantity:return 3; // Illegal data value
 }
 return 3;
}
inline std::size_t encodeRegisterResponse(const RegisterRequest& req,const uint16_t* values,
 uint8_t* pdu,std::size_t capacity) {
 if(!pdu||req.count==0||req.count>32)return 0;
 if(req.function==3||req.function==4){
  const std::size_t size=2U+2U*req.count;
  if(!values||capacity<size)return 0;
  pdu[0]=req.function;pdu[1]=static_cast<uint8_t>(2U*req.count);
  for(uint16_t i=0;i<req.count;++i)writeBe16(pdu+2+2*i,values[i]);
  return size;
 }
 if(capacity<5)return 0;
 pdu[0]=req.function;writeBe16(pdu+1,req.address);
 if(req.function==6)writeBe16(pdu+3,req.values[0]);
 else if(req.function==16)writeBe16(pdu+3,req.count);
 else return 0;
 return 5;
}
inline std::size_t encodeException(uint8_t function,uint8_t exceptionCode,uint8_t* pdu,std::size_t capacity){
 if(!pdu||capacity<2||function==0||function>0x7f)return 0;
 pdu[0]=static_cast<uint8_t>(function|0x80U);pdu[1]=exceptionCode;return 2;
}
}
