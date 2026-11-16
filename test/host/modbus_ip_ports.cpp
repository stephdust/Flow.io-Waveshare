#include <cassert>
#include <cstring>
#include "Modules/Network/ModbusIpServerModule/ModbusIpPortConfig.h"
#include "Modules/Network/ModbusIpServerModule/ModbusIpTransactionBridge.h"
using namespace flowio::modbus_ip;
struct Fake {
 ModbusRequest sent{};
 bool pending=true;
 static ModbusResultCode submit(void* ctx,const ModbusRequest* req,uint16_t* id) {
  auto& f=*static_cast<Fake*>(ctx);f.sent=*req;*id=1;return MODBUS_RESULT_OK;
 }
 static ModbusResultCode poll(void* ctx,uint16_t,ModbusResponse* out) {
  auto& f=*static_cast<Fake*>(ctx);
  if(f.pending)return MODBUS_RESULT_NOT_READY;
  out->state=MODBUS_TRANSACTION_COMPLETE;out->result=MODBUS_RESULT_OK;
  out->slaveAddress=f.sent.slaveAddress;out->function=3;
  out->registerCount=1;out->values[0]=0x1234;
  return MODBUS_RESULT_OK;
 }
};
int main() {
 PortConfig port{};
 assert(parsePortConfig("1:1:1:0:3:9600:0:1",port));
 assert(port.enabled&&port.tcp&&port.udp&&port.mode==0&&port.target==3);
 assert(port.timeoutMs==3000); // legacy eight-field NVS config
 assert(parsePortConfig("1:1:0:1:17:19200:1:2",port));
 assert(port.mode==1&&port.target==17&&port.serial.baud==19200&&port.serial.parity==1);
 assert(parsePortConfig("1:1:0:1:17:19200:1:2:1250",port));
 assert(port.timeoutMs==1250);
 assert(!port.cacheEnabled&&port.cacheTtlMs==800&&port.timeoutBehavior==0);
 assert(parsePortConfig("1:1:1:1:17:19200:1:2:1250:1:800:1",port));
 assert(port.cacheEnabled&&port.cacheTtlMs==800&&port.timeoutBehavior==1);
 assert(!validPortConfigText("1:1:1:1:17:19200:1:2:1250:2:800:1"));
 assert(!validPortConfigText("1:1:1:1:17:19200:1:2:1250:1:0:1"));
 assert(!validPortConfigText("1:1:1:1:17:19200:1:2:1250:1:800:2"));
 assert(!validPortConfigText("1:1:0:1:17:19200:1:2:9"));
 assert(!validPortConfigText("1:1:0:1:17:19200:1:2:5001"));
 assert(!validPortConfigText("1:1:0:1:17:19200:1:2:1250:garbage"));
 assert(!validPortConfigText("1:1:0:1:0:9600:0:1"));
 assert(!validPortConfigText("1:1:0:1:248:9600:0:1"));
 assert(!validPortConfigText("1:1:0:1:17:9600:3:1"));
 assert(!validPortConfigText("1:1:0:1:17:9600:0:1:garbage"));
 assert(!validPortConfigText("1:1:0:1:17:9600:0"));
 Fake fake{};
 ModbusMasterService service{&Fake::submit,&Fake::poll,nullptr,nullptr,&fake};
 uint8_t input[32]{};
 const uint8_t pdu[]={3,0,52,0,1};
 const auto n=encodeAdu(input,sizeof(input),0x2233,99,pdu,sizeof(pdu));
 TransactionBridge bridge{};
 assert(bridge.start(input,n,{19200,1,2},201,3000,service,17));
 assert(fake.sent.slaveAddress==17&&fake.sent.line.baud==19200);
 fake.pending=false;bridge.tick();
 uint8_t output[32]{};std::size_t length=0;
 assert(bridge.takeResponse(output,sizeof(output),length));
 MbapHeader header{};const uint8_t* responsePdu=nullptr;std::size_t responseSize=0;
 assert(decodeAdu(output,length,header,responsePdu,responseSize));
 assert(header.transactionId==0x2233&&header.unitId==99);
 assert(responseSize==4&&responsePdu[0]==3&&responsePdu[1]==2);
 return 0;
}
