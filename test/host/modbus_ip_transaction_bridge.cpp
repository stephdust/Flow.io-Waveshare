#include <cassert>
#include <cstdint>
#include <cstddef>
#include "Modules/Network/ModbusIpServerModule/ModbusIpTransactionBridge.h"
using namespace flowio::modbus_ip;
struct FakeMaster {
 ModbusRequest submitted{};
 bool pending=false;
 static ModbusResultCode submit(void* ctx,const ModbusRequest* req,uint16_t* id){
  auto& self=*static_cast<FakeMaster*>(ctx);self.submitted=*req;self.pending=true;*id=19;
  return MODBUS_RESULT_OK;
 }
 static ModbusResultCode poll(void* ctx,uint16_t id,ModbusResponse* response){
  auto& self=*static_cast<FakeMaster*>(ctx);assert(id==19);
  if(self.pending)return MODBUS_RESULT_NOT_READY;
  response->state=MODBUS_TRANSACTION_COMPLETE;response->result=MODBUS_RESULT_OK;
  response->slaveAddress=4;response->function=3;response->registerCount=2;response->values[0]=0x1234;response->values[1]=0xabcd;
  return MODBUS_RESULT_OK;
 }
 static void cancel(void* ctx,uint8_t){static_cast<FakeMaster*>(ctx)->pending=false;}
};
int main(){
 FakeMaster fake{};
 ModbusMasterService service{&FakeMaster::submit,&FakeMaster::poll,&FakeMaster::cancel,nullptr,&fake};
 const uint8_t requestPdu[]={3,0,16,0,2};
 uint8_t input[32]{};
 const auto n=encodeAdu(input,sizeof(input),0x4321,4,requestPdu,sizeof(requestPdu));
 TransactionBridge bridge{};
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 assert(bridge.state()==TransactionBridge::State::Pending);
 assert(fake.submitted.ownerId==201&&fake.submitted.priority==MODBUS_PRIORITY_NORMAL);
 assert(fake.submitted.slaveAddress==4&&fake.submitted.line.baud==19200);
 bridge.tick();assert(bridge.state()==TransactionBridge::State::Pending);
 fake.pending=false;bridge.tick();
 assert(bridge.state()==TransactionBridge::State::ResponseReady);
 uint8_t output[64]{};std::size_t length=0;
 assert(bridge.takeResponse(output,sizeof(output),length));
 MbapHeader header{};const uint8_t* pdu=nullptr;std::size_t pduLength=0;
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(header.transactionId==0x4321&&header.unitId==4);
 assert(pduLength==6&&pdu[0]==3&&pdu[1]==4&&readBe16(pdu+2)==0x1234);
 assert(!bridge.busy());
 const uint8_t unsupported[]={1,0,0,0,1};
 const auto m=encodeAdu(input,sizeof(input),7,4,unsupported,sizeof(unsupported));
 assert(bridge.start(input,m,{9600,0,1},201,3000,service));
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x81&&pdu[1]==1);
}
