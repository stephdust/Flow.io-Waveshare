#include <cassert>
#include <cstring>
#include "Modules/Network/ModbusIpServerModule/ModbusIpProfiles.h"

int main() {
 using namespace flowio::modbus_ip;
 ProfileTable profiles{};
 assert(profiles.parse("17:9600:0:1;42:19200:1:2;"));
 SerialProfile p{};
 assert(profiles.get(17,p)&&p.baud==9600&&p.parity==0&&p.stopBits==1);
 assert(profiles.get(42,p)&&p.baud==19200&&p.parity==1&&p.stopBits==2);
 char buffer[768]{};
 assert(profiles.format(buffer,sizeof(buffer)));
 ProfileTable restored{};
 assert(restored.parse(buffer));
 assert(restored.get(42,p)&&p.baud==19200);
 assert(!restored.parse("17:9600:0:1;17:19200:0:1;"));
 assert(restored.get(42,p)&&p.baud==19200); // failed update is atomic
 assert(!restored.parse("248:9600:0:1;"));
 assert(!restored.parse("17:9600:3:1;"));
 assert(!restored.parse("17:9600:0:0;"));
 assert(!restored.parse("17:9600:0:1;invalid"));
 assert(restored.parse(""));
 assert(!restored.get(42,p));
 assert(restored.format(buffer,sizeof(buffer))&&std::strcmp(buffer,"")==0);
}
