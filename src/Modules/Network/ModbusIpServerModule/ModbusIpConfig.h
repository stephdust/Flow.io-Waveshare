#pragma once
#include <cstdint>
#include <cstring>
#include "Core/ConfigTypes.h"
#include "Core/NvsKeys.h"
#include "ModbusIpProfiles.h"
#include "ModbusIpPortConfig.h"
namespace flowio::modbus_ip {
// Values are registered through ConfigStore by the owning Flow.io module.
// Disabled by default to avoid exposing an unexpected network listener.
struct GatewayConfig {
 bool enabled=false;
 bool modbusTrace=false;
 bool tcpEnabled=true;
 bool udpEnabled=false;
 uint16_t port=502;
 int32_t timeoutMs=3000;
 uint8_t profileMode=0;
 int32_t baud=9600;
 uint8_t parity=0;
 uint8_t stopBits=1;
 bool valid()const {
  if(port==0||timeoutMs<10||timeoutMs>5000||profileMode>2)return false;
  // The common serial settings are used only in manual mode. In automatic
  // and per-device modes, profiles are resolved from the device registry
  // or the explicit per-device table.
  if(profileMode!=static_cast<uint8_t>(ProfileMode::CommonManual))return true;
  if(baud<0)return false;
  return validProfile(commonProfile());
 }
 SerialProfile commonProfile()const {
  return {static_cast<uint32_t>(baud),parity,stopBits};
 }
};
struct GatewayConfigVariables {
 GatewayConfig data{};
 static constexpr std::size_t DeviceProfilesCapacity=768;
 char deviceProfiles[DeviceProfilesCapacity]{};
 ConfigVariable<bool,1> modbusTrace{NVS_KEY("mi_trace"),"debug_modbus","modbus_ip",ConfigType::Bool,&data.modbusTrace,ConfigPersistence::Persistent,0};
 ConfigVariable<bool,1> enabled{NVS_KEY(NvsKeys::ModbusIp::Enabled),"enabled","modbus_ip",ConfigType::Bool,&data.enabled,ConfigPersistence::Persistent,0};
 ConfigVariable<bool,1> tcp{NVS_KEY(NvsKeys::ModbusIp::TcpEnabled),"tcp_enabled","modbus_ip",ConfigType::Bool,&data.tcpEnabled,ConfigPersistence::Persistent,0};
 ConfigVariable<bool,1> udp{NVS_KEY(NvsKeys::ModbusIp::UdpEnabled),"udp_enabled","modbus_ip",ConfigType::Bool,&data.udpEnabled,ConfigPersistence::Persistent,0};
 ConfigVariable<uint16_t,1> port{NVS_KEY(NvsKeys::ModbusIp::Port),"port","modbus_ip",ConfigType::UInt16,&data.port,ConfigPersistence::Persistent,0};
 ConfigVariable<int32_t,1> timeout{NVS_KEY(NvsKeys::ModbusIp::TimeoutMs),"timeout_ms","modbus_ip",ConfigType::Int32,&data.timeoutMs,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,1> mode{NVS_KEY(NvsKeys::ModbusIp::ProfileMode),"profile_mode","modbus_ip",ConfigType::UInt8,&data.profileMode,ConfigPersistence::Persistent,0};
 ConfigVariable<int32_t,1> baud{NVS_KEY(NvsKeys::ModbusIp::Baud),"baud","modbus_ip",ConfigType::Int32,&data.baud,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,1> parity{NVS_KEY(NvsKeys::ModbusIp::Parity),"parity","modbus_ip",ConfigType::UInt8,&data.parity,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,1> stopBits{NVS_KEY(NvsKeys::ModbusIp::StopBits),"stop_bits","modbus_ip",ConfigType::UInt8,&data.stopBits,ConfigPersistence::Persistent,0};
 ConfigVariable<char,1> deviceProfilesVar{NVS_KEY("mi_devices"),"device_profiles","modbus_ip",ConfigType::CharArray,deviceProfiles,ConfigPersistence::Persistent,DeviceProfilesCapacity};
 // Fixed network ports, independent TCP/UDP and serial targets.
 // The old settings remain registered for backward-compatible NVS reads,
 // but the runtime uses these five records exclusively.
 char port502Text[64]="0:1:0:0:0:9600:0:1";
 char port503Text[64]="0:1:0:0:0:9600:0:1";
 char port504Text[64]="0:1:0:0:0:9600:0:1";
 char port505Text[64]="0:1:0:0:0:9600:0:1";
 char port506Text[64]="0:1:0:0:0:9600:0:1";
 ConfigVariable<char,1> port502{NVS_KEY("mi_p502"),"port_502","modbus_ip",ConfigType::CharArray,port502Text,ConfigPersistence::Persistent,sizeof(port502Text)};
 ConfigVariable<char,1> port503{NVS_KEY("mi_p503"),"port_503","modbus_ip",ConfigType::CharArray,port503Text,ConfigPersistence::Persistent,sizeof(port503Text)};
 ConfigVariable<char,1> port504{NVS_KEY("mi_p504"),"port_504","modbus_ip",ConfigType::CharArray,port504Text,ConfigPersistence::Persistent,sizeof(port504Text)};
 ConfigVariable<char,1> port505{NVS_KEY("mi_p505"),"port_505","modbus_ip",ConfigType::CharArray,port505Text,ConfigPersistence::Persistent,sizeof(port505Text)};
 ConfigVariable<char,1> port506{NVS_KEY("mi_p506"),"port_506","modbus_ip",ConfigType::CharArray,port506Text,ConfigPersistence::Persistent,sizeof(port506Text)};
 const char* portText(uint8_t index)const {
  switch(index) {
   case 0:return port502Text;case 1:return port503Text;case 2:return port504Text;
   case 3:return port505Text;case 4:return port506Text;default:return "";
  }
 }
 static bool validDeviceProfiles(const char* text) {
  ProfileTable table{};
  if(!text)return false;
  // ConfigStore owns a fixed-size char buffer: never scan beyond its end.
  std::size_t length=0;
  while(length<DeviceProfilesCapacity&&text[length]!=0)++length;
  return length<DeviceProfilesCapacity&&table.parse(text);
 }
 template<class Store> void registerWith(Store& store){
  store.registerVar(modbusTrace);store.registerVar(enabled);store.registerVar(tcp);store.registerVar(udp);
  store.registerVar(port);store.registerVar(timeout);store.registerVar(mode);
  store.registerVar(baud);store.registerVar(parity);store.registerVar(stopBits);
  deviceProfilesVar.validateText=&validDeviceProfiles;
  store.registerVar(deviceProfilesVar);
  port502.validateText=&validPortConfigText;port503.validateText=&validPortConfigText;
  port504.validateText=&validPortConfigText;port505.validateText=&validPortConfigText;
  port506.validateText=&validPortConfigText;
  store.registerVar(port502);store.registerVar(port503);store.registerVar(port504);
 }
};
}
