#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace flowio::modbus_ip {
constexpr std::size_t kMbapHeaderBytes=7;
constexpr std::size_t kMaxPduBytes=253;
constexpr std::size_t kMaxAduBytes=kMbapHeaderBytes+kMaxPduBytes;
struct MbapHeader { uint16_t transactionId=0; uint16_t protocolId=0; uint16_t length=0; uint8_t unitId=0; };
inline uint16_t readBe16(const uint8_t* p) { return static_cast<uint16_t>((static_cast<uint16_t>(p[0])<<8U)|p[1]); }
inline void writeBe16(uint8_t* p,uint16_t v) {p[0]=static_cast<uint8_t>(v>>8U);p[1]=static_cast<uint8_t>(v);}
inline bool decodeAdu(const uint8_t* bytes,std::size_t size,MbapHeader& header,const uint8_t*& pdu,std::size_t& pduSize) {
 if(!bytes||size<8||size>kMaxAduBytes)return false;
 MbapHeader parsed;parsed.transactionId=readBe16(bytes);parsed.protocolId=readBe16(bytes+2);parsed.length=readBe16(bytes+4);parsed.unitId=bytes[6];
 if(parsed.protocolId!=0||parsed.length<2||parsed.length>kMaxPduBytes+1||size!=6U+parsed.length)return false;
 header=parsed;pdu=bytes+kMbapHeaderBytes;pduSize=size-kMbapHeaderBytes;return true;
}
inline std::size_t encodeAdu(uint8_t* dest,std::size_t capacity,uint16_t transactionId,uint8_t unitId,const uint8_t* pdu,std::size_t pduSize) {
 if(!dest||!pdu||!pduSize||pduSize>kMaxPduBytes||capacity<kMbapHeaderBytes+pduSize)return 0;
 writeBe16(dest,transactionId);writeBe16(dest+2,0);writeBe16(dest+4,static_cast<uint16_t>(pduSize+1));dest[6]=unitId;std::memcpy(dest+7,pdu,pduSize);return 7+pduSize;
}
}
