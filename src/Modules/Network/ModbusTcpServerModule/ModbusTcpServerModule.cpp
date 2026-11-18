#include "ModbusTcpServerModule.h"
#include "Modules/PoolDeviceModule/PoolDeviceModule.h"
#include "Modules/PoolDeviceModule/PoolDeviceModuleDataModel.h"
#include <new>

namespace {
constexpr uint8_t kModbusConfigProducerId = 91U;
constexpr MqttConfigRouteProducer::Route kModbusConfigRoutes[] = {
    {1, {(uint8_t)ConfigModuleId::ModbusTcpServer, 1U},
     "modbustcp502", "modbustcp/502", (uint8_t)MqttPublishPriority::Normal, nullptr},
    {2, {(uint8_t)ConfigModuleId::ModbusTcpServer, 2U},
     "modbustcp503", "modbustcp/503", (uint8_t)MqttPublishPriority::Normal, nullptr},
    {3, {(uint8_t)ConfigModuleId::ModbusTcpServer, 3U},
     "modbustcp504", "modbustcp/504", (uint8_t)MqttPublishPriority::Normal, nullptr}
};

// One read-only Home Assistant diagnostic entity per TCP port, with ALL
// persistent settings published as attributes on the same retained cfg topic.
// HA settings follow the usual Flow.io MQTT discovery/availability mechanism.
constexpr const char* kModeStateTemplate =
    "{{ 'Aucun' if value_json.mode == 0 else "
    "('Equipement Flow.io' if value_json.mode == 1 else 'Manuel') }}";
constexpr const char* kConfigAttributesTemplate = "{{ value_json | to_json }}";
constexpr HASensorEntry kModbusHaPortSensors[] = {
    {"modbustcp", "modbus_tcp_502", "Modbus TCP 502", "cfg/modbustcp/502",
     kModeStateTemplate, "diagnostic", "mdi:lan-connect", nullptr, false, nullptr,
     true, kConfigAttributesTemplate},
    {"modbustcp", "modbus_tcp_503", "Modbus TCP 503", "cfg/modbustcp/503",
     kModeStateTemplate, "diagnostic", "mdi:lan-connect", nullptr, false, nullptr,
     true, kConfigAttributesTemplate},
    {"modbustcp", "modbus_tcp_504", "Modbus TCP 504", "cfg/modbustcp/504",
     kModeStateTemplate, "diagnostic", "mdi:lan-connect", nullptr, false, nullptr,
     true, kConfigAttributesTemplate}
};
} // namespace

void ModbusTcpServerModule::init(ConfigStore& cfg, ServiceRegistry& services)
{
    registry_ = &services;
    master_ = services.get<ModbusMasterService>(ServiceId::ModbusMaster);
    constexpr uint8_t kModule = (uint8_t)ConfigModuleId::ModbusTcpServer;
    for (uint8_t i = 0U; i < ModbusTcpServer::kPortCount; ++i) {
        ConfigPort& p = portSettings_[i];
        const uint8_t branch = i + 1U;
        cfg.registerVar(p.modeVar, kModule, branch);
        cfg.registerVar(p.deviceVar, kModule, branch);
        cfg.registerVar(p.baudVar, kModule, branch);
        cfg.registerVar(p.parityVar, kModule, branch);
        cfg.registerVar(p.stopBitsVar, kModule, branch);
        cfg.registerVar(p.timeoutVar, kModule, branch);
        cfg.registerVar(p.errorVar, kModule, branch);
    }
    (void)cfg.registerValidator(&ModbusTcpServerModule::validateConfigCandidate_, this);
}

bool ModbusTcpServerModule::validateConfigCandidate_(
    void* context, const ConfigCandidate& candidate)
{
    const auto* self = static_cast<const ModbusTcpServerModule*>(context);
    if (!self) return false;
    for (uint8_t i = 0U; i < ModbusTcpServer::kPortCount; ++i) {
        const ConfigPort& p = self->portSettings_[i];
        uint8_t mode{}, parity{}, stop{}, error{};
        uint16_t device{};
        int32_t baud{}, timeout{};
        if (!candidate.read(p.modeVar, p.mode, mode) ||
            !candidate.read(p.deviceVar, p.deviceId, device) ||
            !candidate.read(p.baudVar, p.baud, baud) ||
            !candidate.read(p.parityVar, p.parity, parity) ||
            !candidate.read(p.stopBitsVar, p.stopBits, stop) ||
            !candidate.read(p.timeoutVar, p.timeoutMs, timeout) ||
            !candidate.read(p.errorVar, p.errorMode, error)) return false;
        if (mode > 2U || device >= POOL_DEVICE_MAX ||
            baud < 1200 || baud > 115200 || parity > 2U ||
            (stop != 1U && stop != 2U) ||
            timeout < 100 || timeout > 120000 || error > 1U) return false;
    }
    return true;
}

ModbusTcpServer::PortConfig ModbusTcpServerModule::fromSettings_(uint8_t index) const
{
    ModbusTcpServer::PortConfig config{};
    if (!ModbusTcpServer::validPortIndex(index)) return config;
    const ConfigPort& p = portSettings_[index];
    config.tcpPort = ModbusTcpServer::kPorts[index];
    config.enabled = p.mode != 0U;
    config.serialSource = p.mode == 2U
        ? ModbusTcpServer::SerialSource::Manual
        : ModbusTcpServer::SerialSource::FlowioDevice;
    config.deviceId = p.deviceId;
    config.manualLine.baud = (uint32_t)p.baud;
    config.manualLine.parity = p.parity;
    config.manualLine.stopBits = p.stopBits;
    config.transactionTimeoutMs = (uint32_t)p.timeoutMs;
    config.errorMode = p.errorMode == 1U
        ? ModbusTcpServer::ErrorMode::Silent
        : ModbusTcpServer::ErrorMode::ModbusException;
    return config;
}

