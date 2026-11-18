#pragma once
/**
 * @brief Arduino Network TCP socket adapter for Flow.io Modbus TCP gateway.
 *
 * Call begin() after networking and the ModbusMasterService are ready, and
 * tick() from ONE network task. No UART access and no cached register values.
 * The serial profile resolver must return the selected Flow.io device profile
 * or the manually configured profile for the requested port.
 */
#include <Arduino.h>
#include <WiFi.h>
#include "ModbusTcpBridge.h"
#include "ModbusTcpSessions.h"

namespace ModbusTcpServer {
class SocketServer {
public:
    using ResolveLine = bool (*)(void* context, uint8_t portIndex,
                                uint8_t unitId, SerialLineProfile& out);

    SocketServer()
        : servers_{WiFiServer(kPorts[0]), WiFiServer(kPorts[1]), WiFiServer(kPorts[2])},
          bridges_{BridgeSlot(201), BridgeSlot(202), BridgeSlot(203),
                   BridgeSlot(204), BridgeSlot(205), BridgeSlot(206)} {}

    void configure(uint8_t port, const PortConfig& config) {
        if (validConfig(port, config)) configs_[port] = config;
    }

    void begin(const ModbusMasterService& service, ResolveLine resolver,
               void* resolverContext) {
        service_ = &service;
        resolver_ = resolver;
        resolverContext_ = resolverContext;
        for (uint8_t port = 0; port < kPortCount; ++port)
            if (configs_[port].enabled) servers_[port].begin();
        started_ = true;
    }

    void stop() {
        for (uint8_t slot = 0; slot < kMaxClients; ++slot) close_(slot);
        for (auto& server : servers_) server.end();
        started_ = false;
        service_ = nullptr;
    }

    /** Nonblocking best-effort network servicing, with bounded read work.
     * A partial TCP write is resumed on a subsequent tick.
     */
    void tick(uint32_t nowMs) {
        if (!started_ || !service_) return;
        for (uint8_t port = 0; port < kPortCount; ++port) {
            if (!configs_[port].enabled) continue;
            WiFiClient incoming = servers_[port].available();
            if (incoming) {
                const int8_t slot = sessions_.accept(port);
                if (slot < 0) {
                    ++stats_[port].connectionsRejected;
                    incoming.stop();
                } else {
                    clients_[slot] = incoming;
                    stats_[port].activeClients = sessions_.active(port);
                    if (stats_[port].activeClients > stats_[port].maxActiveClients)
                        stats_[port].maxActiveClients = stats_[port].activeClients;
                }
            }
        }
        for (uint8_t slot = 0; slot < kMaxClients; ++slot) {
            const uint8_t port = slot / kClientsPerPort;
            WiFiClient& client = clients_[slot];
            if (!sessions_.occupied(slot)) continue;
            if (!client || !client.connected()) { close_(slot); continue; }
            BridgeSlot& bridge = bridges_[slot];
            bridge.poll(nowMs);
            if (bridge.state() == BridgeSlot::State::Ready) {
                if (!writing_[slot]) {
                    writing_[slot] = true;
                    lastWriteProgressMs_[slot] = nowMs;
                }
                const size_t remaining = bridge.outputSize() - sent_[slot];
                if (remaining && client.availableForWrite() > 0) {
                    const size_t writable = size_t(client.availableForWrite());
                    const size_t count = remaining < writable ? remaining : writable;
                    const size_t wrote = client.write(bridge.output() + sent_[slot], count);
                    sent_[slot] += wrote;
                    if (wrote) lastWriteProgressMs_[slot] = nowMs;
                }
                if (sent_[slot] == bridge.outputSize()) {
                    accountOutcome_(port, bridge, true);
                    ++stats_[port].completed;
                    const uint32_t elapsed = bridge.elapsedMs(nowMs);
                    stats_[port].responseTimeTotalMs += elapsed;
                    if (elapsed > stats_[port].responseTimeMaxMs)
                        stats_[port].responseTimeMaxMs = elapsed;
                    bridge.reset();
                    sessions_.clearRequest(slot);
                    sent_[slot] = 0U;
                    writing_[slot] = false;
                } else if (uint32_t(nowMs - lastWriteProgressMs_[slot]) >= kWriteStallTimeoutMs) {
                    // Release a slot held by a peer that has stopped reading.
                    close_(slot);
                    continue;
                }
            } else if (bridge.state() == BridgeSlot::State::Silent) {
                accountOutcome_(port, bridge, false);
                ++stats_[port].silentFailures;
                bridge.reset();
                sessions_.clearRequest(slot);
                sent_[slot] = 0U;
                writing_[slot] = false;
            }
            if (bridge.state() != BridgeSlot::State::Idle) continue;
            // Read a bounded number of bytes per tick so other Flow.io tasks
            // and connections are not starved by a chatty TCP client.
            for (uint16_t n = 0; n < ModbusTcpAdu::kMaxAdu && client.available() > 0; ++n) {
                const int byte = client.read();
                if (byte < 0) break;
                const uint8_t b = uint8_t(byte);
                size_t consumed = 0U;
                const auto status = sessions_.feed(slot, &b, 1U, consumed);
                if (status == TcpSessions::FeedResult::Invalid) {
                    close_(slot); break;
                }
                if (status != TcpSessions::FeedResult::Complete) continue;
                ModbusTcpAdu::Request request{};
                if (!sessions_.request(slot, request)) {
                    ModbusTcpAdu::Request header{};
                    if (!sessions_.headerRequest(slot, header)) {
                        close_(slot);
                        break;
                    }
                    ++stats_[port].received;
                    const bool supported = header.function == 0x03U ||
                        header.function == 0x04U || header.function == 0x06U ||
                        header.function == 0x10U;
                    bridge.rejectException(header, configs_[port].errorMode,
                                           supported ? 0x03U : 0x01U, nowMs);
                    break;
                }
                ++stats_[port].received;
                SerialLineProfile line{};
                if (!resolver_ || !resolver_(resolverContext_, port, request.unitId, line)) {
                    // No matching configured device: reject rather than send
                    // traffic using an arbitrary UART profile.
                    ++stats_[port].queueRejected;
                    bridge.reject(request, configs_[port].errorMode,
                                  MODBUS_RESULT_NOT_READY, nowMs);
                    break;
                }
                if (!bridge.submit(*service_, request, line, configs_[port].errorMode,
                                   configs_[port].transactionTimeoutMs, nowMs)) {
                    ++stats_[port].queueRejected;
                    bridge.reject(request, configs_[port].errorMode,
                                  MODBUS_RESULT_INVALID_ARGUMENT, nowMs);
                }
                break; // one outstanding request per connection
            }
        }
    }

