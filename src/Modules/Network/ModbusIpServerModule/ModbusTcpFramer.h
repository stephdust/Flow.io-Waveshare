#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include "ModbusMbapCodec.h"
namespace flowio::modbus_ip {
// TCP is a byte stream: one read may contain half an ADU or several ADUs.
// This bounded accumulator emits exactly one complete MBAP ADU at a time.
class TcpFramer {
public:
 enum class FeedResult : uint8_t { NeedMore, Complete, Invalid, Overflow };
 FeedResult push(const uint8_t* data,std::size_t length,std::size_t& consumed) {
  consumed=0;
  if(!data&&length)return FeedResult::Invalid;
  while(consumed<length) {
   if(used_==sizeof(bytes_)){reset();return FeedResult::Overflow;}
   bytes_[used_++]=data[consumed++];
   if(used_==6) {
    const auto declared=readBe16(bytes_+4);
    if(readBe16(bytes_+2)!=0||declared<2||declared>kMaxPduBytes+1){
     reset();return FeedResult::Invalid;
    }
    expected_=6U+declared;
   }
   if(expected_&&used_==expected_)return FeedResult::Complete;
  }
  return FeedResult::NeedMore;
 }
 bool ready() const {return expected_&&used_==expected_;}
 const uint8_t* data() const {return ready()?bytes_:nullptr;}
 std::size_t size() const {return ready()?used_:0;}
 void reset(){used_=0;expected_=0;}
private:
 uint8_t bytes_[kMaxAduBytes]{};
 std::size_t used_=0,expected_=0;
};
}
