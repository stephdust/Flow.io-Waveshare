#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "ModbusIpProfiles.h"

namespace flowio::modbus_ip {
// Persistent per-port record: enabled:tcp:udp:mode:target:baud:parity:stop
// mode=0: existing Flow.io pool-device slot; mode=1: manual RTU unit ID.
struct PortConfig {
 bool enabled=false;
 bool tcp=true;
 bool udp=false;
 uint8_t mode=0;
 uint8_t target=0;
 SerialProfile serial{};
};
inline bool parsePortConfig(const char* text,PortConfig& result) {
 if(!text||!*text)return false;
 unsigned values[8]{};
 int consumed=0;
 if(std::sscanf(text,"%u:%u:%u:%u:%u:%u:%u:%u%n",
   &values[0],&values[1],&values[2],&values[3],&values[4],
   &values[5],&values[6],&values[7],&consumed)!=8 ||
   text[consumed]!='\0')return false;
 if(values[0]>1||values[1]>1||values[2]>1||values[3]>1||
    values[4]>247||values[5]>115200||values[6]>2||values[7]<1||values[7]>2||
    (values[3]==1&&values[4]<1))return false;
 PortConfig next{};
 next.enabled=values[0]!=0;
 next.tcp=values[1]!=0;
 next.udp=values[2]!=0;
 next.mode=static_cast<uint8_t>(values[3]);
 next.target=static_cast<uint8_t>(values[4]);
 next.serial={values[5],static_cast<uint8_t>(values[6]),static_cast<uint8_t>(values[7])};
 if(next.mode==1&&!validProfile(next.serial))return false;
 result=next;
 return true;
}
inline bool validPortConfigText(const char* text) {
 PortConfig parsed{};
 return parsePortConfig(text,parsed);
}
} // namespace flowio::modbus_ip