    const PortStats& stats(uint8_t port) const { return stats_[port < kPortCount ? port : 0U]; }
private:
    void accountOutcome_(uint8_t port, const BridgeSlot& bridge, bool replied) {
        if (bridge.hasSerialTiming()) {
            const uint32_t queueMs = bridge.queueWaitMs();
            const uint32_t responseMs = bridge.rtuResponseMs();
            ++stats_[port].rtuSamples;
            stats_[port].queueWaitTotalMs += queueMs;
            stats_[port].rtuResponseTotalMs += responseMs;
            if (queueMs > stats_[port].queueWaitMaxMs)
                stats_[port].queueWaitMaxMs = queueMs;
            if (responseMs > stats_[port].rtuResponseMaxMs)
                stats_[port].rtuResponseMaxMs = responseMs;
        }
        const ModbusResultCode result = bridge.resultCode();
        if (result == MODBUS_RESULT_TIMEOUT || result == MODBUS_RESULT_EXPIRED)
            ++stats_[port].timeouts;
        if (result == MODBUS_RESULT_CRC_ERROR)
            ++stats_[port].crcErrors;
        if (result == MODBUS_RESULT_QUEUE_FULL)
            ++stats_[port].queueRejected;
        if (replied && result != MODBUS_RESULT_OK)
            ++stats_[port].exceptionsSent;
    }
    static constexpr uint32_t kWriteStallTimeoutMs = 5000U;
    void close_(uint8_t slot) {
        bridges_[slot].reset();
        clients_[slot].stop();
        sessions_.release(slot);
        sent_[slot] = 0U;
        writing_[slot] = false;
        lastWriteProgressMs_[slot] = 0U;
        const uint8_t port = slot / kClientsPerPort;
        stats_[port].activeClients = sessions_.active(port);
    }
    WiFiServer servers_[kPortCount];
    WiFiClient clients_[kMaxClients];
    TcpSessions sessions_{};
    BridgeSlot bridges_[kMaxClients];
    PortConfig configs_[kPortCount]{};
    PortStats stats_[kPortCount]{};
    size_t sent_[kMaxClients]{};
    uint32_t lastWriteProgressMs_[kMaxClients]{};
    bool writing_[kMaxClients]{};
    const ModbusMasterService* service_ = nullptr;
    ResolveLine resolver_ = nullptr;
    void* resolverContext_ = nullptr;
    bool started_ = false;
};
} // namespace ModbusTcpServer
