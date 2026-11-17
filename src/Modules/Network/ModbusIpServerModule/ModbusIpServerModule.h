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
#include "ModbusIpHealth.h"

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
  for(uint8_t i=0;i<3;++i)contexts_[i]={this,i};
  started_=true;
 }
 void loop() override {
  FlowModbusIpHealth::loopStartMs=millis();
  FlowModbusIpHealth::lastProgressMs=FlowModbusIpHealth::loopStartMs;
  FlowModbusIpHealth::stage=1;
#if FLOW_MODBUS_IP_UDP_TIMING
  const uint32_t loopStartedUs=micros();
  uint32_t slowestPortUs=0;
  uint8_t slowestPort=0;
#endif
  if(started_&&services_){
   if(!master_)master_=services_->get<ModbusMasterService>(ServiceId::ModbusMaster);
   if(!network_)network_=services_->get<NetworkAccessService>(ServiceId::NetworkAccess);
   if(!poolDevices_)poolDevices_=services_->get<PoolDeviceService>(ServiceId::PoolDevice);
  }
  if(!started_||!master_||
     !network_||!network_->isWebReachable||!network_->isWebReachable(network_->ctx)) {
   stopAll_();
   FlowModbusIpHealth::stage=3;
   FlowModbusIpHealth::lastProgressMs=millis();
   return;
  }
  for(uint8_t i=0;i<3;++i) {
   FlowModbusIpHealth::stage=2;
   FlowModbusIpHealth::port=(uint8_t)(502+i);
   FlowModbusIpHealth::lastProgressMs=millis();
#if FLOW_MODBUS_IP_UDP_TIMING
   const uint32_t portStartedUs=micros();
#endif
   ::flowio::modbus_ip::PortConfig port{};
   const bool configured=::flowio::modbus_ip::parsePortConfig(config_.portText(i),port);
   if(!configured||(!port.tcp&&!port.udp)) {
    tcp_[i].stop();udp_[i].stop();caches_[i].clear();
    loadedPorts_[i][0]=0;continue;
   }
   const char* settings=config_.portText(i);
   if(std::strcmp(loadedPorts_[i],settings)!=0){
    caches_[i].clear();
    std::strncpy(loadedPorts_[i],settings,sizeof(loadedPorts_[i])-1);
    loadedPorts_[i][sizeof(loadedPorts_[i])-1]=0;
   }
   uint8_t target=port.target;
   if(port.mode==0) {
    ::flowio::modbus_ip::SerialProfile profile{};
    if(!resolvePort_(i,target,profile)) {
     tcp_[i].stop();udp_[i].stop();continue;
    }
   }
   const uint16_t networkPort=static_cast<uint16_t>(502+i);
   const uint32_t timeout=port.timeoutMs;
   if(port.tcp) {
    if(tcp_[i].begin(networkPort))
     tcp_[i].tick(*master_,&resolvePortCallback_,&contexts_[i],
                  static_cast<uint8_t>(201+i*5),timeout,target,
                  port.cacheEnabled?&caches_[i]:nullptr,port.cacheTtlMs,
                  port.timeoutBehavior==0);
   }else if(tcp_[i].listening())tcp_[i].stop();
   if(port.udp) {
    if(udp_[i].begin(networkPort))
     udp_[i].tick(*master_,&resolvePortCallback_,&contexts_[i],
                  static_cast<uint8_t>(205+i*5),timeout,target,
                  port.cacheEnabled?&caches_[i]:nullptr,port.cacheTtlMs,
                  port.timeoutBehavior==0);
   }else if(udp_[i].listening())udp_[i].stop();
#if FLOW_MODBUS_IP_UDP_TIMING
   const uint32_t portUs=micros()-portStartedUs;
   if(portUs>slowestPortUs){slowestPortUs=portUs;slowestPort=i;}
#endif
  }
  FlowModbusIpHealth::stage=3;
  FlowModbusIpHealth::lastProgressMs=millis();
#if FLOW_MODBUS_IP_UDP_TIMING
  const uint32_t loopUs=micros()-loopStartedUs;
  static uint32_t lastSlowLogMs=0;
  const uint32_t nowMs=millis();
  if(loopUs>=100000U && (uint32_t)(nowMs-lastSlowLogMs)>=2000U){
   lastSlowLogMs=nowMs;
   ::Log::info((LogModuleId)LogModuleIdValue::IOModule,
     "[Modbus IP] SLOW LOOP total_us=%lu max_port=%u port_us=%lu\n",
     (unsigned long)loopUs,(unsigned)(502U+slowestPort),(unsigned long)slowestPortUs);
  }
#endif
 }
 bool setDeviceProfile(uint8_t id,const ::flowio::modbus_ip::SerialProfile& profile) {
  return profiles_.set(id,profile);
 }
 void setKnownDeviceResolver(bool (*resolver)(void*,uint8_t,::flowio::modbus_ip::SerialProfile&),
                             void* ctx) {
  knownResolver_=resolver;knownCtx_=ctx;
 }
