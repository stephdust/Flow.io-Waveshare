#include "WebModbusRoutes.h"

#include "PsramWebServer.h"
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpServerModule.h"
#include "Modules/PoolDeviceModule/PoolDeviceModuleDataModel.h"

#include <Arduino.h>
#include <stdint.h>

namespace {
bool postNumber_(AsyncWebServerRequest* request, const char* key, uint32_t& result)
{
    if (!request || !request->hasParam(key, true)) return false;
    const AsyncWebParameter* parameter = request->getParam(key, true);
    if (!parameter) return false;
    const String& input = parameter->value();
    if (input.isEmpty() || input.length() > 10U) return false;
    uint32_t value = 0U;
    for (size_t i = 0U; i < input.length(); ++i) {
        const char c = input[i];
        if (c < '0' || c > '9') return false;
        const uint32_t digit = uint32_t(c - '0');
        if (value > (UINT32_MAX - digit) / 10U) return false;
        value = value * 10U + digit;
    }
    result = value;
    return true;
}

void printJsonText_(Print& stream, const char* text)
{
    stream.print('"');
    if (text) {
        for (const char* p = text; *p; ++p) {
            switch (*p) {
                case '"': stream.print("\\\""); break;
                case '\\': stream.print("\\\\"); break;
                case '\n': stream.print("\\n"); break;
                case '\r': stream.print("\\r"); break;
                case '\t': stream.print("\\t"); break;
                default:
                    if (uint8_t(*p) < 32U) stream.print('?');
                    else stream.print(*p);
                    break;
            }
        }
    }
    stream.print('"');
}

void sendError_(AsyncWebServerRequest* request, int status, const char* reason)
{
    char json[150]{};
    snprintf(json, sizeof(json), "{\"ok\":false,\"error\":\"%s\"}",
             reason ? reason : "Request failed");
    request->send(status, "application/json", json);
}

} // namespace

