#include <cassert>
#include "Modules/Network/ModbusIpServerModule/ModbusIpConfig.h"

int main() {
    using flowio::modbus_ip::GatewayConfig;
    GatewayConfig cfg{};
    assert(cfg.valid());
    assert(!cfg.enabled);
    assert(cfg.port == 502 && cfg.timeoutMs == 3000);

    cfg.profileMode = 1; // CommonManual
    assert(cfg.valid());
    cfg.baud = -1;
    assert(!cfg.valid());
    cfg.baud = 9600;
    cfg.parity = 3;
    assert(!cfg.valid());

    // Unused common settings must not disable automatic/per-device profiles.
    cfg.profileMode = 0;
    assert(cfg.valid());
    cfg.profileMode = 2;
    assert(cfg.valid());
    cfg.profileMode = 3;
    assert(!cfg.valid());
    cfg.profileMode = 0;
    cfg.port = 0;
    assert(!cfg.valid());
    cfg.port = 502;
    cfg.timeoutMs = 5001;
    assert(!cfg.valid());
}
