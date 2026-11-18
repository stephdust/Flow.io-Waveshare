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

// Editable Home Assistant configuration entities on the existing HAService.
// Commands use Flow.io's authenticated MQTT broker and native cfg/set path,
// which validates and persists each field before republishing the state.
// Active TCP/RS485 listeners still apply the new settings on the next reboot.
constexpr HASelectEntry kModbusHaSelects[] = {
    {"modbustcp", "modbus_tcp_502_mode", "Modbus 502 Liaison RS485", "cfg/modbustcp/502", "{{ {0:'Aucun',1:'Equipement Flow.io',2:'Manuel'}.get(value_json.mode | int,'Aucun') }}", "cfg/set", "{{ {'modbustcp502': {'mode': {'Aucun':0,'Equipement Flow.io':1,'Manuel':2}.get(value,0)}} | to_json }}", "[\"Aucun\",\"Equipement Flow.io\",\"Manuel\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_502_parity", "Modbus 502 Parite RS485", "cfg/modbustcp/502", "{{ {0:'Aucune',1:'Paire',2:'Impaire'}.get(value_json.parity | int,'Aucune') }}", "cfg/set", "{{ {'modbustcp502': {'parity': {'Aucune':0,'Paire':1,'Impaire':2}.get(value,0)}} | to_json }}", "[\"Aucune\",\"Paire\",\"Impaire\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_502_stop_bits", "Modbus 502 Bits stop RS485", "cfg/modbustcp/502", "{{ {1:'1',2:'2'}.get(value_json.stop_bits | int,'1') }}", "cfg/set", "{{ {'modbustcp502': {'stop_bits': {'1':1,'2':2}.get(value,1)}} | to_json }}", "[\"1\",\"2\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_502_error_mode", "Modbus 502 Erreur Modbus", "cfg/modbustcp/502", "{{ {0:'Exception Modbus',1:'Silence'}.get(value_json.error_mode | int,'Exception Modbus') }}", "cfg/set", "{{ {'modbustcp502': {'error_mode': {'Exception Modbus':0,'Silence':1}.get(value,0)}} | to_json }}", "[\"Exception Modbus\",\"Silence\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_503_mode", "Modbus 503 Liaison RS485", "cfg/modbustcp/503", "{{ {0:'Aucun',1:'Equipement Flow.io',2:'Manuel'}.get(value_json.mode | int,'Aucun') }}", "cfg/set", "{{ {'modbustcp503': {'mode': {'Aucun':0,'Equipement Flow.io':1,'Manuel':2}.get(value,0)}} | to_json }}", "[\"Aucun\",\"Equipement Flow.io\",\"Manuel\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_503_parity", "Modbus 503 Parite RS485", "cfg/modbustcp/503", "{{ {0:'Aucune',1:'Paire',2:'Impaire'}.get(value_json.parity | int,'Aucune') }}", "cfg/set", "{{ {'modbustcp503': {'parity': {'Aucune':0,'Paire':1,'Impaire':2}.get(value,0)}} | to_json }}", "[\"Aucune\",\"Paire\",\"Impaire\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_503_stop_bits", "Modbus 503 Bits stop RS485", "cfg/modbustcp/503", "{{ {1:'1',2:'2'}.get(value_json.stop_bits | int,'1') }}", "cfg/set", "{{ {'modbustcp503': {'stop_bits': {'1':1,'2':2}.get(value,1)}} | to_json }}", "[\"1\",\"2\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_503_error_mode", "Modbus 503 Erreur Modbus", "cfg/modbustcp/503", "{{ {0:'Exception Modbus',1:'Silence'}.get(value_json.error_mode | int,'Exception Modbus') }}", "cfg/set", "{{ {'modbustcp503': {'error_mode': {'Exception Modbus':0,'Silence':1}.get(value,0)}} | to_json }}", "[\"Exception Modbus\",\"Silence\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_504_mode", "Modbus 504 Liaison RS485", "cfg/modbustcp/504", "{{ {0:'Aucun',1:'Equipement Flow.io',2:'Manuel'}.get(value_json.mode | int,'Aucun') }}", "cfg/set", "{{ {'modbustcp504': {'mode': {'Aucun':0,'Equipement Flow.io':1,'Manuel':2}.get(value,0)}} | to_json }}", "[\"Aucun\",\"Equipement Flow.io\",\"Manuel\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_504_parity", "Modbus 504 Parite RS485", "cfg/modbustcp/504", "{{ {0:'Aucune',1:'Paire',2:'Impaire'}.get(value_json.parity | int,'Aucune') }}", "cfg/set", "{{ {'modbustcp504': {'parity': {'Aucune':0,'Paire':1,'Impaire':2}.get(value,0)}} | to_json }}", "[\"Aucune\",\"Paire\",\"Impaire\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_504_stop_bits", "Modbus 504 Bits stop RS485", "cfg/modbustcp/504", "{{ {1:'1',2:'2'}.get(value_json.stop_bits | int,'1') }}", "cfg/set", "{{ {'modbustcp504': {'stop_bits': {'1':1,'2':2}.get(value,1)}} | to_json }}", "[\"1\",\"2\"]", "mdi:tune", "config"},
    {"modbustcp", "modbus_tcp_504_error_mode", "Modbus 504 Erreur Modbus", "cfg/modbustcp/504", "{{ {0:'Exception Modbus',1:'Silence'}.get(value_json.error_mode | int,'Exception Modbus') }}", "cfg/set", "{{ {'modbustcp504': {'error_mode': {'Exception Modbus':0,'Silence':1}.get(value,0)}} | to_json }}", "[\"Exception Modbus\",\"Silence\"]", "mdi:tune", "config"},
};
constexpr HANumberEntry kModbusHaNumbers[] = {
    {"modbustcp", "modbus_tcp_502_device_id", "Modbus 502 Equipement RS485", "cfg/modbustcp/502", "{{ value_json.device_id | int }}", "cfg/set", "{{ {'modbustcp502': {'device_id': value | int}} | to_json }}", 0, (float)(POOL_DEVICE_MAX - 1U), 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_502_baud", "Modbus 502 Baud RS485", "cfg/modbustcp/502", "{{ value_json.baud | int }}", "cfg/set", "{{ {'modbustcp502': {'baud': value | int}} | to_json }}", 1200, 115200, 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_502_timeout_ms", "Modbus 502 Timeout Modbus (ms)", "cfg/modbustcp/502", "{{ value_json.timeout_ms | int }}", "cfg/set", "{{ {'modbustcp502': {'timeout_ms': value | int}} | to_json }}", 100, 120000, 100, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_503_device_id", "Modbus 503 Equipement RS485", "cfg/modbustcp/503", "{{ value_json.device_id | int }}", "cfg/set", "{{ {'modbustcp503': {'device_id': value | int}} | to_json }}", 0, (float)(POOL_DEVICE_MAX - 1U), 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_503_baud", "Modbus 503 Baud RS485", "cfg/modbustcp/503", "{{ value_json.baud | int }}", "cfg/set", "{{ {'modbustcp503': {'baud': value | int}} | to_json }}", 1200, 115200, 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_503_timeout_ms", "Modbus 503 Timeout Modbus (ms)", "cfg/modbustcp/503", "{{ value_json.timeout_ms | int }}", "cfg/set", "{{ {'modbustcp503': {'timeout_ms': value | int}} | to_json }}", 100, 120000, 100, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_504_device_id", "Modbus 504 Equipement RS485", "cfg/modbustcp/504", "{{ value_json.device_id | int }}", "cfg/set", "{{ {'modbustcp504': {'device_id': value | int}} | to_json }}", 0, (float)(POOL_DEVICE_MAX - 1U), 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_504_baud", "Modbus 504 Baud RS485", "cfg/modbustcp/504", "{{ value_json.baud | int }}", "cfg/set", "{{ {'modbustcp504': {'baud': value | int}} | to_json }}", 1200, 115200, 1, "box", "config", "mdi:tune", nullptr},
    {"modbustcp", "modbus_tcp_504_timeout_ms", "Modbus 504 Timeout Modbus (ms)", "cfg/modbustcp/504", "{{ value_json.timeout_ms | int }}", "cfg/set", "{{ {'modbustcp504': {'timeout_ms': value | int}} | to_json }}", 100, 120000, 100, "box", "config", "mdi:tune", nullptr},
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
                    if (ok) {
                        // Persist every field BEFORE the migration marker.
                        // A partial or interrupted migration must be retried,
                        // not silently treated as complete on next boot.
                        const bool fieldsSaved =
                            cfg.persistRegisteredValue(&p.deviceId) &&
                            cfg.persistRegisteredValue(&p.baud) &&
                            cfg.persistRegisteredValue(&p.parity) &&
                            cfg.persistRegisteredValue(&p.stopBits) &&
                            cfg.persistRegisteredValue(&p.timeoutMs) &&
                            cfg.persistRegisteredValue(&p.errorMode);
                        if (fieldsSaved && cfg.set(p.modeVar, mode))
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
    if (ha) {
        if (ha->addSelect)
            for (const auto& entry : kModbusHaSelects)
                (void)ha->addSelect(ha->ctx, &entry);
        if (ha->addNumber)
            for (const auto& entry : kModbusHaNumbers)
                (void)ha->addNumber(ha->ctx, &entry);
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
