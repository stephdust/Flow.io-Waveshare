#include <assert.h>
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpLineResolver.h"

namespace {
bool lookup(void* context, uint16_t deviceId, SerialLineProfile& out) {
    ++*static_cast<unsigned*>(context);
    if (deviceId != 7U) return false;
    out.baud = 19200U;
    out.parity = 1U;
    out.stopBits = 2U;
    return true;
}
}
int main() {
    using namespace ModbusTcpServer;
    LineResolver resolver;
    SerialLineProfile line{};
    assert(!resolver.resolve(0, 17, line));
    PortConfig manual{};
    manual.enabled = true;
    manual.tcpPort = 502;
    manual.serialSource = SerialSource::Manual;
    manual.manualLine.baud = 9600;
    resolver.configure(0, manual);
    assert(resolver.resolve(0, 17, line) && line.baud == 9600);
    assert(!resolver.resolve(0, 0, line));
    assert(!resolver.resolve(3, 17, line));
    PortConfig device{};
    device.enabled = true;
    device.tcpPort = 503;
    device.serialSource = SerialSource::FlowioDevice;
    device.deviceId = 7;
    resolver.configure(1, device);
    assert(!resolver.resolve(1, 17, line));
    unsigned calls = 0;
    resolver.setDeviceLookup(&lookup, &calls);
    assert(resolver.resolve(1, 17, line));
    assert(line.baud == 19200 && line.parity == 1 && line.stopBits == 2);
    assert(calls == 1);
    device.deviceId = 8;
    resolver.configure(1, device);
    assert(!resolver.resolve(1, 17, line));
    device.enabled = false;
    resolver.configure(1, device);
    assert(!resolver.resolve(1, 17, line));
}