namespace WebModbusRoutes {
void registerRoutes(PsramWebServer& server, ModbusTcpServerModule* gateway)
{
    if (!gateway) return;
    server.on("/api/modbus/ports", HTTP_GET, [gateway](AsyncWebServerRequest* request) {
        AsyncResponseStream* response = request->beginResponseStream("application/json");
        if (!response) {
            request->send(503, "application/json", "{\"ok\":false}");
            return;
        }
        response->addHeader("Cache-Control", "no-store");
        ModbusMasterStats master{};
        (void)gateway->schedulerStats(master);
        response->printf(
            "{\"ok\":true,\"running\":%s,\"restart_required\":true,"
            "\"scheduler\":{\"queue\":%u,\"peak\":%u,\"rejected\":%lu},\"ports\":[",
            gateway->running() ? "true" : "false",
            (unsigned)master.queued, (unsigned)master.queuedPeak,
            (unsigned long)master.queueRejected);
        for (uint8_t i = 0; i < ModbusTcpServer::kPortCount; ++i) {
            ModbusTcpServer::PortConfig cfg{};
            if (!gateway->readPort(i, cfg)) continue;
            if (i) response->print(',');
            response->printf(
                "{\"index\":%u,\"port\":%u,\"enabled\":%s,\"source\":%u,"
                "\"device_id\":%u,\"baud\":%lu,\"data_bits\":8,\"parity\":%u,"
                "\"stop_bits\":%u,\"timeout_ms\":%lu,\"error_mode\":%u",
                (unsigned)i, (unsigned)cfg.tcpPort,
                cfg.enabled ? "true" : "false",
                (unsigned)cfg.serialSource,
                (unsigned)cfg.deviceId,
                (unsigned long)cfg.manualLine.baud,
                (unsigned)cfg.manualLine.parity,
                (unsigned)cfg.manualLine.stopBits,
                (unsigned long)cfg.transactionTimeoutMs,
                (unsigned)cfg.errorMode);
            const ModbusTcpServer::PortStats& stat = gateway->portStats(i);
            const uint32_t averageMs = stat.completed ?
                stat.responseTimeTotalMs / stat.completed : 0U;
            const uint32_t queueAverageMs = stat.rtuSamples ?
                stat.queueWaitTotalMs / stat.rtuSamples : 0U;
            const uint32_t rtuAverageMs = stat.rtuSamples ?
                stat.rtuResponseTotalMs / stat.rtuSamples : 0U;
            response->printf(
                ",\"stats\":{\"clients\":%u,\"peak_clients\":%u,"
                "\"requests\":%lu,\"responses\":%lu,\"exceptions\":%lu,"
                "\"silent\":%lu,\"timeouts\":%lu,\"crc_errors\":%lu,"
                "\"queue_rejected\":%lu,\"connections_rejected\":%lu,"
                "\"tcp_avg_ms\":%lu,\"tcp_max_ms\":%lu,"
                "\"queue_avg_ms\":%lu,\"queue_max_ms\":%lu,"
                "\"rtu_avg_ms\":%lu,\"rtu_max_ms\":%lu}}",
                (unsigned)stat.activeClients, (unsigned)stat.maxActiveClients,
                (unsigned long)stat.received, (unsigned long)stat.completed,
                (unsigned long)stat.exceptionsSent, (unsigned long)stat.silentFailures,
                (unsigned long)stat.timeouts, (unsigned long)stat.crcErrors,
                (unsigned long)stat.queueRejected,
                (unsigned long)stat.connectionsRejected,
                (unsigned long)averageMs,
                (unsigned long)stat.responseTimeMaxMs,
                (unsigned long)queueAverageMs,
                (unsigned long)stat.queueWaitMaxMs,
                (unsigned long)rtuAverageMs,
                (unsigned long)stat.rtuResponseMaxMs);
        }
        response->print("],\"devices\":[");
        bool first = true;
        for (uint16_t id = 0; id < POOL_DEVICE_MAX; ++id) {
            SerialLineProfile line{};
            char label[32]{};
            uint8_t slaveAddress = 0U;
            if (!gateway->serialDeviceInfo(id, line, label, sizeof(label), &slaveAddress)) continue;
            if (!first) response->print(',');
            first = false;
            response->printf("{\"id\":%u,\"label\":", (unsigned)id);
            printJsonText_(*response, label);
            response->printf(",\"baud\":%lu,\"parity\":%u,\"stop_bits\":%u,\"rtu_unit_id\":%u}",
                             (unsigned long)line.baud, (unsigned)line.parity,
                             (unsigned)line.stopBits, (unsigned)slaveAddress);
        }
        response->print("]}");
        request->send(response);
    });

    // All write fields are required; no silent coercion of malformed input.
    server.on("/api/modbus/port", HTTP_POST, [gateway](AsyncWebServerRequest* request) {
        static const char* const keys[] = {
            "index", "enabled", "source", "device_id", "baud",
            "parity", "stop_bits", "timeout_ms", "error_mode"
        };
        uint32_t v[sizeof(keys) / sizeof(keys[0])]{};
        for (size_t i = 0; i < sizeof(v) / sizeof(v[0]); ++i) {
            if (!postNumber_(request, keys[i], v[i])) {
                sendError_(request, 400, "Invalid parameter");
                return;
            }
        }
        if (v[0] >= ModbusTcpServer::kPortCount || v[1] > 1U ||
            v[2] > 1U || v[3] >= POOL_DEVICE_MAX || v[4] < 1200U ||
            v[4] > 115200U || v[5] > 2U || (v[6] != 1U && v[6] != 2U) ||
            v[7] < 100U || v[7] > 120000U || v[8] > 1U) {
            sendError_(request, 400, "Unsupported port configuration");
            return;
        }
        ModbusTcpServer::PortConfig cfg{};
        cfg.tcpPort = ModbusTcpServer::kPorts[v[0]];
        cfg.enabled = v[1] != 0U;
        cfg.serialSource = static_cast<ModbusTcpServer::SerialSource>(v[2]);
        cfg.deviceId = uint16_t(v[3]);
        cfg.manualLine.baud = v[4];
        cfg.manualLine.parity = uint8_t(v[5]);
        cfg.manualLine.stopBits = uint8_t(v[6]);
        cfg.transactionTimeoutMs = v[7];
        cfg.errorMode = static_cast<ModbusTcpServer::ErrorMode>(v[8]);
        if (!ModbusTcpServer::validConfig(uint8_t(v[0]), cfg)) {
            sendError_(request, 400, "Invalid serial configuration");
            return;
        }
        if (cfg.enabled && cfg.serialSource == ModbusTcpServer::SerialSource::FlowioDevice) {
            SerialLineProfile line{};
            if (!gateway->serialDeviceInfo(cfg.deviceId, line, nullptr, 0U)) {
                sendError_(request, 400, "Selected RS485 equipment unavailable");
                return;
            }
        }
        if (!gateway->savePort(uint8_t(v[0]), cfg)) {
            sendError_(request, 503, "NVS save failed");
            return;
        }
        request->send(200, "application/json",
                      "{\"ok\":true,\"restart_required\":true}");
    });
}
} // namespace WebModbusRoutes
