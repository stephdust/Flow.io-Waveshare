#pragma once
#include "Core/Services/PoolActuatorTypes.h"
#include "ModbusIpProfiles.h"

namespace flowio::modbus_ip {

// Convert an existing Flow.io pool device's serial configuration to a
// standard Modbus RTU gateway profile. Proprietary RS485 protocols (such as
// AquaGem) must never be addressed with standard Modbus function codes.
inline bool profileFromPoolSerialConfig(const PoolDriverConfig& device,
                                        uint8_t unitId,
                                        SerialProfile& out) {
 if(unitId<1||unitId>247 ||
    device.capabilities.kind!=PoolControlKind::Rs485 ||
    device.serial.protocol!=RegisterWireProtocol::ModbusRtu ||
    device.serial.address!=unitId ||
    device.serial.line.busId!=0) return false;
 const SerialProfile candidate{device.serial.line.baud,
                               device.serial.line.parity,
                               device.serial.line.stopBits};
 if(!validProfile(candidate))return false;
 out=candidate;
 return true;
}

// Preserve a single unambiguous line configuration when multiple Flow.io
// device slots refer to the same Modbus address.
inline bool mergeKnownDeviceProfile(const SerialProfile& candidate,
                                   bool& found,
                                   SerialProfile& selected) {
 if(!validProfile(candidate))return false;
 if(found&&(selected.baud!=candidate.baud||
            selected.parity!=candidate.parity||
            selected.stopBits!=candidate.stopBits))return false;
 selected=candidate;
 found=true;
 return true;
}

} // namespace flowio::modbus_ip
