#include "ModbusTcpServerModule.h"
#include "Modules/PoolDeviceModule/PoolDeviceModule.h"

void ModbusTcpServerModule::setPoolDeviceModule(PoolDeviceModule* devices) {
    devices_ = devices;
    resolver_.setDeviceLookup(&ModbusTcpServerModule::lookupDevice_, this);
}

bool ModbusTcpServerModule::lookupDevice_(void* context, uint16_t deviceId,
                                          SerialLineProfile& out) {
    const auto* module = static_cast<const ModbusTcpServerModule*>(context);
    return module && module->devices_ &&
        module->devices_->serialLineForDevice(deviceId, out);
}
