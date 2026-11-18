#pragma once
/**
 * @brief Flow.io lifecycle adapter for three Modbus TCP listeners.
 * Disabled by default until ports have valid explicit configuration.
 */
#include "Core/Module.h"
#include <esp_heap_caps.h>
#include <Preferences.h>
#include "Core/NvsKeys.h"
#include "Core/Services/IModbusMaster.h"
#include "Core/Services/INetworkAccess.h"
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpLineResolver.h"
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpSocketServer.h"

class PoolDeviceModule;

class ModbusTcpServerModule : public Module {
public:
    ModuleId moduleId() const override { return ModuleId::ModbusTcpServer; }
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
        registry_ = &services;
        master_ = services.get<ModbusMasterService>(ServiceId::ModbusMaster);
    }
    void onConfigLoaded(ConfigStore&, ServiceRegistry&) override {
        Preferences prefs;
        if (!prefs.begin(NvsKeys::StorageNamespace, true)) return;
        for (uint8_t i = 0; i < ModbusTcpServer::kPortCount; ++i) {
            char key[12]{};
            snprintf(key, sizeof(key), "mbtcp%u", unsigned(i));
            StoredPort stored{};
            if (prefs.getBytesLength(key) != sizeof(stored) ||
                prefs.getBytes(key, &stored, sizeof(stored)) != sizeof(stored) ||
                stored.version != kConfigVersion) continue;
            const auto& cfg = stored.config;
            if (ModbusTcpServer::validConfig(i, cfg)) configurePort(i, cfg);
        }
        prefs.end();
    }
    /** Persist one port atomically; changes take effect on next restart. */
    bool savePort(uint8_t index, const ModbusTcpServer::PortConfig& config) {
        if (!ModbusTcpServer::validConfig(index, config)) return false;
        Preferences prefs;
        if (!prefs.begin(NvsKeys::StorageNamespace, false)) return false;
        char key[12]{};
        snprintf(key, sizeof(key), "mbtcp%u", unsigned(index));
        StoredPort stored{};
        stored.version = kConfigVersion;
        stored.config = config;
        const bool ok = prefs.putBytes(key, &stored, sizeof(stored)) == sizeof(stored);
        prefs.end();
        if (ok && !running_) configurePort(index, config);
        return ok;
    }
    void onStart(ConfigStore&, ServiceRegistry&) override {
        // Wait for an actual station/Ethernet IP before binding sockets.
        // Never expose the unauthenticated Modbus protocol on provisioning AP.
        eligible_ = master_ && master_->submit && master_->poll;
    }
    void loop() override {
        if (!eligible_) return;
        const NetworkAccessService* network =
            registry_ ? registry_->get<NetworkAccessService>(ServiceId::NetworkAccess) : nullptr;
        const bool stationConnected = network && network->mode &&
            network->mode(network->ctx) == NetworkAccessMode::Station;
        if (!stationConnected) {
            if (running_) {
                server_.stop();
                running_ = false;
            }
            return;
        }
        if (!running_) {
            bool enabled = false;
            for (uint8_t i = 0; i < ModbusTcpServer::kPortCount; ++i)
                enabled = enabled || configs_[i].enabled;
            if (!enabled) return;
            server_.begin(*master_, &ModbusTcpServer::LineResolver::resolveStatic, &resolver_);
            running_ = true;
        }
        const uint32_t now = millis();
        server_.tick(now);
        if (uint32_t(now - lastDiagnosticsMs_) < 60000U) return;
        lastDiagnosticsMs_ = now;
        ModbusMasterStats queue{};
        if (master_ && master_->stats) (void)master_->stats(master_->ctx, &queue);
        const uint32_t freeInternal = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
        const uint32_t largestInternal = heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
        const uint32_t minInternal = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
        const uint32_t fragEstimate = freeInternal ?
            100U - (largestInternal * 100U / freeInternal) : 0U;
        const uint32_t freePsram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
        const uint32_t largestPsram = heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);
        const uint32_t stackWatermark = uxTaskGetStackHighWaterMark(nullptr);
        Serial.printf("[MODBUS-TCP] heap_internal=%lu min_internal=%lu largest_internal=%lu frag_est_percent=%lu psram=%lu largest_psram=%lu stack_hwm=%lu rtu_queue=%u rtu_peak=%u rtu_rejected=%lu rtu_crc=%lu rtu_timeouts=%lu\n",
            (unsigned long)freeInternal, (unsigned long)minInternal,
            (unsigned long)largestInternal, (unsigned long)fragEstimate,
            (unsigned long)freePsram, (unsigned long)largestPsram,
            (unsigned long)stackWatermark, (unsigned)queue.queued,
            (unsigned)queue.queuedPeak, (unsigned long)queue.queueRejected,
            (unsigned long)queue.crcErrors, (unsigned long)queue.timeouts);
        for (uint8_t i = 0; i < ModbusTcpServer::kPortCount; ++i) {
            const auto& p = server_.stats(i);
            Serial.printf("[MODBUS-TCP] port=%u clients=%u peak_clients=%u requests=%lu replies=%lu exceptions=%lu silent=%lu crc=%lu timeouts=%lu rejected=%lu tcp_max_ms=%lu rtu_queue_max_ms=%lu rtu_response_max_ms=%lu\n",
                (unsigned)ModbusTcpServer::kPorts[i], (unsigned)p.activeClients,
                (unsigned)p.maxActiveClients, (unsigned long)p.received,
                (unsigned long)p.completed, (unsigned long)p.exceptionsSent,
                (unsigned long)p.silentFailures, (unsigned long)p.crcErrors,
                (unsigned long)p.timeouts, (unsigned long)p.connectionsRejected,
                (unsigned long)p.responseTimeMaxMs, (unsigned long)p.queueWaitMaxMs,
                (unsigned long)p.rtuResponseMaxMs);
        }
    }
    void setPoolDeviceModule(PoolDeviceModule* devices);
    /** Read persisted settings (or disabled defaults when not configured). */
    bool readPort(uint8_t index, ModbusTcpServer::PortConfig& out) const;
    /** Get a serial device selectable in the web interface. */
    bool serialDeviceInfo(uint16_t id, SerialLineProfile& line,
                          char* label, size_t labelCapacity,
                          uint8_t* slaveAddress = nullptr) const;
    bool running() const { return running_; }
    bool schedulerStats(ModbusMasterStats& out) const {
        return master_ && master_->stats && master_->stats(master_->ctx, &out);
    }
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
    static constexpr uint32_t kConfigVersion = 1U;
    struct StoredPort {
        uint32_t version = 0U;
        ModbusTcpServer::PortConfig config{};
    };
    static bool lookupDevice_(void* context, uint16_t deviceId,
                              SerialLineProfile& out, uint8_t& slaveAddress);
    PoolDeviceModule* devices_ = nullptr;
    ServiceRegistry* registry_ = nullptr;
    const ModbusMasterService* master_ = nullptr;
    ModbusTcpServer::LineResolver resolver_{};
    ModbusTcpServer::SocketServer server_{};
    ModbusTcpServer::PortConfig configs_[ModbusTcpServer::kPortCount]{};
    bool running_ = false;
    bool eligible_ = false;
    uint32_t lastDiagnosticsMs_ = 0U;
};
