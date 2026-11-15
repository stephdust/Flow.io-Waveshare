#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>
namespace flowio::modbus_ip {
enum class ProfileMode : uint8_t { Automatic=0, CommonManual=1, PerDevice=2 };
struct SerialProfile {
 uint32_t baud=9600;
 uint8_t parity=0; // 0 none, 1 even, 2 odd
 uint8_t stopBits=1;
};
inline bool validProfile(const SerialProfile& p) {
 return p.baud>=1200 && p.baud<=115200 && p.parity<=2 && (p.stopBits==1||p.stopBits==2);
}
class ProfileTable {
public:
 static constexpr std::size_t Capacity=32;
 bool set(uint8_t id,const SerialProfile& profile) {
  if(id<1||id>247||!validProfile(profile))return false;
  for(auto& item:entries_)if(item.id==id){item.profile=profile;return true;}
  for(auto& item:entries_)if(item.id==0){item.id=id;item.profile=profile;return true;}
  return false;
 }
 bool erase(uint8_t id){for(auto& item:entries_)if(item.id==id){item={};return true;}return false;}
 bool get(uint8_t id,SerialProfile& out)const {for(const auto& item:entries_)if(item.id==id){out=item.profile;return true;}return false;}
 // Format: id:baud:parity:stopBits;... (empty string = no overrides).
 // Reject malformed entries and duplicates without mutating the live table.
 bool parse(const char* text) {
  if(!text)return false;
  ProfileTable candidate{};
  const char* cursor=text;
  while(*cursor) {
   unsigned id=0,baud=0,parity=0,stops=0;
   int consumed=0;
   if(std::sscanf(cursor,"%u:%u:%u:%u%n",&id,&baud,&parity,&stops,&consumed)!=4||
      consumed<=0||id>247||id==0||parity>2||stops<1||stops>2)return false;
   cursor+=consumed;
   if(*cursor!=';'&&*cursor!='\0')return false;
   SerialProfile previous{};
   if(candidate.get(static_cast<uint8_t>(id),previous)||
      !candidate.set(static_cast<uint8_t>(id),
                     {static_cast<uint32_t>(baud),static_cast<uint8_t>(parity),
                      static_cast<uint8_t>(stops)}))return false;
   if(*cursor==';')++cursor;
  }
  *this=candidate;
  return true;
 }
 bool format(char* out,std::size_t capacity)const {
  if(!out||!capacity)return false;
  std::size_t offset=0;
  out[0]='\0';
  for(const auto& item:entries_) {
   if(!item.id)continue;
   const int n=std::snprintf(out+offset,capacity-offset,"%u:%lu:%u:%u;",
     static_cast<unsigned>(item.id),static_cast<unsigned long>(item.profile.baud),
     static_cast<unsigned>(item.profile.parity),static_cast<unsigned>(item.profile.stopBits));
   if(n<0||static_cast<std::size_t>(n)>=capacity-offset){out[0]='\0';return false;}
   offset+=static_cast<std::size_t>(n);
  }
  return true;
 }
private:
 struct Entry {uint8_t id=0;SerialProfile profile{};};
 Entry entries_[Capacity]{};
};
}
