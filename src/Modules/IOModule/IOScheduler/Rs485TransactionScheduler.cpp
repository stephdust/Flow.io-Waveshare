/**
 * @file Rs485TransactionScheduler.cpp
 * @brief Asynchronous Modbus RTU master implementation.
 */

#include "Rs485TransactionScheduler.h"
#include "ModbusTraceControl.h"

#include <esp_heap_caps.h>
#include <new>
#include <Arduino.h>

#define LOG_MODULE_ID ((LogModuleId)LogModuleIdValue::IOModule)
#include "Core/ModuleLog.h"

#include "Modules/IOModule/IOProtocols/Modbus/ModbusRtuCodec.h"

namespace {
uint32_t busAvailableAt(const SerialLineProfile& line, uint32_t sentAt, uint32_t now, bool guard)
{
    const uint32_t quietUntil = now + line.quietMs + (guard ? line.lateResponseGuardMs : 0);
    const uint32_t nextStart = sentAt + line.minimumRequestIntervalMs;
    return int32_t(nextStart - quietUntil) > 0 ? nextStart : quietUntil;
}
const char* resultName(ModbusResultCode result)
{
    switch (result) {
        case MODBUS_RESULT_OK: return "ok";
        case MODBUS_RESULT_INVALID_ARGUMENT: return "invalid_argument";
        case MODBUS_RESULT_NOT_READY: return "not_ready";
        case MODBUS_RESULT_QUEUE_FULL: return "queue_full";
        case MODBUS_RESULT_UNKNOWN_TRANSACTION: return "unknown_transaction";
        case MODBUS_RESULT_TIMEOUT: return "timeout";
        case MODBUS_RESULT_CRC_ERROR: return "crc_error";
        case MODBUS_RESULT_PROTOCOL_ERROR: return "protocol_error";
        case MODBUS_RESULT_EXCEPTION: return "exception";
        case MODBUS_RESULT_EXPIRED: return "expired";
        case MODBUS_RESULT_IO_ERROR: return "io_error";
    }
    return "unknown";
}
} // namespace

Rs485TransactionScheduler::Rs485TransactionScheduler(IRs485Transport& bus) : bus_(bus)
{
    service_ = {
        &Rs485TransactionScheduler::submitStatic_,
        &Rs485TransactionScheduler::pollStatic_,
        &Rs485TransactionScheduler::cancelOwnerStatic_,
        &Rs485TransactionScheduler::statsStatic_,
        this
    };
}

