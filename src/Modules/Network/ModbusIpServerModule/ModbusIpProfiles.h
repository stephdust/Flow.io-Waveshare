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
   uint32_t parts[4]{};
   for(unsigned index=0;index<4;++index) {
    if(*cursor<'0'||*cursor>'9')return false;
    uint32_t value=0;
    while(*cursor>='0'&&*cursor<='9') {
     const uint32_t digit=static_cast<uint32_t>(*cursor-'0');
     if(value>(UINT32_MAX-digit)/10U)return false;
     value=value*10U+digit;
     ++cursor;
    }
    parts[index]=value;
    if(index!=3) {
     if(*cursor!=':')return false;
     ++cursor;
    }
   }
   if(*cursor!=';'&&*cursor!=0)return false;
   if(parts[0]<1||parts[0]>247||parts[1]<1200||parts[1]>115200||
      parts[2]>2||parts[3]<1||parts[3]>2)return false;
   const auto id=static_cast<uint8_t>(parts[0]);
   SerialProfile previous{};
   if(candidate.get(id,previous)||
      !candidate.set(id,{parts[1],static_cast<uint8_t>(parts[2]),
                         static_cast<uint8_t>(parts[3])}))return false;
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