void ModbusTcpServerModule::onConfigLoaded(ConfigStore& cfg, ServiceRegistry& services)
{
    for (uint8_t i = 0U; i < ModbusTcpServer::kPortCount; ++i) {
        // Import the original (single NVS blob per port) settings only once.
        // Write the mode key last as the migration completion marker, so
        // interrupted migrations can be retried without losing the old blob.
        bool migrated = false;
        if (cfg.persistentKeyExists(kConfigKeys_[i][0], migrated) && !migrated) {
            char oldKey[12]{};
            snprintf(oldKey, sizeof(oldKey), "mbtcp%u", (unsigned)i);
            StoredPort old{};
            size_t actual = 0U;
            if (cfg.readRuntimeBlob(oldKey, &old, sizeof(old), &actual) &&
                actual == sizeof(old) && old.version == kConfigVersion &&
                ModbusTcpServer::validConfig(i, old.config)) {
                const auto& saved = old.config;
                ConfigPort& p = portSettings_[i];
                const uint8_t mode = !saved.enabled ? 0U :
                    saved.serialSource == ModbusTcpServer::SerialSource::Manual ? 2U : 1U;
                const uint16_t device = saved.deviceId;
                const int32_t baud = (int32_t)saved.manualLine.baud;
                const uint8_t parity = saved.manualLine.parity;
                const uint8_t stop = saved.manualLine.stopBits;
                const int32_t timeout = (int32_t)saved.transactionTimeoutMs;
                const uint8_t error = saved.errorMode == ModbusTcpServer::ErrorMode::Silent ? 1U : 0U;
                // Copy only configurations that meet all new ConfigStore bounds.
                if (device < POOL_DEVICE_MAX && baud >= 1200 && baud <= 115200 &&
                    parity <= 2U && (stop == 1U || stop == 2U) &&
                    timeout >= 100 && timeout <= 120000) {
                    const bool ok =
                        cfg.set(p.deviceVar, device) &&
                        cfg.set(p.baudVar, baud) &&
                        cfg.set(p.parityVar, parity) &&
                        cfg.set(p.stopBitsVar, stop) &&
                        cfg.set(p.timeoutVar, timeout) &&
                        cfg.set(p.errorVar, error);
                    if (ok && cfg.set(p.modeVar, mode)) {
                        // set() skips writes when the value equals its default.
                        // Persist all variables anyway, mode last as a commit key.
                        (void)cfg.persistRegisteredValue(&p.deviceId);
                        (void)cfg.persistRegisteredValue(&p.baud);
                        (void)cfg.persistRegisteredValue(&p.parity);
                        (void)cfg.persistRegisteredValue(&p.stopBits);
                        (void)cfg.persistRegisteredValue(&p.timeoutMs);
                        (void)cfg.persistRegisteredValue(&p.errorMode);
                        (void)cfg.persistRegisteredValue(&p.mode);
                    }
                }
            }
        }
        const auto config = fromSettings_(i);
        if (ModbusTcpServer::validConfig(i, config)) (void)configurePort(i, config);
    }

    if (!cfgMqttPub_) cfgMqttPub_ = new (std::nothrow) MqttConfigRouteProducer();
    if (cfgMqttPub_) {
        cfgMqttPub_->configure(this, kModbusConfigProducerId,
            kModbusConfigRoutes,
            (uint8_t)(sizeof(kModbusConfigRoutes) / sizeof(kModbusConfigRoutes[0])),
            services);
    }

    const HAService* ha = services.get<HAService>(ServiceId::Ha);
    if (ha && ha->addSensor) {
        for (const auto& entry : kModbusHaPortSensors)
            (void)ha->addSensor(ha->ctx, &entry);
    }
}

void ModbusTcpServerModule::setPoolDeviceModule(PoolDeviceModule* devices)
{
    devices_ = devices;
    resolver_.setDeviceLookup(&ModbusTcpServerModule::lookupDevice_, this);
}

bool ModbusTcpServerModule::lookupDevice_(void* context, uint16_t deviceId,
                                          SerialLineProfile& out, uint8_t& slaveAddress)
{
    const auto* module = static_cast<const ModbusTcpServerModule*>(context);
    return module && module->devices_ &&
        module->devices_->serialDeviceInfo(deviceId, out, nullptr, 0U, &slaveAddress);
}

bool ModbusTcpServerModule::readPort(uint8_t index, ModbusTcpServer::PortConfig& out) const
{
    if (!ModbusTcpServer::validPortIndex(index)) return false;
    out = fromSettings_(index);
    return ModbusTcpServer::validConfig(index, out);
}

bool ModbusTcpServerModule::serialDeviceInfo(uint16_t id, SerialLineProfile& line,
                                             char* label, size_t labelCapacity,
                                             uint8_t* slaveAddress) const
{
    return devices_ && devices_->serialDeviceInfo(id, line, label, labelCapacity, slaveAddress);
}
