#pragma once
#include <atomic>
#include <Arduino.h>
#include "Core/Log.h"
#include "Core/LogModuleIds.h"
namespace flowio::modbus_trace {
inline std::atomic<bool> enabled{false};
inline void frame(const char* direction, uint16_t id, const uint8_t* bytes, size_t length) {
    static std::atomic<uint32_t> lastTxMs{0};
    static std::atomic<uint32_t> lastRxMs{0};
    auto& lastMs = direction[0] == 'T' ? lastTxMs : lastRxMs;
    const uint32_t now = millis();
    uint32_t previous = lastMs.load(std::memory_order_relaxed);
    if ((uint32_t)(now - previous) < 500U ||
        !lastMs.compare_exchange_strong(previous, now, std::memory_order_relaxed)) return;
    char line[160];
    int used = snprintf(line, sizeof(line), "Modbus TRACE %s id=%u len=%u:",
                        direction, (unsigned)id, (unsigned)length);
    if (used < 0 || (size_t)used >= sizeof(line)) return;
    const size_t maxBytes = (sizeof(line) - (size_t)used - 1U) / 3U;
    const size_t shown = length < maxBytes ? length : maxBytes;
    for (size_t i=0; i<shown; ++i) {
        const int n = snprintf(line + used, sizeof(line) - (size_t)used, " %02X", bytes[i]);
        if (n != 3) break;
        used += n;
    }
    if (shown < length && (size_t)used + 4U < sizeof(line))
        snprintf(line + used, sizeof(line) - (size_t)used, " ...");
    Log::info((LogModuleId)LogModuleIdValue::IOModule, "%s", line);
}
}
