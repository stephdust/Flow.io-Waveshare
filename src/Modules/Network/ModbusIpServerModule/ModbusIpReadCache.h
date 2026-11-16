#pragma once
#include <cstdint>
#include "ModbusIpRegisterCodec.h"
#include "ModbusIpProfiles.h"

namespace flowio::modbus_ip {
// One cache instance per network port, shared between its TCP and UDP listeners.
// Only successful FC03/FC04 reads are cached; exception frames are never cached.
class ReadCache {
public:
 static constexpr unsigned Capacity=8;
 void clear(){for(auto& e:entries_)e.valid=false;}
 bool lookup(const RegisterRequest& req,const SerialProfile& profile,uint32_t now,
             uint32_t ttl,uint16_t* out) {
  if(!out||ttl==0||req.kind!=RequestKind::ReadRegisters)return false;
  for(auto& e:entries_) {
   if(!e.valid)continue;
   if(static_cast<uint32_t>(now-e.storedAt)>=ttl){e.valid=false;continue;}
   if(matches_(e,req,profile)){
    for(uint16_t i=0;i<req.count;++i)out[i]=e.values[i];
    return true;
   }
  }
  return false;
 }
 void store(const RegisterRequest& req,const SerialProfile& profile,uint32_t now,
            const uint16_t* values) {
  if(!values||req.kind!=RequestKind::ReadRegisters||req.count==0||req.count>32)return;
  Entry* chosen=nullptr;
  for(auto& e:entries_){
   if(e.valid&&matches_(e,req,profile)){chosen=&e;break;}
   if(!e.valid&&!chosen)chosen=&e;
  }
  if(!chosen){
   chosen=&entries_[0];
   for(auto& e:entries_)
    if(static_cast<uint32_t>(now-e.storedAt)>
       static_cast<uint32_t>(now-chosen->storedAt))chosen=&e;
  }
  chosen->valid=true;chosen->request=req;chosen->profile=profile;chosen->storedAt=now;
  for(uint16_t i=0;i<req.count;++i)chosen->values[i]=values[i];
 }
 void invalidate(uint8_t unitId){
  for(auto& e:entries_)if(e.valid&&e.request.unitId==unitId)e.valid=false;
 }
private:
 struct Entry {
  bool valid=false;
  RegisterRequest request{};
  SerialProfile profile{};
  uint32_t storedAt=0;
  uint16_t values[32]{};
 };
 static bool matches_(const Entry& e,const RegisterRequest& req,const SerialProfile& profile){
  return e.request.unitId==req.unitId&&e.request.function==req.function&&
    e.request.address==req.address&&e.request.count==req.count&&
    e.profile.baud==profile.baud&&e.profile.parity==profile.parity&&
    e.profile.stopBits==profile.stopBits;
 }
 Entry entries_[Capacity]{};
};
