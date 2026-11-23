#!/usr/bin/env python3
"""Regression: flow units are applied atomically at reboot with one-shot HA discovery."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class FlowUnitRestartTests(unittest.TestCase):
    def test_one_shot_ha_is_configured(self):
        self.assertIn("-D FLOW_HA_ONESHOT_DISCOVERY=1", read("platformio.ini"))

    def test_runtime_uses_boot_unit_until_restart(self):
        source = read("src/Modules/IOModule/IOModule.cpp")
        mode = source.split("if (slot.inDef.mode == IO_DIGITAL_INPUT_PULSES_PER_MINUTE) {", 1)[1]
        mode = mode.split("if (!slot.provider.isBound()) return false;", 1)[0]
        self.assertIn("const uint8_t activeUnit = slot.appliedFlowUnit;", mode)
        self.assertIn("pulseFlowUnitValid(activeUnit)", mode)
        self.assertIn("(double)cfg.c0, activeUnit)", mode)
        self.assertNotIn("pulseFlowConvert((double)measurement.pulsesPerMinute,\n                                                  (double)cfg.c0, cfg.flowUnit)", mode)
        self.assertIn("s.appliedFlowUnit = cfg.flowUnit;", source)
        self.assertIn("setValueUnit(flowMeta.displayUnit, pulseFlowUnitText(cfg.flowUnit))", source)

    def test_tft_and_web_get_unit_from_same_registry(self):
        api = read("src/Modules/Network/WebInterfaceModule/WebInterfaceServer.cpp")
        self.assertIn('item["unit"] = defined ? meta.displayUnit : descriptor.unit;', api)
        ui = read("data/webinterface/app.js")
        self.assertIn("dynamicTftRuntimeUiOptions", ui)
        self.assertIn("item.unit", ui)

    def test_four_units_and_help(self):
        for name in ("fr", "en"):
            data = json.loads(read(f"src/Modules/IOModule/text/i18n.{name}.json"))
            for i in range(16):
                key = f"cfgmods.io.input.i{i:02}.flow_unit.help"
                self.assertIn("redémarrage" if name == "fr" else "reboot", data["translations"][key])
        docs = json.loads(read("src/Modules/IOModule/text/cfgmods.fr.json"))
        self.assertEqual([v["value"] for v in docs["meta"]["enum_sets"]["flowio_input_flow_unit"]], [3, 2, 1, 0])

if __name__ == "__main__":
    unittest.main()
