#pragma once
/**
 * @brief Per-port serial-profile resolution without direct UART access.
 *
 * FlowioDevice mode uses an explicit device ID, resolved by the PoolDevice
 * owner. Manual mode uses the configured line. No fallback to a different
 * device or default baud rate is allowed.
 */
#include "ModbusTcpServerPolicy.h"

namespace ModbusTcpServer {
class LineResolver {
public:
    using DeviceLookup = bool (*)(void* context, uint16_t deviceId,
                                  SerialLineProfile& out);
    void configure(uint8_t portIndex, const PortConfig& config) {
        if (!validConfig(portIndex, config)) return;
        configs_[portIndex] = config;
    }
    void setDeviceLookup(DeviceLookup lookup, void* context) {
        lookup_ = lookup;
        context_ = context;
    }
    bool resolve(uint8_t portIndex, uint8_t unitId, SerialLineProfile& out) const {
        if (!validPortIndex(portIndex) || unitId < 1U || unitId > 247U) return false;
        const PortConfig& config = configs_[portIndex];
        if (!config.enabled || !validConfig(portIndex, config)) return false;
        SerialLineProfile line{};
        if (config.serialSource == SerialSource::Manual) {
            line = config.manualLine;
        } else if (config.serialSource == SerialSource::FlowioDevice) {
            if (!lookup_ ||
                !lookup_(context_, config.deviceId, line)) return false;
        } else return false;
        if (line.busId != 0U || line.baud < 1200U || line.baud > 115200U ||
            line.parity > 2U || (line.stopBits != 1U && line.stopBits != 2U) ||
            line.minimumRequestIntervalMs > 60000U || line.quietMs > 1000U ||
            line.lateResponseGuardMs > 5000U) return false;
        out = line;
        return true;
    }
    static bool resolveStatic(void* context, uint8_t portIndex, uint8_t unitId,
                              SerialLineProfile& out) {
        return context &&
            static_cast<const LineResolver*>(context)->resolve(portIndex, unitId, out);
    }
private:
    PortConfig configs_[kPortCount]{};
    DeviceLookup lookup_ = nullptr;
    void* context_ = nullptr;
};
} // namespace ModbusTcpServer