bool Rs485TransactionScheduler::begin()
{
    if (!mutex_) mutex_ = xSemaphoreCreateMutexStatic(&mutexStorage_);
    if (!storageAllocationAttempted_ && mutex_ && bus_.ready()) {
        storageAllocationAttempted_ = true;
        void* memory = heap_caps_malloc(sizeof(Storage), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
        if (memory) {
            storage_ = new (memory) Storage{};
            LOGI("Modbus storage ready bytes=%u memory=psram", (unsigned)sizeof(Storage));
        } else {
            LOGE("Modbus unavailable: PSRAM allocation failed bytes=%u", (unsigned)sizeof(Storage));
        }
    }
    ready_ = mutex_ != nullptr && storage_ != nullptr && bus_.ready();
    statsData_.ready = ready_;
    LOGD("Modbus init ready=%u bus=%u mutex=%u storage=%u queue_capacity=%u",
         ready_, bus_.ready(), mutex_ != nullptr, storage_ != nullptr, kQueueCapacity);
    return ready_;
}

bool Rs485TransactionScheduler::lock_(TickType_t timeout) const
{
    return mutex_ && xSemaphoreTake(mutex_, timeout) == pdTRUE;
}

void Rs485TransactionScheduler::unlock_() const
{
    if (mutex_) xSemaphoreGive(mutex_);
}

bool Rs485TransactionScheduler::validRequest_(const ModbusRequest& request)
{
    return request.ownerId != 0 && request.priority <= MODBUS_PRIORITY_SAFETY &&
        request.transactionBudgetMs > 0 && request.transactionBudgetMs <= 120000 &&
        request.responseTimeoutMs >= 10 && request.responseTimeoutMs <= 5000 &&
        request.retries <= 3 && request.line.busId == 0 &&
        request.line.baud >= 1200 && request.line.baud <= 115200 &&
        request.line.parity <= 2 && (request.line.stopBits == 1 || request.line.stopBits == 2) &&
        request.line.minimumRequestIntervalMs <= 60000 && request.line.quietMs <= 1000 && request.line.lateResponseGuardMs <= 5000 &&
        ModbusRtuCodec::validRequest(request);
}

ModbusResultCode Rs485TransactionScheduler::submitStatic_(void* ctx,
                                                const ModbusRequest* request,
                                                uint16_t* outTransactionId)
{
    if (!ctx || !request || !outTransactionId) return MODBUS_RESULT_INVALID_ARGUMENT;
    return static_cast<Rs485TransactionScheduler*>(ctx)->submit_(*request, *outTransactionId);
}

ModbusResultCode Rs485TransactionScheduler::pollStatic_(void* ctx,
                                              uint16_t transactionId,
                                              ModbusResponse* outResponse)
{
    if (!ctx || !outResponse || transactionId == MODBUS_TRANSACTION_INVALID) {
        return MODBUS_RESULT_INVALID_ARGUMENT;
    }
    return static_cast<Rs485TransactionScheduler*>(ctx)->poll_(transactionId, *outResponse);
}

void Rs485TransactionScheduler::cancelOwnerStatic_(void* ctx, uint8_t ownerId)
{
    if (ctx) static_cast<Rs485TransactionScheduler*>(ctx)->cancelOwner_(ownerId);
}

bool Rs485TransactionScheduler::statsStatic_(void* ctx, ModbusMasterStats* outStats)
{
    return ctx && outStats && static_cast<Rs485TransactionScheduler*>(ctx)->stats_(*outStats);
}

ModbusResultCode Rs485TransactionScheduler::submit_(const ModbusRequest& request,
                                          uint16_t& outTransactionId)
{
    outTransactionId = MODBUS_TRANSACTION_INVALID;
    if (!validRequest_(request)) {
        LOGD("Modbus submit rejected owner=%u slave=%u fc=0x%02X reason=invalid_argument",
             request.ownerId, request.slaveAddress, request.function);
        return MODBUS_RESULT_INVALID_ARGUMENT;
    }
    if (!ready_) return MODBUS_RESULT_NOT_READY;
    if (!lock_()) return MODBUS_RESULT_NOT_READY;

    if (!accepting_) { unlock_(); return MODBUS_RESULT_NOT_READY; }
    Slot* freeSlot = nullptr;
    for (Slot& slot : storage_->slots) {
        if (slot.state == SlotState::Free) {
            freeSlot = &slot;
            break;
        }
    }
    // Leave capacity for monitoring reads and an urgent stop even during
    // a burst of writes. Serial drivers keep at most one request per owner.
    unsigned freeCount = 0;
    for (const auto& slot : storage_->slots) if (slot.state == SlotState::Free) ++freeCount;
    const unsigned reserved = request.priority == MODBUS_PRIORITY_SAFETY ? 0 :
        request.operation == RegisterOperation::Read ? 1 : 2;
    if (!freeSlot || freeCount <= reserved) {
        LOGD("Modbus submit rejected owner=%u slave=%u reason=queue_full",
             request.ownerId, request.slaveAddress);
        unlock_();
        return MODBUS_RESULT_QUEUE_FULL;
    }

    const uint16_t id = allocateTransactionId_();
    if (id == MODBUS_TRANSACTION_INVALID) {
        unlock_();
        return MODBUS_RESULT_QUEUE_FULL;
    }
    *freeSlot = Slot{};
    freeSlot->state = SlotState::Queued;
    freeSlot->transactionId = id;
    freeSlot->order = nextOrder_++;
    freeSlot->queuedAtMs = millis();
    freeSlot->enqueuedAttemptAtMs = freeSlot->queuedAtMs;
    freeSlot->request = request;
    freeSlot->response.transactionId = id;
    outTransactionId = id;
    ++statsData_.submitted;
    LOGD("Modbus queued id=%u owner=%u slave=%u fc=0x%02X reg=0x%04X count=%u priority=%u",
         id, request.ownerId, request.slaveAddress, request.function,
         request.registerAddress, request.registerCount, request.priority);
    unlock_();
    return MODBUS_RESULT_OK;
}

uint16_t Rs485TransactionScheduler::allocateTransactionId_()
{
    // The queue is small, but completed transactions may remain until consumed.
    // Avoid reusing their identifier when the 16-bit sequence wraps.
    for (uint32_t checked = 0U; checked < UINT16_MAX; ++checked) {
        uint16_t candidate = nextTransactionId_++;
        if (candidate == MODBUS_TRANSACTION_INVALID) candidate = nextTransactionId_++;
        bool inUse = false;
        for (const Slot& slot : storage_->slots) {
            if (slot.state != SlotState::Free && slot.transactionId == candidate) {
                inUse = true;
                break;
            }
        }
        if (!inUse) return candidate;
    }
    return MODBUS_TRANSACTION_INVALID;
}

ModbusResultCode Rs485TransactionScheduler::poll_(uint16_t transactionId,
                                        ModbusResponse& outResponse)
{
    if (!storage_) return MODBUS_RESULT_NOT_READY;
    if (!lock_()) return MODBUS_RESULT_NOT_READY;
    for (Slot& slot : storage_->slots) {
        if (slot.state == SlotState::Free || slot.transactionId != transactionId) continue;
        if (slot.state != SlotState::Finished) {
            outResponse = slot.response;
            outResponse.transactionId = transactionId;
            outResponse.state = MODBUS_TRANSACTION_QUEUED;
            outResponse.result = MODBUS_RESULT_NOT_READY;
            unlock_();
            return MODBUS_RESULT_NOT_READY;
        }
        outResponse = slot.response;
        slot = Slot{};
        unlock_();
        return MODBUS_RESULT_OK;
    }
    unlock_();
    return MODBUS_RESULT_UNKNOWN_TRANSACTION;
}

void Rs485TransactionScheduler::cancelOwner_(uint8_t ownerId)
{
    // Cancellation may not silently fail and leave an obsolete ON in the queue.
    // The mutex protects scheduler bookkeeping; it is never held awaiting a reply.
    if (ownerId == 0U || !storage_ || !lock_(portMAX_DELAY)) return;
    for (uint8_t i = 0U; i < kQueueCapacity; ++i) {
        Slot& slot = storage_->slots[i];
        if (slot.state == SlotState::Free || slot.request.ownerId != ownerId) continue;
        LOGD("Modbus cancel id=%u owner=%u active=%u",
             slot.transactionId, ownerId, (int8_t)i == activeIndex_);
        if ((int8_t)i == activeIndex_) {
            // Cancellation never truncates a frame or reconfigures UART from a caller task.
            slot.abandoned = true;
            continue;
        }
        slot = Slot{};
    }
    unlock_();
}

bool Rs485TransactionScheduler::stats_(ModbusMasterStats& outStats) const
{
    if (!lock_()) return false;
    outStats = statsData_;
    outStats.queued = 0U;
    if (!storage_) {
        unlock_();
        return true;
    }
    for (const Slot& slot : storage_->slots) {
        if (slot.state == SlotState::Queued || slot.state == SlotState::Active) {
            ++outStats.queued;
        }
    }
    unlock_();
    return true;
}

int8_t Rs485TransactionScheduler::selectNextSlot_(uint32_t nowMs) const
{
    int8_t selected = -1;
    for (uint8_t i = 0U; i < kQueueCapacity; ++i) {
        const Slot& candidate = storage_->slots[i];
        if (candidate.state != SlotState::Queued) continue;
        if (selected < 0) {
            selected = (int8_t)i;
            continue;
        }
        const Slot& current = storage_->slots[(uint8_t)selected];
        const auto rank = [nowMs](const Slot& s) -> uint8_t {
            if (s.request.priority == MODBUS_PRIORITY_SAFETY) return 4;
            const uint32_t waitMs = (uint32_t)(nowMs - s.queuedAtMs);
            // Give periodic internal polls a bounded chance under continuous IP load.
            // Commands retain precedence until a poll has waited 750 ms; safety
            // always wins. At 2 s, age every request to avoid starving IP traffic.
            // Preserve FIFO within each effective priority; no UART/profile changes.
            if (waitMs >= 2000U) return 3;
            if (s.request.priority == MODBUS_PRIORITY_BACKGROUND &&
                s.request.ownerId < 201U && waitMs >= 750U) return 2;
            return s.request.priority;
        };
        if (rank(candidate) > rank(current) ||
            (rank(candidate) == rank(current) && int32_t(candidate.order - current.order) < 0)) {
            selected = (int8_t)i;
        }
    }
    return selected;
}

bool Rs485TransactionScheduler::sendActive_(Slot& slot, uint32_t nowMs, uint32_t nowUs)
{
    if (!bus_.configureLine(slot.request.line)) {
        LOGD("Modbus TX id=%u failed stage=configure_line", slot.transactionId);
        finish_(slot, MODBUS_RESULT_IO_ERROR);
        return false;
    }
    size_t txLength = 0U;
    if (!ModbusRtuCodec::encodeRequest(slot.request,
                                       storage_->txFrame, sizeof(storage_->txFrame), txLength)) {
        finish_(slot, MODBUS_RESULT_INVALID_ARGUMENT);
        return false;
    }
    if (!bus_.startTransmit(storage_->txFrame, txLength, nowUs)) {
        ++statsData_.ioErrors;
        finish_(slot, MODBUS_RESULT_IO_ERROR);
        return false;
    }
    LOGD("Modbus dispatch id=%u slave=%u queue_ms=%lu", slot.transactionId,
         slot.request.slaveAddress, (unsigned long)(nowMs - slot.enqueuedAttemptAtMs));
    LOGD_HEX("Modbus TX", slot.transactionId, storage_->txFrame, txLength);
    if (flowio::modbus_trace::enabled.load(std::memory_order_relaxed))
        flowio::modbus_trace::frame("TX", slot.transactionId, storage_->txFrame, txLength);
    slot.state = SlotState::Active;
    slot.sentAtMs = nowMs;
    LOGD("Modbus TX id=%u bytes=%u attempt=%u/%u timeout_ms=%lu protocol=%u",
         slot.transactionId, (unsigned)txLength, slot.attempts + 1U, slot.request.retries + 1U,
         (unsigned long)slot.request.responseTimeoutMs, (unsigned)slot.request.protocol);
    return true;
}

void Rs485TransactionScheduler::finish_(Slot& slot,
                              ModbusResultCode result,
                              const ModbusResponse* response)
{
    if (response) slot.response = *response;
    slot.response.transactionId = slot.transactionId;
    slot.response.result = result;
    slot.response.state = (result == MODBUS_RESULT_OK)
                              ? MODBUS_TRANSACTION_COMPLETE
                              : MODBUS_TRANSACTION_FAILED;
    availableAtMs_ = busAvailableAt(slot.request.line, slot.sentAtMs, millis(),
                                    result != MODBUS_RESULT_OK || slot.abandoned);
    LOGD("Modbus done id=%u slave=%u result=%s exception=0x%02X total_ms=%lu abandoned=%u",
         slot.transactionId, slot.request.slaveAddress, resultName(result),
         slot.response.exceptionCode, (unsigned long)(millis() - slot.queuedAtMs), slot.abandoned);
    // Rate-limited timing for Modbus TCP owners (ports 502-504, two clients each).
    // Measures scheduler queue + RS485 transaction without changing bus behavior.
    if (slot.request.ownerId >= 201U && slot.request.ownerId <= 212U) {
        static uint32_t lastIpTimingLogMs = 0U;
        const uint32_t nowMs = millis();
        if ((uint32_t)(nowMs - lastIpTimingLogMs) >= 2000U) {
            lastIpTimingLogMs = nowMs;
            LOGI("Modbus IP TIMING owner=%u id=%u slave=%u fc=0x%02X reg=0x%04X count=%u queue_ms=%lu rs485_ms=%lu total_ms=%lu attempts=%u result=%s",
                 slot.request.ownerId, slot.transactionId, slot.request.slaveAddress,
                 slot.request.function, slot.request.registerAddress, slot.request.registerCount,
                 (unsigned long)(slot.sentAtMs - slot.queuedAtMs),
                 (unsigned long)(nowMs - slot.sentAtMs),
                 (unsigned long)(nowMs - slot.queuedAtMs),
                 (unsigned)(slot.attempts + 1U), resultName(result));
        }
    }
    // Lightweight aggregate metrics for internal polling and external Modbus IP traffic.
    // No frame dumps, allocations or extra UART operations. One line per class / 15 s.
    {
        struct TimingBucket {
            uint32_t windowStartMs = 0U;
            uint32_t samples = 0U;
            uint32_t errors = 0U;
            uint64_t queueTotalMs = 0U;
            uint64_t busTotalMs = 0U;
            uint32_t queueMaxMs = 0U;
            uint32_t busMaxMs = 0U;
        };
        static TimingBucket buckets[4]{};
        const bool ipOwner = slot.request.ownerId >= 201U && slot.request.ownerId <= 212U;
        const uint8_t category = ipOwner ? 2U :
            (slot.request.slaveAddress == 0x11U ? 0U :
             (slot.request.slaveAddress == 0xAAU ? 1U : 3U));
        const char* const names[4] = {"internal_polytropic", "internal_aquagem",
                                      "modbus_ip", "internal_other"};
        TimingBucket& bucket = buckets[category];
        const uint32_t finishedMs = millis();
        const uint32_t queueMs = slot.sentAtMs - slot.queuedAtMs;
        const uint32_t busMs = finishedMs - slot.sentAtMs;
        if (bucket.windowStartMs == 0U) bucket.windowStartMs = finishedMs;
        ++bucket.samples;
        if (result != MODBUS_RESULT_OK) ++bucket.errors;
        bucket.queueTotalMs += queueMs;
        bucket.busTotalMs += busMs;
        if (queueMs > bucket.queueMaxMs) bucket.queueMaxMs = queueMs;
        if (busMs > bucket.busMaxMs) bucket.busMaxMs = busMs;
        if ((uint32_t)(finishedMs - bucket.windowStartMs) >= 15000U) {
            LOGI("Modbus SCHED class=%s samples=%lu errors=%lu queue_avg_ms=%lu queue_max_ms=%lu rs485_avg_ms=%lu rs485_max_ms=%lu last_owner=%u last_slave=0x%02X last_baud=%lu",
                 names[category], (unsigned long)bucket.samples,
                 (unsigned long)bucket.errors,
                 (unsigned long)(bucket.queueTotalMs / bucket.samples),
                 (unsigned long)bucket.queueMaxMs,
                 (unsigned long)(bucket.busTotalMs / bucket.samples),
                 (unsigned long)bucket.busMaxMs,
                 (unsigned)slot.request.ownerId, (unsigned)slot.request.slaveAddress,
                 (unsigned long)slot.request.line.baud);
            bucket = TimingBucket{};
        }
    }
    if (slot.abandoned) slot = Slot{};
    else slot.state = SlotState::Finished;
    activeIndex_ = -1;
    if (result == MODBUS_RESULT_OK) ++statsData_.completed;
}

void Rs485TransactionScheduler::retryOrFinish_(Slot& slot,
                                     ModbusResultCode result,
                                     uint32_t nowMs)
{
    if (result == MODBUS_RESULT_CRC_ERROR) ++statsData_.crcErrors;
    if (result == MODBUS_RESULT_PROTOCOL_ERROR) ++statsData_.protocolErrors;
    if (result == MODBUS_RESULT_TIMEOUT) ++statsData_.timeouts;
    LOGD("Modbus failed id=%u result=%s elapsed_ms=%lu",
         slot.transactionId, resultName(result), (unsigned long)(nowMs - slot.sentAtMs));
    bus_.abort();
    if (accepting_ && !slot.abandoned && result != MODBUS_RESULT_EXCEPTION && slot.attempts < slot.request.retries) {
        ++slot.attempts;
        ++statsData_.retries;
        LOGD("Modbus retry id=%u next_attempt=%u delay_ms=%lu",
             slot.transactionId, slot.attempts + 1U,
             (unsigned long)(slot.request.line.lateResponseGuardMs + slot.request.line.quietMs));
        slot.state = SlotState::Queued;
        slot.enqueuedAttemptAtMs = nowMs;
        slot.order = nextOrder_++;
        activeIndex_ = -1;
        availableAtMs_ = busAvailableAt(slot.request.line, slot.sentAtMs, nowMs, true);
        return;
    }
    finish_(slot, result);
}

void Rs485TransactionScheduler::tick(uint32_t nowMs, uint32_t nowUs, bool enabled)
{
    if (!ready_ || !lock_(0U)) return;
    if (accepting_ != enabled) LOGD("Modbus accepting=%u", enabled);
    accepting_ = enabled;
    if (!enabled) {
        for (auto& slot : storage_->slots) if (slot.state == SlotState::Queued) {
            slot.response.state = MODBUS_TRANSACTION_FAILED;
            slot.response.result = MODBUS_RESULT_NOT_READY;
            slot.state = SlotState::Finished;
        }
    }
    bus_.tick(nowUs);
    for (auto& slot : storage_->slots) {
        if (slot.state == SlotState::Queued &&
            nowMs - slot.queuedAtMs >= slot.request.transactionBudgetMs) {
            slot.response.result = MODBUS_RESULT_EXPIRED;
            slot.response.state = MODBUS_TRANSACTION_FAILED;
            slot.state = SlotState::Finished;
            LOGD("Modbus queue expired id=%u slave=%u wait_ms=%lu", slot.transactionId,
                 slot.request.slaveAddress, (unsigned long)(nowMs - slot.queuedAtMs));
        }
    }

    // Track elapsed time spent blocked while a queued transaction is waiting.
    // Attribute each interval to the state observed at the preceding tick.
    // Unlike tick counts, these durations remain meaningful if the tick rate varies.
    {
        enum class WaitState : uint8_t { None, Active, Guard, Quiet, Ready };
        static uint32_t windowStartMs = 0U;
        static uint32_t previousTickMs = 0U;
        static WaitState previousState = WaitState::None;
        static uint64_t elapsedMs[4]{};
        static uint32_t ticks[4]{};
        if (windowStartMs == 0U) windowStartMs = nowMs;
        if (previousTickMs != 0U && previousState != WaitState::None) {
            const uint32_t elapsed = (uint32_t)(nowMs - previousTickMs);
            elapsedMs[(uint8_t)previousState - 1U] += elapsed;
        }
        bool pending = false;
        for (const Slot& candidate : storage_->slots) {
            if (candidate.state == SlotState::Queued) {
                pending = true;
                break;
            }
        }
        WaitState state = WaitState::None;
        if (pending) {
            if (activeIndex_ >= 0) state = WaitState::Active;
            else if (availableAtMs_ && int32_t(nowMs - availableAtMs_) < 0) state = WaitState::Guard;
            else if (!bus_.quiet(nowUs)) state = WaitState::Quiet;
            else state = WaitState::Ready;
            ++ticks[(uint8_t)state - 1U];
        }
        previousTickMs = nowMs;
        previousState = state;
        if ((uint32_t)(nowMs - windowStartMs) >= 15000U) {
            LOGI("Modbus BUS WAIT active_ms=%llu guard_ms=%llu quiet_ms=%llu ready_ms=%llu active_ticks=%lu guard_ticks=%lu quiet_ticks=%lu ready_ticks=%lu",
                 (unsigned long long)elapsedMs[0], (unsigned long long)elapsedMs[1],
                 (unsigned long long)elapsedMs[2], (unsigned long long)elapsedMs[3],
                 (unsigned long)ticks[0], (unsigned long)ticks[1],
                 (unsigned long)ticks[2], (unsigned long)ticks[3]);
            for (uint8_t i = 0U; i < 4U; ++i) {
                elapsedMs[i] = 0U;
                ticks[i] = 0U;
            }
            windowStartMs = nowMs;
        }
    }

    if (activeIndex_ < 0) {
        if ((availableAtMs_ && int32_t(nowMs - availableAtMs_) < 0) || !bus_.quiet(nowUs)) {
            unlock_();
            return;
        }
        availableAtMs_ = 0;
        activeIndex_ = selectNextSlot_(nowMs);
        if (activeIndex_ >= 0) {
            Slot& slot = storage_->slots[(uint8_t)activeIndex_];
            (void)sendActive_(slot, nowMs, nowUs);
        }
        unlock_();
        return;
    }

    Slot& slot = storage_->slots[(uint8_t)activeIndex_];
    if (bus_.frameAvailable()) {
        size_t rxLength = 0U;
        if (!bus_.takeFrame(storage_->rxFrame, sizeof(storage_->rxFrame), rxLength)) {
            retryOrFinish_(slot, MODBUS_RESULT_IO_ERROR, nowMs);
        } else {
            ModbusResponse response{};
            const ModbusResultCode result = ModbusRtuCodec::decodeResponse(
                slot.request, storage_->rxFrame, rxLength, response);
            if (result != MODBUS_RESULT_OK && result != MODBUS_RESULT_EXCEPTION) {
                LOGD_HEX("Modbus BAD RX", slot.transactionId, storage_->rxFrame, rxLength);
                static uint32_t lastBadFrameLogMs = 0U;
                if ((uint32_t)(nowMs - lastBadFrameLogMs) >= 2000U) {
                    lastBadFrameLogMs = nowMs;
                    LOGI("Modbus BAD RX id=%u owner=%u slave=%u fc=0x%02X bytes=%u result=%s elapsed_ms=%lu",
                         slot.transactionId, slot.request.ownerId, slot.request.slaveAddress,
                         slot.request.function, (unsigned)rxLength, resultName(result),
                         (unsigned long)(nowMs - slot.sentAtMs));
                }
            }
            if (flowio::modbus_trace::enabled.load(std::memory_order_relaxed))
                flowio::modbus_trace::frame("RX", slot.transactionId, storage_->rxFrame, rxLength);
            LOGD("Modbus RX id=%u bytes=%u elapsed_ms=%lu result=%s registers=%u",
                 slot.transactionId, (unsigned)rxLength,
                 (unsigned long)(nowMs - slot.sentAtMs), resultName(result), response.registerCount);
            if (result == MODBUS_RESULT_OK || result == MODBUS_RESULT_EXCEPTION) {
                finish_(slot, result, &response);
            } else {
                retryOrFinish_(slot, result, nowMs);
            }
        }
    } else if (nowMs - slot.queuedAtMs >= slot.request.transactionBudgetMs) {
        bus_.abort();
        finish_(slot, MODBUS_RESULT_EXPIRED);
    } else if ((uint32_t)(nowMs - slot.sentAtMs) >= slot.request.responseTimeoutMs &&
               !bus_.receivingFrame()) {
        // A delayed tick may just have drained a complete response from UART.
        // Let the transport observe the frame gap before decoding those bytes;
        // otherwise task latency turns an already received response into a timeout.
        retryOrFinish_(slot, MODBUS_RESULT_TIMEOUT, nowMs);
    }
    unlock_();
}
