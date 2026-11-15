#include <cassert>
#include "../../src/Modules/Network/ModbusIpServerModule/ModbusIpProfileResolver.h"
using namespace flowio::modbus_ip;
int main(){
 ProfileTable table;
 const SerialProfile common{9600,0,1};
 const SerialProfile mapped{19200,1,1};
 const KnownDeviceProfile known{true,{38400,0,2}};
 assert(table.set(4,mapped));
 auto p=resolveProfile(ProfileMode::PerDevice,4,common,table,known);
 assert(p.status==ResolveStatus::Ok&&p.profile.baud==19200&&p.profile.parity==1&&p.profile.stopBits==1);
 p=resolveProfile(ProfileMode::PerDevice,5,common,table,known);
 assert(p.status==ResolveStatus::Ok&&p.profile.baud==38400);
 p=resolveProfile(ProfileMode::PerDevice,5,common,table,{});
 assert(p.status==ResolveStatus::UnknownDevice);
 p=resolveProfile(ProfileMode::Automatic,4,common,table,known);
 assert(p.status==ResolveStatus::Ok&&p.profile.baud==38400);
 p=resolveProfile(ProfileMode::CommonManual,4,common,table,{});
 assert(p.status==ResolveStatus::Ok&&p.profile.baud==9600);
 p=resolveProfile(ProfileMode::CommonManual,0,common,table,{});
 assert(p.status==ResolveStatus::UnknownDevice);
 p=resolveProfile(ProfileMode::CommonManual,4,{0,0,1},table,{});
 assert(p.status==ResolveStatus::InvalidProfile);
 return 0;
}
