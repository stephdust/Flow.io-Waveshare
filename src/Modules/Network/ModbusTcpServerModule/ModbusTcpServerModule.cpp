#include "ModbusTcpServerModule.h"
#include "Modules/PoolDeviceModule/PoolDeviceModule.h"

void ModbusTcpServerModule::setPoolDeviceModule(PoolDeviceModule* devices) {
    devices_ = devices;
    resolver_.setDeviceLookup(&ModbusTcpServerModule::lookupDevice_, this);
}

bool ModbusTcpServerModule::lookupDevice_(void* context, uint16_t deviceId,
                                          SerialLineProfile& out, uint8_t& slaveAddress) {
    const auto* module = static_cast<const ModbusTcpServerModule*>(context);
    return module && module->devices_ &&
        module->devices_->serialDeviceInfo(deviceId, out, nullptr, 0U, &slaveAddress);
}

bool ModbusTcpServerModule::readPort(uint8_t index, ModbusTcpServer::PortConfig& out) const
{
    if (!ModbusTcpServer::validPortIndex(index)) return false;
    out = ModbusTcpServer::PortConfig{};
    out.tcpPort = ModbusTcpServer::kPorts[index];
    Preferences prefs;
    if (!prefs.begin(NvsKeys::StorageNamespace, true)) return true;
    char key[12]{};
    snprintf(key, sizeof(key), "mbtcp%u", (unsigned)index);
    StoredPort stored{};
    const bool saved = prefs.getBytesLength(key) == sizeof(stored) &&
        prefs.getBytes(key, &stored, sizeof(stored)) == sizeof(stored) &&
        stored.version == kConfigVersion &&
        ModbusTcpServer::validConfig(index, stored.config);
    prefs.end();
    if (saved) out = stored.config;
    return true;
}

bool ModbusTcpServerModule::serialDeviceInfo(uint16_t id, SerialLineProfile& line,
                                             char* label, size_t labelCapacity, uint8_t* slaveAddress) const
{
    return devices_ && devices_->serialDeviceInfo(id, line, label, labelCapacity, slaveAddress);
}
