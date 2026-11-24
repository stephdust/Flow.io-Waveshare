#!/usr/bin/env python3
"""Waveshare digital input defaults and upgrade/NVS precedence regression guards.

A fresh boot uses the profile defaults; upgrades keep persisted field values
while newly introduced keys inherit defaults because Preferences::get*(key,
current_value) returns that current value for an absent NVS key.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


class WaveshareDigitalInputDefaultsTests(unittest.TestCase):
    def test_domain_inputs_match_reference_configuration(self):
        layout = read("src/Profiles/Waveshare/WaveshareIoLayout.h")
        expected = (
            "{PoolIds::SensorWaterMeter, PortGpio5Input, false, IO_PULL_NONE, IO_DIGITAL_INPUT_COUNTER, IO_EDGE_RISING, 1000U}",
            "{PoolIds::SensorPoolLevel, PortGpio6Input, true, IO_PULL_NONE, IO_DIGITAL_INPUT_STATE, IO_EDGE_RISING, 0U}",
            "{PoolIds::SensorChlorineLevel, PortGpio7Input, true, IO_PULL_NONE, IO_DIGITAL_INPUT_STATE, IO_EDGE_RISING, 0U}",
            "{PoolIds::SensorPhLevel, PortGpio8Input, true, IO_PULL_NONE, IO_DIGITAL_INPUT_STATE, IO_EDGE_RISING, 0U}",
            "{PoolIds::SensorPir, PortGpio11Input, true, IO_PULL_UP, IO_DIGITAL_INPUT_STATE, IO_EDGE_RISING, 0U}",
        )
        for line in expected:
            with self.subTest(setting=line):
                self.assertIn(line, layout)

    def test_flow_meter_fallback_defaults(self):
        source = read("src/Profiles/Waveshare/WaveshareIoAssembly.cpp")
        block = source.split("if (i == PoolInputSlots::FlowMeter) {", 1)[1].split("\n        }", 1)[0]
        for setting in (
            "def.activeHigh = true;",
            "def.pullMode = IO_PULL_NONE;",
            "def.mode = IO_DIGITAL_INPUT_PULSES_PER_MINUTE;",
            "def.edgeMode = IO_EDGE_RISING;",
            "def.counterDebounceUs = 100U;",
            "def.flowUnit = IO_FLOW_LITERS_PER_MINUTE;",
            "def.c0 = 23.0f;",
            "def.precision = 0;",
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, block)
        self.assertIn('case PoolInputSlots::Spare: return "GPIO10";', source)
        self.assertIn("def.binding.primaryPort = FlowIoLayout::digitalInputPortUsedByDomainRole(defaultPort)", source)

    def test_profile_values_are_loaded_into_registered_config(self):
        definition = read("src/Modules/IOModule/IOModuleTypes.h")
        module = read("src/Modules/IOModule/IOModule.cpp")
        descriptor = read("src/Modules/IOModule/IOConfigDescriptorStorage.h")
        for field in ("flowUnit", "c0", "precision"):
            self.assertIn(f"digitalInCfg_[logicalIdx].{field} = def.{field};", module)
        for field in ("flowUnit", "c0", "precision", "mode", "activeHigh", "counterDebounceUs"):
            self.assertIn(f"digitalInCfg[slot].{field}", descriptor)
        for field in ("flowUnit", "c0", "precision"):
            self.assertIn(f"    digitalInCfg_[logicalIdx].{field} = def.{field};", module)
        self.assertIn("uint8_t flowUnit = IO_FLOW_LITERS_PER_MINUTE;", definition)

    def test_upgrade_keeps_nvs_values_and_new_fields_get_default(self):
        manager = read("src/Core/ModuleManager.cpp")
        load = read("src/Core/ConfigStore.cpp")
        # Profile initializes registered variables; NVS overrides only stored keys.
        self.assertLess(manager.index("ordered[i]->init(cfg, services);"),
                        manager.index("cfg.loadPersistent();"))
        self.assertLess(manager.index("cfg.loadPersistent();"),
                        manager.index("ordered[i]->onConfigLoaded(cfg, services);"))
        for method in ("getBool", "getUChar", "getInt", "getFloat", "getString"):
            self.assertIn(f"_prefs->{method}(", load)
        self.assertIn("_prefs->getFloat(m.nvsKey, *(float*)m.valuePtr)", load)
        self.assertIn("_prefs->getUChar(m.nvsKey, *(uint8_t*)m.valuePtr)", load)


if __name__ == "__main__":
    unittest.main()
