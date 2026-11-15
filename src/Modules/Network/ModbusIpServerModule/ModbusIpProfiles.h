#pragma once
#include <cstddef>
#include <cstdint>
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
private:
 struct Entry {uint8_t id=0;SerialProfile profile{};};
 Entry entries_[Capacity]{};
};
}
