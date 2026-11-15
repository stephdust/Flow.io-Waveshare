#pragma once
#include <cstdint>
#include "ModbusIpProfiles.h"
namespace flowio::modbus_ip {
// The caller resolves known Flow.io devices through the existing device
// registry. No hardware access is performed from this policy layer.
struct KnownDeviceProfile {
 bool found=false;
 SerialProfile profile{};
};
enum class ResolveStatus : uint8_t { Ok, UnknownDevice, InvalidProfile };
struct ProfileSelection {
 ResolveStatus status=ResolveStatus::UnknownDevice;
 SerialProfile profile{};
};
inline ProfileSelection resolveProfile(ProfileMode mode,uint8_t unitId,
 const SerialProfile& common,const ProfileTable& table,
 const KnownDeviceProfile& known) {
 if(unitId<1||unitId>247)return {};
 SerialProfile selected{};
 switch(mode) {
  case ProfileMode::Automatic:
   if(!known.found)return {};
   selected=known.profile;
   break;
  case ProfileMode::CommonManual:
   selected=common;
   break;
  case ProfileMode::PerDevice:
   // An explicit table entry takes precedence; Flow.io profiles remain
   // available for devices that are not overridden.
   if(!table.get(unitId,selected)){
    if(!known.found)return {};
    selected=known.profile;
   }
   break;
  default:return {};
 }
 if(!validProfile(selected))return {ResolveStatus::InvalidProfile,{}};
 return {ResolveStatus::Ok,selected};
}
}
