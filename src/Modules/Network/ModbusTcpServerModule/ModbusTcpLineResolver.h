#pragma once
/**
 * @brief Per-port serial-profile resolution without direct UART access.
 *
 * FlowioDevice mode uses an explicit device ID, resolved by the PoolDevice
 * owner. Manual mode uses the configured line. No fallback to a different
 * device or default baud rate is allowed.
 */
#include "ModbusTcpServerPolicy.h"
#include <Arduino.h>
#include "Core/Log.h"
#include "Core/LogModuleIds.h"

// Temporary, error-only reason tags for field diagnostics.
// Disable with -DFLOW_MODBUS_RESOLVER_DIAGNOSTICS=0.
#ifndef FLOW_MODBUS_RESOLVER_DIAGNOSTICS
#define FLOW_MODBUS_RESOLVER_DIAGNOSTICS 1
#endif

namespace ModbusTcpServer {
class LineResolver {
public:
    using DeviceLookup = bool (*)(void* context, uint16_t deviceId,
                                  SerialLineProfile& out, uint8_t& slaveAddress);
    void configure(uint8_t portIndex, const PortConfig& config) {
        if (!validConfig(portIndex, config)) return;
        configs_[portIndex] = config;
    }
    void setDeviceLookup(DeviceLookup lookup, void* context) {
        lookup_ = lookup;
        context_ = context;
    }
    bool resolve(uint8_t portIndex, uint8_t unitId, SerialLineProfile& out,
                 uint8_t& rtuUnitId) const {
        if (!validPortIndex(portIndex)) return false;
        const PortConfig& config = configs_[portIndex];
        const SerialLineProfile empty{};
        if (unitId > 247U) return reject_(portIndex, unitId, "bad_unit", empty, unitId);
        if (!config.enabled) return reject_(portIndex, unitId, "port_disabled", empty, unitId);
        if (!validConfig(portIndex, config))
            return reject_(portIndex, unitId, "port_config", empty, unitId);
        SerialLineProfile line{};
        uint8_t target = unitId;
        if (config.serialSource == SerialSource::Manual) {
            if (!target) return reject_(portIndex, unitId, "zero_manual_unit", line, target);
            line = config.manualLine;
        } else if (config.serialSource == SerialSource::FlowioDevice) {
            if (!lookup_) return reject_(portIndex, unitId, "missing_lookup", line, target);
            if (!lookup_(context_, config.deviceId, line, target))
                return reject_(portIndex, unitId, "device_lookup", line, target);
            if (!target || target > 247U)
                return reject_(portIndex, unitId, "invalid_rtu_id", line, target);
        } else return reject_(portIndex, unitId, "unknown_mode", line, target);
        if (line.busId != 0U) return reject_(portIndex, unitId, "invalid_bus", line, target);
        if (line.baud < 1200U || line.baud > 115200U)
            return reject_(portIndex, unitId, "invalid_baud", line, target);
        if (line.parity > 2U) return reject_(portIndex, unitId, "invalid_parity", line, target);
        if (line.stopBits != 1U && line.stopBits != 2U)
            return reject_(portIndex, unitId, "invalid_stop", line, target);
        if (line.minimumRequestIntervalMs > 60000U)
            return reject_(portIndex, unitId, "invalid_min_gap", line, target);
        if (line.quietMs > 1000U)
            return reject_(portIndex, unitId, "invalid_quiet", line, target);
        if (line.lateResponseGuardMs > 5000U)
            return reject_(portIndex, unitId, "invalid_late", line, target);
        out = line;
        rtuUnitId = target;
        return true;
    }
    static bool resolveStatic(void* context, uint8_t portIndex, uint8_t unitId,
                              SerialLineProfile& out, uint8_t& rtuUnitId) {
        return context &&
            static_cast<const LineResolver*>(context)->resolve(
                portIndex, unitId, out, rtuUnitId);
    }
private:
    bool reject_(uint8_t port, uint8_t unit, const char* why,
                 const SerialLineProfile& line, uint8_t target) const {
#if FLOW_MODBUS_RESOLVER_DIAGNOSTICS
        // Only report a failure when the reason changes, or every 15 seconds.
        // This is network-task-local state; no extra locks or RS485 traffic.
        const uint32_t now = millis();
        if (!lastReason_[port] || lastReason_[port] != why ||
            uint32_t(now - lastReasonAtMs_[port]) >= 15000U) {
            lastReason_[port] = why;
            lastReasonAtMs_[port] = now ? now : 1U;
            const PortConfig& cfg = configs_[port];
            ::Log::warn((LogModuleId)LogModuleIdValue::ModbusTcpServerModule,
                "[MODBUS-RDBG] p=%u dev=%u u=%u why=%s tgt=%u bus=%u bd=%lu par=%u stop=%u gap=%lu q=%lu late=%lu",
                (unsigned)kPorts[port], (unsigned)cfg.deviceId, (unsigned)unit, why,
                (unsigned)target, (unsigned)line.busId, (unsigned long)line.baud,
                (unsigned)line.parity, (unsigned)line.stopBits,
                (unsigned long)line.minimumRequestIntervalMs,
                (unsigned long)line.quietMs, (unsigned long)line.lateResponseGuardMs);
        }
#else
        (void)port; (void)unit; (void)why; (void)line; (void)target;
#endif
        return false;
    }
    PortConfig configs_[kPortCount]{};
    DeviceLookup lookup_ = nullptr;
    void* context_ = nullptr;
#if FLOW_MODBUS_RESOLVER_DIAGNOSTICS
    mutable uint32_t lastReasonAtMs_[kPortCount]{};
    mutable const char* lastReason_[kPortCount]{};
#endif
};
} // namespace ModbusTcpServer
