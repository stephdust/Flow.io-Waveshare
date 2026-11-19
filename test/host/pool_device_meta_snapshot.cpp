#include <cassert>
#include <cstdint>
#include <cstring>
#include "Core/Services/IPoolDevice.h"

// Host harness calls the exact PoolDevice implementation extracted from
// PoolDeviceControl.cpp, with a tiny state-lock fake.
static constexpr uint8_t POOL_DEVICE_MAX = 16;
struct FakeDeviceDefinition {
    uint8_t type = 0;
    bool enabled = false;
    DomainSlotId commandSlot = DOMAIN_SLOT_INVALID;
    float flowLPerHour = 0;
    char label[24]{};
};
struct PoolDeviceSlot {
    bool used = false;
    FakeDeviceDefinition def{};
    PoolDriverConfig driverConfig{};
    uint8_t blockReason = 0;
    PoolInterlockState interlockState = PoolInterlockState::Ready;
    IoId ioId = IO_ID_INVALID;
    bool driverReady = false;
    bool rs485BootCommandConfirmed = false;
    bool desiredOn = false;
    PoolDeviceTarget desired{};
    ActuatorControlState control{};
    const char* id = "";
};
class PoolDeviceModule {
public:
    PoolDeviceSlot slots_[POOL_DEVICE_MAX]{};
    mutable unsigned locks = 0;
    mutable unsigned unlocks = 0;
    bool rejectLock = false;
    bool lockState_() const {
        ++locks;
        return !rejectLock;
    }
    void unlockState_() const { ++unlocks; }
    void fillMetaLocked_(uint8_t, PoolDeviceSvcMeta*) const;
    PoolDeviceSvcStatus svcMetaImpl_(uint8_t, PoolDeviceSvcMeta*) const;
    PoolDeviceSvcStatus svcSnapshotMetaImpl_(PoolDeviceSvcMeta*, uint8_t, uint8_t*) const;
};
// PRODUCTION_METHODS

int main() {
    PoolDeviceModule devices;
    auto& pump = devices.slots_[0];
    pump.used = true;
    pump.def.enabled = true;
    pump.id = "pd0";
    std::strcpy(pump.def.label, "Filtration");
    pump.driverReady = true;
    pump.desiredOn = true;
    pump.desired.setpoint = 1800;
    pump.driverConfig.capabilities.kind = PoolControlKind::Rs485;
    pump.driverConfig.serial.hasFeedback = true;

    auto& heater = devices.slots_[7];
    heater.used = true;
    heater.def.enabled = true;
    heater.id = "pd7";
    std::strcpy(heater.def.label, "Polytropic");
    heater.driverReady = true;
    heater.desiredOn = true;
    heater.desired.setpoint = 28;
    heater.driverConfig.capabilities.kind = PoolControlKind::Rs485;
    heater.driverConfig.serial.hasFeedback = true;
    heater.rs485BootCommandConfirmed = true;

    PoolDeviceSvcMeta snapshot[POOL_DEVICE_MAX]{};
    uint8_t count = 222;
    assert(devices.svcSnapshotMetaImpl_(snapshot, POOL_DEVICE_MAX, &count) == POOLDEV_SVC_OK);
    assert(devices.locks == 1 && devices.unlocks == 1);
    assert(count == 2 && snapshot[0].slot == 0 && snapshot[1].slot == 7);
    assert(std::strcmp(snapshot[0].label, "Filtration") == 0);
    assert(std::strcmp(snapshot[1].runtimeId, "pd7") == 0);
    assert(snapshot[0].serialStartupPending && !snapshot[1].serialStartupPending);
    assert(snapshot[0].guidedTarget.setpoint == 1800);
    assert(snapshot[1].guidedTarget.setpoint == 28);

    // The optimized list must be equivalent to individual metadata calls.
    PoolDeviceSvcMeta meta{};
    assert(devices.svcMetaImpl_(7, &meta) == POOLDEV_SVC_OK);
    assert(meta.slot == snapshot[1].slot);
    assert(meta.guidedOn == snapshot[1].guidedOn);
    assert(meta.serialStartupPending == snapshot[1].serialStartupPending);
    assert(devices.locks == 2 && devices.unlocks == 2);
    assert(devices.svcMetaImpl_(3, &meta) == POOLDEV_SVC_ERR_UNKNOWN_SLOT);

    const auto before = devices.locks;
    count = 8;
    assert(devices.svcSnapshotMetaImpl_(snapshot, 1, &count) == POOLDEV_SVC_ERR_INVALID_ARG);
    assert(count == 0 && devices.locks == before);
    assert(devices.svcSnapshotMetaImpl_(nullptr, POOL_DEVICE_MAX, &count) == POOLDEV_SVC_ERR_INVALID_ARG);
    assert(count == 0 && devices.locks == before);

    devices.rejectLock = true;
    count = 55;
    assert(devices.svcSnapshotMetaImpl_(snapshot, POOL_DEVICE_MAX, &count) == POOLDEV_SVC_ERR_NOT_READY);
    assert(count == 0 && devices.unlocks == 3);
}
