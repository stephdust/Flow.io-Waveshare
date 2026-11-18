#pragma once
/**
 * @brief Flow.io lifecycle adapter for three Modbus TCP listeners.
 * Disabled by default until ports have valid explicit configuration.
 */
#include "Core/Module.h"
#include "Core/Services/IModbusMaster.h"
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpLineResolver.h"
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpSocketServer.h"

class PoolDeviceModule;

class ModbusTcpServerModule : public Module {
public:
    ModuleId moduleId() const override { return ModuleId::Reserved28; }
    const char* taskName() const override { return "modbustcp"; }
    uint8_t dependencyCount() const override { return 3; }
    ModuleId dependency(uint8_t i) const override {
        if (i == 0) return ModuleId::Io;
        if (i == 1) return ModuleId::PoolDevice;
        if (i == 2) return ModuleId::Wifi;
        return ModuleId::Unknown;
    }
    uint8_t taskCount() const override { return 1; }
    const ModuleTaskSpec* taskSpecs() const override { return singleLoopTaskSpec(); }
    uint16_t taskStackSize() const override { return 4096; }
    void init(ConfigStore&, ServiceRegistry& services) override {
        master_ = services.get<ModbusMasterService>(ServiceId::ModbusMaster);
    }
    void onStart(ConfigStore&, ServiceRegistry&) override {
        if (!master_ || !master_->submit || !master_->poll) return;
        bool enabled = false;
        for (uint8_t i = 0; i < ModbusTcpServer::kPortCount; ++i)
            enabled = enabled || configs_[i].enabled;
        if (!enabled) return;
        server_.begin(*master_, &ModbusTcpServer::LineResolver::resolveStatic, &resolver_);
        running_ = true;
    }
    void loop() override {
        if (running_) server_.tick(millis());
    }
    void setPoolDeviceModule(PoolDeviceModule* devices);
    bool configurePort(uint8_t index, const ModbusTcpServer::PortConfig& config) {
        if (running_ || !ModbusTcpServer::validConfig(index, config)) return false;
        configs_[index] = config;
        resolver_.configure(index, config);
        server_.configure(index, config);
        return true;
    }
    const ModbusTcpServer::PortStats& portStats(uint8_t index) const {
        return server_.stats(index);
    }
private:
    static bool lookupDevice_(void* context, uint16_t deviceId, SerialLineProfile& out);
    PoolDeviceModule* devices_ = nullptr;
    const ModbusMasterService* master_ = nullptr;
    ModbusTcpServer::LineResolver resolver_{};
    ModbusTcpServer::SocketServer server_{};
    ModbusTcpServer::PortConfig configs_[ModbusTcpServer::kPortCount]{};
    bool running_ = false;
};
