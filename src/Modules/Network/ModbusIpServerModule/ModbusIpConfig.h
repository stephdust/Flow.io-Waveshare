#pragma once
#include <cstdint>
#include "Core/ConfigTypes.h"
#include "Core/NvsKeys.h"
#include "ModbusIpProfiles.h"
namespace flowio::modbus_ip {
// Values are registered through ConfigStore by the owning Flow.io module.
// Disabled by default to avoid exposing an unexpected network listener.
struct GatewayConfig {
 bool enabled=false;
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
  const SerialProfile p{static_cast<uint32_t>(baud),parity,stopBits};
  return validProfile(p);
 }
 SerialProfile commonProfile()const {
  return {static_cast<uint32_t>(baud),parity,stopBits};
 }
};
struct GatewayConfigVariables {
 GatewayConfig data{};
 ConfigVariable<bool,0> enabled{NVS_KEY(NvsKeys::ModbusIp::Enabled),"enabled","modbus_ip",ConfigType::Bool,&data.enabled,ConfigPersistence::Persistent,0};
 ConfigVariable<bool,0> tcp{NVS_KEY(NvsKeys::ModbusIp::TcpEnabled),"tcp_enabled","modbus_ip",ConfigType::Bool,&data.tcpEnabled,ConfigPersistence::Persistent,0};
 ConfigVariable<bool,0> udp{NVS_KEY(NvsKeys::ModbusIp::UdpEnabled),"udp_enabled","modbus_ip",ConfigType::Bool,&data.udpEnabled,ConfigPersistence::Persistent,0};
 ConfigVariable<uint16_t,0> port{NVS_KEY(NvsKeys::ModbusIp::Port),"port","modbus_ip",ConfigType::UInt16,&data.port,ConfigPersistence::Persistent,0};
 ConfigVariable<int32_t,0> timeout{NVS_KEY(NvsKeys::ModbusIp::TimeoutMs),"timeout_ms","modbus_ip",ConfigType::Int32,&data.timeoutMs,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,0> mode{NVS_KEY(NvsKeys::ModbusIp::ProfileMode),"profile_mode","modbus_ip",ConfigType::UInt8,&data.profileMode,ConfigPersistence::Persistent,0};
 ConfigVariable<int32_t,0> baud{NVS_KEY(NvsKeys::ModbusIp::Baud),"baud","modbus_ip",ConfigType::Int32,&data.baud,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,0> parity{NVS_KEY(NvsKeys::ModbusIp::Parity),"parity","modbus_ip",ConfigType::UInt8,&data.parity,ConfigPersistence::Persistent,0};
 ConfigVariable<uint8_t,0> stopBits{NVS_KEY(NvsKeys::ModbusIp::StopBits),"stop_bits","modbus_ip",ConfigType::UInt8,&data.stopBits,ConfigPersistence::Persistent,0};
 template<class Store> void registerWith(Store& store){
  store.registerVar(enabled);store.registerVar(tcp);store.registerVar(udp);
  store.registerVar(port);store.registerVar(timeout);store.registerVar(mode);
  store.registerVar(baud);store.registerVar(parity);store.registerVar(stopBits);
 }
};
}
