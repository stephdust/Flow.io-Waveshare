#pragma once
#include <stdint.h>

// Diagnostic only: single writer (modbusip task), lock-free readers.
// A stale timestamp means the loop has not reached the next checkpoint;
// it does not, by itself, prove which operation blocked.
namespace FlowModbusIpHealth {
inline volatile uint32_t lastProgressMs = 0;
inline volatile uint32_t loopStartMs = 0;
inline volatile uint8_t stage = 0; // 1=loop entry, 2=port work, 3=loop completed
inline volatile uint8_t port = 0;
}
