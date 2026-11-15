#pragma once
#include "Core/Module.h"
#include "Core/Services/Services.h"
#include "ModbusIpConfig.h"
#include "ModbusIpKnownDeviceProfile.h"
#include "Core/Services/IPoolDevice.h"
#include "Core/SystemLimits.h"
#include "ModbusIpProfileResolver.h"
#include "ModbusTcpEndpoint.h"
#include "ModbusUdpEndpoint.h"

// Native Flow.io module. No UART is created here: all requests use the
// ModbusMaster service provided by IOModule.
class ModbusIpServerModule final : public Module {
public:
 ModuleId moduleId() const override { return ModuleId::ModbusIpServer; }
 const char* taskName() const override { return "modbusip"; }
 uint8_t dependencyCount() const override { return 2; }
 ModuleId dependency(uint8_t index) const override {
  return index==0?ModuleId::Io:index==1?ModuleId::LogHub:ModuleId::Unknown;
 }
 uint8_t taskCount() const override { return 1; }
 const ModuleTaskSpec* taskSpecs() const override { return singleLoopTaskSpec(); }
 uint16_t taskStackSize() const override { return 6144; }
 void init(ConfigStore& cfg,ServiceRegistry& services) override {
  config_.registerWith(cfg);
  services_=&services;
 }
 void onStart(ConfigStore&,ServiceRegistry& services) override {
  master_=services.get<ModbusMasterService>(ServiceId::ModbusMaster);
  network_=services.get<NetworkAccessService>(ServiceId::NetworkAccess);
  poolDevices_=services.get<PoolDeviceService>(ServiceId::PoolDevice);
  started_=true;
 }
 void loop() override {
  if(started_&&services_){
   if(!master_)master_=services_->get<ModbusMasterService>(ServiceId::ModbusMaster);
   if(!network_)network_=services_->get<NetworkAccessService>(ServiceId::NetworkAccess);
   if(!poolDevices_)poolDevices_=services_->get<PoolDeviceService>(ServiceId::PoolDevice);
  }
  if(!started_||!master_||!config_.data.enabled||!config_.data.valid()||
     !network_||!network_->isWebReachable||!network_->isWebReachable(network_->ctx)) {
   if(active_){tcp_.stop();udp_.stop();active_=false;}return;
  }
  const auto& cfg=config_.data;
  if(active_&&boundPort_!=cfg.port){tcp_.stop();udp_.stop();active_=false;}
  boundPort_=cfg.port;active_=true;
  if(cfg.tcpEnabled){
   if(tcp_.begin(cfg.port))tcp_.tick(*master_,&resolve_,this,201,
                                        static_cast<uint32_t>(cfg.timeoutMs));
  }else if(tcp_.listening())tcp_.stop();
  if(cfg.udpEnabled){
   if(udp_.begin(cfg.port))udp_.tick(*master_,&resolve_,this,202,
                                        static_cast<uint32_t>(cfg.timeoutMs));
  }else if(udp_.listening())udp_.stop();
 }
 bool setDeviceProfile(uint8_t id,const flowio::modbus_ip::SerialProfile& profile) {
  return profiles_.set(id,profile);
 }
 void setKnownDeviceResolver(bool (*resolver)(void*,uint8_t,flowio::modbus_ip::SerialProfile&),
                             void* ctx) {
  knownResolver_=resolver;knownCtx_=ctx;
 }
private:
 bool resolveKnownDevice_(uint8_t id,flowio::modbus_ip::SerialProfile& profile) const {
  if(!poolDevices_||!poolDevices_->getSerialConfig)return false;
  bool found=false;
  flowio::modbus_ip::SerialProfile selected{};
  // PoolDeviceService::count counts used slots, not the highest slot index.
  // Iterate the full configured slot range to include sparse allocations.
  for(uint8_t slot=0;slot<Limits::Io::MaxPoolDevices;++slot){
   PoolDriverConfig device{};
   if(!poolDevices_->getSerialConfig(poolDevices_->ctx,slot,&device))continue;
   flowio::modbus_ip::SerialProfile candidate{};
   if(!flowio::modbus_ip::profileFromPoolSerialConfig(device,id,candidate))continue;
   // Conflicting configurations for the same RTU address are ambiguous.
   // Refuse to guess a serial line configuration for the shared bus.
   if(!flowio::modbus_ip::mergeKnownDeviceProfile(candidate,found,selected))
    return false;
  }
  if(found)profile=selected;
  return found;
 }
 static bool resolve_(void* ctx,uint8_t id,flowio::modbus_ip::SerialProfile& profile) {
  auto& self=*static_cast<ModbusIpServerModule*>(ctx);
  flowio::modbus_ip::KnownDeviceProfile known{};
  if(self.knownResolver_)known.found=self.knownResolver_(self.knownCtx_,id,known.profile);
  if(!known.found)known.found=self.resolveKnownDevice_(id,known.profile);
  const auto& cfg=self.config_.data;
  const auto selection=flowio::modbus_ip::resolveProfile(
   static_cast<flowio::modbus_ip::ProfileMode>(cfg.profileMode),id,
   cfg.commonProfile(),self.profiles_,known);
  if(selection.status!=flowio::modbus_ip::ResolveStatus::Ok)return false;
  profile=selection.profile;return true;
 }
 flowio::modbus_ip::GatewayConfigVariables config_{};
 flowio::modbus_ip::ProfileTable profiles_{};
 flowio::modbus_ip::TcpEndpoint tcp_{};
 flowio::modbus_ip::UdpEndpoint udp_{};
 ServiceRegistry* services_=nullptr;
 const ModbusMasterService* master_=nullptr;
 const NetworkAccessService* network_=nullptr;
 const PoolDeviceService* poolDevices_=nullptr;
 bool (*knownResolver_)(void*,uint8_t,flowio::modbus_ip::SerialProfile&)=nullptr;
 void* knownCtx_=nullptr;
 bool started_=false;
 bool active_=false;
 uint16_t boundPort_=0;
};
