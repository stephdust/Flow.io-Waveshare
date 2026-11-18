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
#include <lwip/sockets.h>
#include <errno.h>
#include "ModbusTcpBridge.h"
#include "ModbusTcpSessions.h"

namespace ModbusTcpServer {
class SocketServer {
public:
    using ResolveLine = bool (*)(void* context, uint8_t portIndex,
                                uint8_t unitId, SerialLineProfile& out,
                                uint8_t& rtuUnitId);

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
            WiFiClient incoming = servers_[port].accept();
            if (incoming) {
                const int8_t slot = sessions_.accept(port);
                if (slot < 0) {
                    ++stats_[port].connectionsRejected;
                    incoming.stop();
                } else {
                    clients_[slot] = incoming;
                    lastReadProgressMs_[slot] = nowMs;
                    lastConnectionCheckMs_[slot] = nowMs;
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
            // Polling connected() for every slot every 10 ms invokes a
            // MSG_PEEK socket read even when clients are completely idle.
            // The actual reads/sends below detect disconnects immediately;
            // check persistent sessions at a lower rate to save lwIP work.
            if (client.fd() < 0) { close_(slot); continue; }
            if (uint32_t(nowMs - lastConnectionCheckMs_[slot]) >= kConnectionCheckMs) {
                lastConnectionCheckMs_[slot] = nowMs;
                if (!client.connected()) { close_(slot); continue; }
            }
            // A peer may hold a scarce per-port slot by sending only part
            // of an MBAP frame. Close incomplete frames with no progress,
            // but preserve normal long-lived idle Modbus TCP connections.
            if (sessions_.hasPartialRequest(slot) &&
                uint32_t(nowMs - lastReadProgressMs_[slot]) >= kPartialFrameTimeoutMs) {
                close_(slot);
                continue;
            }
            BridgeSlot& bridge = bridges_[slot];
            bridge.poll(nowMs);
            if (bridge.state() == BridgeSlot::State::Ready) {
                if (!writing_[slot]) {
                    writing_[slot] = true;
                    lastWriteProgressMs_[slot] = nowMs;
                }
                const size_t remaining = bridge.outputSize() - sent_[slot];
                if (remaining) {
                    // Arduino-ESP32 NetworkClient does not override
                    // Print::availableForWrite(), which always returns zero.
                    // Using it as a readiness gate prevented *every* Modbus
                    // response (including exceptions) from being sent.
                    //
                    // Use a bounded, nonblocking socket send rather than
                    // NetworkClient::write(), whose select/retry loop can
                    // block the Modbus task when a peer stops reading.
                    const int fd = client.fd();
                    if (fd < 0) {
                        ++stats_[port].txErrors;
                        close_(slot);
                        continue;
                    }
                    const size_t count = remaining < kMaxTxBytesPerTick
                        ? remaining : kMaxTxBytesPerTick;
                    const int wrote = ::send(fd, bridge.output() + sent_[slot],
                                             count, MSG_DONTWAIT);
                    if (wrote > 0) {
                        sent_[slot] += size_t(wrote);
                        stats_[port].tcpBytesSent += uint32_t(wrote);
                        lastWriteProgressMs_[slot] = nowMs;
                    } else if (wrote < 0 && errno != EAGAIN &&
                               errno != EWOULDBLOCK && errno != EINTR) {
                        ++stats_[port].txErrors;
                        close_(slot);
                        continue;
                    } else {
                        ++stats_[port].txWouldBlock;
                    }
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
            // One bounded, nonblocking recv per active socket per tick.
            // Previously, available() performed a lwIP FIONREAD ioctl for
            // EVERY byte of the Modbus ADU (up to 260 calls/connection),
            // starving HTTP and ICMP handling under sustained traffic.
            //
            // Read only up to the exact current MBAP/ADU boundary: bytes
            // from the next pipelined TCP request stay in the socket until
            // this request is answered through the shared RS485 scheduler.
            const size_t needed = sessions_.bytesNeeded(slot);
            if (!needed) continue;
            uint8_t input[kMaxRxBytesPerTick]{};
            const size_t readLength = needed < sizeof(input) ? needed : sizeof(input);
            const int received = ::recv(client.fd(), input, readLength, MSG_DONTWAIT);
            if (received == 0) {
                // Peer orderly shutdown.
                close_(slot);
                continue;
            }
            if (received < 0) {
                if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
                    ++stats_[port].rxErrors;
                    close_(slot);
                }
                continue;
            }
            lastReadProgressMs_[slot] = nowMs;
            stats_[port].tcpBytesReceived += uint32_t(received);
            size_t consumed = 0U;
            const auto status = sessions_.feed(slot, input, size_t(received), consumed);
            if (status == TcpSessions::FeedResult::Invalid ||
                consumed != size_t(received)) {
                close_(slot);
                continue;
            }
            if (status != TcpSessions::FeedResult::Complete) continue;
            ModbusTcpAdu::Request request{};
            if (!sessions_.request(slot, request)) {
                ModbusTcpAdu::Request header{};
                if (!sessions_.headerRequest(slot, header)) {
                    close_(slot);
                    continue;
                }
                ++stats_[port].received;
                const bool supported = header.function == 0x03U ||
                    header.function == 0x04U || header.function == 0x06U ||
                    header.function == 0x10U;
                bridge.rejectException(header, configs_[port].errorMode,
                                       supported ? 0x03U : 0x01U, nowMs);
                continue;
            }
            ++stats_[port].received;
            SerialLineProfile line{};
            uint8_t targetUnitId = request.unitId;
            if (!resolver_ || !resolver_(resolverContext_, port, request.unitId,
                                          line, targetUnitId)) {
                ++stats_[port].resolverFailures;
                bridge.reject(request, configs_[port].errorMode,
                              MODBUS_RESULT_NOT_READY, nowMs);
                continue;
            }
            if (!bridge.submit(*service_, request, line, configs_[port].errorMode,
                               configs_[port].transactionTimeoutMs, nowMs, targetUnitId)) {
                ++stats_[port].queueRejected;
                bridge.reject(request, configs_[port].errorMode,
                              MODBUS_RESULT_INVALID_ARGUMENT, nowMs);
            }
            // One outstanding request per connection; the next pipelined
            // ADU remains buffered by lwIP until its predecessor is answered.
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
    static constexpr size_t kMaxTxBytesPerTick = 128U;
    static constexpr size_t kMaxRxBytesPerTick = 64U;
    static constexpr uint32_t kConnectionCheckMs = 250U;
    static constexpr uint32_t kWriteStallTimeoutMs = 5000U;
    static constexpr uint32_t kPartialFrameTimeoutMs = 10000U;
    void close_(uint8_t slot) {
        bridges_[slot].reset();
        clients_[slot].stop();
        sessions_.release(slot);
        sent_[slot] = 0U;
        writing_[slot] = false;
        lastWriteProgressMs_[slot] = 0U;
        lastReadProgressMs_[slot] = 0U;
        lastConnectionCheckMs_[slot] = 0U;
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
    uint32_t lastReadProgressMs_[kMaxClients]{};
    uint32_t lastConnectionCheckMs_[kMaxClients]{};
    bool writing_[kMaxClients]{};
    const ModbusMasterService* service_ = nullptr;
    ResolveLine resolver_ = nullptr;
    void* resolverContext_ = nullptr;
    bool started_ = false;
};
} // namespace ModbusTcpServer
