#pragma once
#include "Core/Services/IModbusMaster.h"
#include "ModbusIpRegisterCodec.h"
#include "ModbusIpProfileResolver.h"
namespace flowio::modbus_ip {
// Adapter only: all bus I/O stays in Flow.io's single RS485 scheduler.
inline bool makeSchedulerRequest(const RegisterRequest& source,const SerialProfile& profile,
 uint8_t ownerId,uint32_t timeoutMs,ModbusRequest& dest) {
 if(!ownerId||!validProfile(profile)||timeoutMs<10||timeoutMs>5000||
    source.unitId<1||source.unitId>247||source.count<1||source.count>32)return false;
 ModbusRequest request{};
 request.ownerId=ownerId;
 request.protocol=RegisterWireProtocol::ModbusRtu;
 request.slaveAddress=source.unitId;
 request.function=source.function;
 request.priority=MODBUS_PRIORITY_NORMAL;
 request.line.busId=0;
 request.line.baud=profile.baud;
 request.line.parity=profile.parity;
 request.line.stopBits=profile.stopBits;
 request.responseTimeoutMs=timeoutMs;
 request.transactionBudgetMs=timeoutMs+1000U;
 request.retries=0;
 request.registerAddress=source.address;
 request.registerCount=source.count;
 switch(source.kind) {
  case RequestKind::ReadRegisters:
   if(source.function!=3&&source.function!=4)return false;
   request.operation=RegisterOperation::Read;break;
  case RequestKind::WriteSingleRegister:
   if(source.function!=6||source.count!=1)return false;
   request.operation=RegisterOperation::WriteSingle;break;
  case RequestKind::WriteRegisters:
   if(source.function!=16)return false;
   request.operation=RegisterOperation::WriteMultiple;break;
  default:return false;
 }
 for(uint16_t i=0;i<source.count;++i)request.values[i]=source.values[i];
 dest=request;return true;
}
inline uint8_t gatewayExceptionCode(ModbusResultCode result) {
 switch(result) {
  case MODBUS_RESULT_TIMEOUT:
  case MODBUS_RESULT_EXPIRED:
  case MODBUS_RESULT_CRC_ERROR:
  case MODBUS_RESULT_PROTOCOL_ERROR:
  case MODBUS_RESULT_IO_ERROR:return 0x0b; // Gateway target failed to respond
  case MODBUS_RESULT_QUEUE_FULL:
  case MODBUS_RESULT_NOT_READY:return 0x0a; // Gateway path unavailable
  default:return 0x04; // Slave device failure
 }
}
}