private:
 struct PortContext { ModbusIpServerModule* module=nullptr;uint8_t index=0; };
 void stopAll_() {
  for(uint8_t i=0;i<3;++i){tcp_[i].stop();udp_[i].stop();caches_[i].clear();}
 }
 bool resolvePort_(uint8_t index,uint8_t& target,
                   ::flowio::modbus_ip::SerialProfile& profile) const {
  ::flowio::modbus_ip::PortConfig port{};
  if(index>=3||!::flowio::modbus_ip::parsePortConfig(config_.portText(index),port)||
     !port.enabled)return false;
  if(port.mode==1) {
   target=port.target;profile=port.serial;
   return target>=1&&target<=247&&::flowio::modbus_ip::validProfile(profile);
  }
  if(!poolDevices_||!poolDevices_->getSerialConfig||
     port.target>=Limits::Io::MaxPoolDevices)return false;
  PoolDriverConfig device{};
  if(!poolDevices_->getSerialConfig(poolDevices_->ctx,port.target,&device))return false;
  const uint8_t address=device.serial.address;
  if(!::flowio::modbus_ip::profileFromPoolSerialConfig(device,address,profile))return false;
  target=address;
  return true;
 }
 static bool resolvePortCallback_(void* ctx,uint8_t unitId,
                                  ::flowio::modbus_ip::SerialProfile& profile) {
  const auto& context=*static_cast<PortContext*>(ctx);
  if(!context.module)return false;
  uint8_t target=0;
  if(!context.module->resolvePort_(context.index,target,profile))return false;
  return unitId==target;
 }

 void refreshDeviceProfiles_() {
  if(std::strcmp(loadedDeviceProfiles_,config_.deviceProfiles)==0)return;
  ::flowio::modbus_ip::ProfileTable candidate{};
  if(!candidate.parse(config_.deviceProfiles))return;
  profiles_=candidate;
  std::memcpy(loadedDeviceProfiles_,config_.deviceProfiles,
              std::strlen(config_.deviceProfiles)+1);
 }
 bool resolveKnownDevice_(uint8_t id,::flowio::modbus_ip::SerialProfile& profile) const {
  if(!poolDevices_||!poolDevices_->getSerialConfig)return false;
  bool found=false;
  ::flowio::modbus_ip::SerialProfile selected{};
  // PoolDeviceService::count counts used slots, not the highest slot index.
  // Iterate the full configured slot range to include sparse allocations.
  for(uint8_t slot=0;slot<Limits::Io::MaxPoolDevices;++slot){
   PoolDriverConfig device{};
   if(!poolDevices_->getSerialConfig(poolDevices_->ctx,slot,&device))continue;
   ::flowio::modbus_ip::SerialProfile candidate{};
   if(!::flowio::modbus_ip::profileFromPoolSerialConfig(device,id,candidate))continue;
   // Conflicting configurations for the same RTU address are ambiguous.
   // Refuse to guess a serial line configuration for the shared bus.
   if(!::flowio::modbus_ip::mergeKnownDeviceProfile(candidate,found,selected))
    return false;
  }
  if(found)profile=selected;
  return found;
 }
 static bool resolve_(void* ctx,uint8_t id,::flowio::modbus_ip::SerialProfile& profile) {
  auto& self=*static_cast<ModbusIpServerModule*>(ctx);
  ::flowio::modbus_ip::KnownDeviceProfile known{};
  if(self.knownResolver_)known.found=self.knownResolver_(self.knownCtx_,id,known.profile);
  if(!known.found)known.found=self.resolveKnownDevice_(id,known.profile);
  const auto& cfg=self.config_.data;
  const auto selection=::flowio::modbus_ip::resolveProfile(
   static_cast<::flowio::modbus_ip::ProfileMode>(cfg.profileMode),id,
   cfg.commonProfile(),self.profiles_,known);
  if(selection.status!=::flowio::modbus_ip::ResolveStatus::Ok)return false;
  profile=selection.profile;return true;
 }
 ::flowio::modbus_ip::GatewayConfigVariables config_{};
 ::flowio::modbus_ip::ProfileTable profiles_{};
 char loadedDeviceProfiles_[::flowio::modbus_ip::GatewayConfigVariables::DeviceProfilesCapacity]{};
 ::flowio::modbus_ip::TcpEndpoint tcp_[3]{};
 ::flowio::modbus_ip::UdpEndpoint udp_[3]{};
 ::flowio::modbus_ip::ReadCache caches_[3]{};
 char loadedPorts_[3][64]{};
 PortContext contexts_[3]{};
 ServiceRegistry* services_=nullptr;
 const ModbusMasterService* master_=nullptr;
 const NetworkAccessService* network_=nullptr;
 const PoolDeviceService* poolDevices_=nullptr;
 bool (*knownResolver_)(void*,uint8_t,::flowio::modbus_ip::SerialProfile&)=nullptr;
 void* knownCtx_=nullptr;
 bool started_=false;

};
