#include <cassert>
#include <cstddef>
#include <cstdint>
#include "Modules/Network/ModbusIpServerModule/ModbusIpReadCache.h"
#include "Modules/Network/ModbusIpServerModule/ModbusIpTransactionBridge.h"
using namespace flowio::modbus_ip;
struct FakeMaster {
  ModbusRequest sent{};
  unsigned submits=0;
  bool pending=false;
  ModbusResultCode result=MODBUS_RESULT_OK;
  static ModbusResultCode submit(void* ctx,const ModbusRequest* req,uint16_t* id){
    auto& self=*static_cast<FakeMaster*>(ctx);
    self.sent=*req;++self.submits;self.pending=true;*id=12;
    return MODBUS_RESULT_OK;
  }
  static ModbusResultCode poll(void* ctx,uint16_t,ModbusResponse* out){
    auto& self=*static_cast<FakeMaster*>(ctx);
    if(self.pending)return MODBUS_RESULT_NOT_READY;
    out->state=self.result==MODBUS_RESULT_OK?MODBUS_TRANSACTION_COMPLETE:MODBUS_TRANSACTION_FAILED;
    out->result=self.result;
    out->slaveAddress=self.sent.slaveAddress;
    out->function=self.sent.function;
    out->registerCount=self.sent.registerCount;
    out->values[0]=0xCAFE;
    return MODBUS_RESULT_OK;
  }
};
int main(){
  ReadCache cache{};
  const SerialProfile profile{9600,0,1};
  const SerialProfile otherProfile{19200,0,1};
  RegisterRequest request{};
  request.function=3;request.unitId=7;request.kind=RequestKind::ReadRegisters;
  request.address=10;request.count=1;
  const uint16_t values[]={0xCAFE};
  uint16_t cached[32]{};
  assert(!cache.lookup(request,profile,100,800,cached));
  cache.store(request,profile,100,values);
  assert(cache.lookup(request,profile,899,800,cached)&&cached[0]==0xCAFE);
  assert(!cache.lookup(request,profile,900,800,cached));
  cache.store(request,profile,1000,values);
  assert(!cache.lookup(request,otherProfile,1001,800,cached));
  auto different=request;different.address=11;
  assert(!cache.lookup(different,profile,1001,800,cached));
  cache.invalidate(7);
  assert(!cache.lookup(request,profile,1001,800,cached));
  cache.store(request,profile,0xFFFFFFFEU,values);
  assert(cache.lookup(request,profile,1,800,cached)); // millis rollover
  cache.clear();
  assert(!cache.lookup(request,profile,1,800,cached));

  FakeMaster fake{};
  ModbusMasterService service{&FakeMaster::submit,&FakeMaster::poll,nullptr,nullptr,&fake};
  TransactionBridge bridge{};
  uint8_t input[64]{},output[64]{};
  const uint8_t readPdu[]={3,0,10,0,1};
  std::size_t n=encodeAdu(input,sizeof(input),123,7,readPdu,sizeof(readPdu));
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,100,800,true));
  assert(fake.submits==1);
  fake.pending=false;bridge.tick(110);
  std::size_t length=0;
  assert(bridge.takeResponse(output,sizeof(output),length));
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,200,800,true));
  assert(fake.submits==1); // cache hit
  MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduSize=0;
  assert(bridge.takeResponse(output,sizeof(output),length));
  assert(decodeAdu(output,length,header,pdu,pduSize));
  assert(header.transactionId==123&&pduSize==4&&readBe16(pdu+2)==0xCAFE);
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,910,800,true));
  assert(fake.submits==2); // cache expired
  fake.pending=false;bridge.tick(920);
  assert(bridge.takeResponse(output,sizeof(output),length));

  const uint8_t writePdu[]={6,0,10,0,33};
  n=encodeAdu(input,sizeof(input),124,7,writePdu,sizeof(writePdu));
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,930,800,true));
  assert(fake.submits==3);
  fake.pending=false;bridge.tick(940);
  assert(bridge.takeResponse(output,sizeof(output),length));
  n=encodeAdu(input,sizeof(input),125,7,readPdu,sizeof(readPdu));
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,950,800,true));
  assert(fake.submits==4); // write invalidated cache
  fake.result=MODBUS_RESULT_TIMEOUT;fake.pending=false;bridge.tick(960);
  assert(!bridge.busy()); // silent timeout
  assert(!bridge.takeResponse(output,sizeof(output),length));
  assert(bridge.start(input,n,profile,201,3000,service,0,&cache,970,800,false));
  assert(fake.submits==5);
  fake.pending=false;bridge.tick(980);
  assert(bridge.takeResponse(output,sizeof(output),length));
  assert(decodeAdu(output,length,header,pdu,pduSize));
  assert(pduSize==2&&pdu[0]==0x83&&pdu[1]==0x0B);
  return 0;
}
