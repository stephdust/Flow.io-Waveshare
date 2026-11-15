#include <cassert>
#include <cstdint>
#include <cstddef>
#include "Modules/Network/ModbusIpServerModule/ModbusIpTransactionBridge.h"
using namespace flowio::modbus_ip;
struct FakeMaster {
 ModbusRequest submitted{};
 bool pending=false;
 unsigned cancellations=0;
 uint8_t cancelledOwner=0;
 ModbusResultCode result=MODBUS_RESULT_OK;
 ModbusResultCode submitResult=MODBUS_RESULT_OK;
 uint8_t slave=4;
 uint8_t function=3;
 uint8_t exception=0;
 uint16_t count=2;
 static ModbusResultCode submit(void* ctx,const ModbusRequest* req,uint16_t* id){
  auto& self=*static_cast<FakeMaster*>(ctx);self.submitted=*req;self.pending=true;
  if(self.submitResult!=MODBUS_RESULT_OK)return self.submitResult;
  *id=19;
  return MODBUS_RESULT_OK;
 }
 static ModbusResultCode poll(void* ctx,uint16_t id,ModbusResponse* response){
  auto& self=*static_cast<FakeMaster*>(ctx);assert(id==19);
  if(self.pending)return MODBUS_RESULT_NOT_READY;
  response->state=self.result==MODBUS_RESULT_OK?MODBUS_TRANSACTION_COMPLETE:MODBUS_TRANSACTION_FAILED;response->result=self.result;
  response->slaveAddress=self.slave;response->function=self.function;response->exceptionCode=self.exception;response->registerCount=self.count;response->values[0]=0x1234;response->values[1]=0xabcd;
  return MODBUS_RESULT_OK;
 }
 static void cancel(void* ctx,uint8_t owner){
  auto& self=*static_cast<FakeMaster*>(ctx);
  self.pending=false;++self.cancellations;self.cancelledOwner=owner;
 }
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

 // FC04 must retain its function code and register values in the reply.
 fake.function=4;fake.result=MODBUS_RESULT_OK;fake.count=2;
 const uint8_t inputRegisters[]={4,0,16,0,2};
 const auto inputLength=encodeAdu(input,sizeof(input),0x4340,4,inputRegisters,sizeof(inputRegisters));
 assert(bridge.start(input,inputLength,{19200,1,1},201,3000,service));
 assert(fake.submitted.function==4&&fake.submitted.registerCount==2);
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(header.transactionId==0x4340&&pduLength==6&&pdu[0]==4);
 assert(readBe16(pdu+2)==0x1234&&readBe16(pdu+4)==0xabcd);
 fake.function=3;
 // The FC04 test reused the input buffer: restore the original FC03 ADU
 // before testing cancellation, RTU exceptions, and gateway errors.
 assert(encodeAdu(input,sizeof(input),0x4321,4,requestPdu,sizeof(requestPdu))==n);
 // Cancellation releases the pending transaction without generating a stale reply.
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 assert(bridge.state()==TransactionBridge::State::Pending);
 bridge.cancel();
 assert(fake.cancellations==1&&fake.cancelledOwner==201);
 assert(!bridge.busy());
 assert(!bridge.takeResponse(output,sizeof(output),length));
 // A real RTU exception must preserve its exception code.
 fake.result=MODBUS_RESULT_EXCEPTION;fake.exception=2;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==2);
 // RTU timeout maps to gateway target failed to respond (0x0B).
 fake.result=MODBUS_RESULT_TIMEOUT;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==0x0b);
 // Reject a successful RTU response from a different slave.
 fake.result=MODBUS_RESULT_OK;fake.slave=5;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==4);
 // Reject truncated read results.
 fake.slave=4;fake.count=1;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==4);
 // A mismatched exception must not be forwarded as if it came from this device.
 fake.result=MODBUS_RESULT_EXCEPTION;fake.exception=2;fake.slave=5;fake.count=2;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==4);
 // Scheduler queue saturation must yield an immediate Modbus gateway exception.
 fake.slave=4;fake.submitResult=MODBUS_RESULT_QUEUE_FULL;
 assert(bridge.start(input,n,{19200,1,1},201,3000,service));
 assert(bridge.state()==TransactionBridge::State::ResponseReady);
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x83&&pdu[1]==0x0a);
 fake.submitResult=MODBUS_RESULT_OK;
 fake.result=MODBUS_RESULT_OK;fake.slave=4;fake.function=6;fake.count=1;
 const uint8_t writeSingle[]={6,0,16,0x12,0x34};
 const auto singleLength=encodeAdu(input,sizeof(input),0x4322,4,writeSingle,sizeof(writeSingle));
 assert(bridge.start(input,singleLength,{9600,0,1},201,3000,service));
 assert(fake.submitted.function==6&&fake.submitted.registerAddress==16);
 assert(fake.submitted.values[0]==0x1234);
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(header.transactionId==0x4322&&pduLength==5&&pdu[0]==6);
 assert(readBe16(pdu+1)==16&&readBe16(pdu+3)==0x1234);
 fake.function=16;fake.count=2;
 const uint8_t writeMultiple[]={16,0,20,0,2,4,0x12,0x34,0xab,0xcd};
 const auto multiLength=encodeAdu(input,sizeof(input),0x4323,4,writeMultiple,sizeof(writeMultiple));
 assert(bridge.start(input,multiLength,{9600,0,1},201,3000,service));
 assert(fake.submitted.function==16&&fake.submitted.registerAddress==20);
 assert(fake.submitted.registerCount==2&&fake.submitted.values[0]==0x1234);
 assert(fake.submitted.values[1]==0xabcd);
 fake.pending=false;bridge.tick();
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(header.transactionId==0x4323&&pduLength==5&&pdu[0]==16);
 assert(readBe16(pdu+1)==20&&readBe16(pdu+3)==2);
 const uint8_t unsupported[]={1,0,0,0,1};
 const auto m=encodeAdu(input,sizeof(input),7,4,unsupported,sizeof(unsupported));
 assert(bridge.start(input,m,{9600,0,1},201,3000,service));
 assert(bridge.takeResponse(output,sizeof(output),length));
 assert(decodeAdu(output,length,header,pdu,pduLength));
 assert(pduLength==2&&pdu[0]==0x81&&pdu[1]==1);
}
