#include <cassert>
#include "Modules/Network/ModbusIpServerModule/ModbusIpKnownDeviceProfile.h"

int main() {
 using namespace flowio::modbus_ip;
 PoolDriverConfig device{};
 device.capabilities.kind=PoolControlKind::Rs485;
 device.serial.protocol=RegisterWireProtocol::ModbusRtu;
 device.serial.address=17;
 device.serial.line.busId=0;
 device.serial.line.baud=19200;
 device.serial.line.parity=1;
 device.serial.line.stopBits=2;
 SerialProfile selected{};
 assert(profileFromPoolSerialConfig(device,17,selected));
 assert(selected.baud==19200&&selected.parity==1&&selected.stopBits==2);
 assert(!profileFromPoolSerialConfig(device,18,selected));
 device.serial.protocol=RegisterWireProtocol::AquaGem;
 assert(!profileFromPoolSerialConfig(device,17,selected));
 device.serial.protocol=RegisterWireProtocol::ModbusRtu;
 device.serial.line.busId=1;
 assert(!profileFromPoolSerialConfig(device,17,selected));
 device.serial.line.busId=0;
 device.serial.line.baud=0;
 assert(!profileFromPoolSerialConfig(device,17,selected));
 device.serial.line.baud=9600;
 device.capabilities.kind=PoolControlKind::Relay;
 assert(!profileFromPoolSerialConfig(device,17,selected));
 bool found=false;
 SerialProfile merged{};
 assert(mergeKnownDeviceProfile({9600,0,1},found,merged));
 assert(found&&merged.baud==9600);
 assert(mergeKnownDeviceProfile({9600,0,1},found,merged));
 assert(!mergeKnownDeviceProfile({19200,0,1},found,merged));
 assert(merged.baud==9600);
 assert(!mergeKnownDeviceProfile({9600,3,1},found,merged));
}
