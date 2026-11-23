#!/usr/bin/env python3
"""Regression: changing flow_unit updates measurements, TFT/Web metadata and HA."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class FlowUnitLiveTests(unittest.TestCase):
    def test_mode_2_metadata_and_value_use_same_unit(self):
        module = read("src/Modules/IOModule/IOModule.cpp")
        block = module.split("if (slot.inDef.mode == IO_DIGITAL_INPUT_PULSES_PER_MINUTE) {", 1)[1].split("if (!slot.provider.isBound()) return false;", 1)[0]
        self.assertIn("cfg.flowUnit != slot.appliedFlowUnit", block)
        self.assertIn("values.setDisplayUnit(ValueIds::ConvertedRate + slot.logicalIdx", block.replace("dataStore_->", ""))
        self.assertIn("slot.appliedFlowUnit = cfg.flowUnit;", block)
        self.assertIn("pulseFlowConvert((double)measurement.pulsesPerMinute", block)
        self.assertIn("if (!measurement.refreshed && !unitChanged) return validRate;", block)
        self.assertLess(block.index("setDisplayUnit("), block.index("pulseFlowConvert("),
                        "metadata unit must be set before reporting the converted flow")
        self.assertIn("s.appliedFlowUnit = cfg.flowUnit;", module)
        self.assertIn("flowUnitHaDirtyMask_.fetch_or", module)

    def test_registry_updates_metadata_without_redefining_value(self):
        registry = read("src/Core/Values/ValueRegistry.cpp")
        block = registry.split("bool ValueRegistry::setDisplayUnit(", 1)[1].split("void ValueRegistry::setName(", 1)[0]
        self.assertIn("Lock lock(mutex_)", block)
        self.assertIn("strncmp(", block)
        self.assertIn("memcpy(slot.metadata.displayUnit,", block)
        self.assertIn("notification_(", block)
        self.assertNotIn("define(", block)
        self.assertNotIn("slot.runtime =", block)

    def test_home_assistant_refresh_and_tft_catalog(self):
        assembly = read("src/Profiles/Waveshare/WaveshareIoAssembly.cpp")
        block = assembly.split("void refreshIoHomeAssistantIfNeeded(", 1)[1].split("void releaseIoHomeAssistantDiscoveryHeapIfDone(", 1)[0]
        self.assertIn("takeFlowUnitDirtyMask()", block)
        self.assertIn("syncDataSensors(modules);", block)
        self.assertIn("requestRefresh", block)
        web = read("src/Modules/Network/WebInterfaceModule/WebInterfaceServer.cpp")
        self.assertIn('item["unit"] = defined ? meta.displayUnit : descriptor.unit;', web)
        app = read("data/webinterface/app.js")
        self.assertIn("function dynamicTftRuntimeUiOptions(", app)
        self.assertIn("item.unit", app)
        values = json.loads(read("src/Core/Values/catalog.json"))["values"]
        self.assertEqual(next(v["id"] for v in values if v["reference"] == "i05.flow"), 85)

if __name__ == "__main__":
    unittest.main()
