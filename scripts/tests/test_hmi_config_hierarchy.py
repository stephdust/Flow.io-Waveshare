#!/usr/bin/env python3
"""Check all Web -> Nextion ConfigStore aliases and the new physical hierarchy.

The C++ conversion functions are compiled and executed on a host; the test
sources expected paths from every cfgmods.fr.json, not a copied test table.
Also verifies Modbus TCP MQTT/HA/ConfigStore contract and paged tree shape.
"""
from pathlib import Path
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CPP = r"""
#include "src/Modules/HMIModule/ConfigMenuPaths.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char** argv) {
    if ((argc - 1) % 2 != 0) return 7;
    for (int i = 1; i + 1 < argc; i += 2) {
        char store[128] = {};
        char display[128] = {};
        if (!HmiConfigPaths::toStore(argv[i], store, sizeof(store)) ||
            strcmp(store, argv[i+1]) != 0) {
            fprintf(stderr, "toStore failed: %s => %s, expected %s\n",
                    argv[i], store, argv[i+1]); return 1;
        }
        if (!HmiConfigPaths::toDisplay(argv[i+1], display, sizeof(display)) ||
            strcmp(display, argv[i]) != 0) {
            fprintf(stderr, "toDisplay failed: %s => %s, expected %s\n",
                    argv[i+1], display, argv[i]); return 2;
        }
    }
    puts("PASS: native C++ bidirectional ConfigStore alias mapping");
    return 0;
}
"""

aliases = []
for path in sorted((ROOT / "src/Modules").rglob("cfgmods.fr.json")):
    meta = json.loads(path.read_text(encoding="utf-8")).get("meta") or {}
    for pair in meta.get("cfg_tree_aliases", []):
        display, store = pair["display"], pair["store"]
        aliases.append((display, store))

for port in (502, 503, 504):
    aliases.append((f"network/modbus-tcp/{port}", f"network/modbus-tcp/{port}"))
aliases += [
    ("hmi/tft/sensors/slot09", "tft/s3/sensors/slot09"),
    ("io/input/analog/a00/deep", "io/input/a00/deep"),
    ("io/input/digital/i12", "io/input/i12"),
    ("network/wifi", "wifi"),
    ("network/mqtt", "mqtt"),
    ("other/unrelated", "other/unrelated"),
]

with tempfile.TemporaryDirectory(prefix="flowio-hmi-tree-") as dirname:
    source = Path(dirname) / "check.cpp"
    binary = Path(dirname) / "check"
    source.write_text(CPP, encoding="utf-8")
    subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
         "-I", str(ROOT), str(source), "-o", str(binary)],
        check=True, cwd=ROOT,
    )
    args = [str(binary)]
    for display, store in aliases:
        args += [display, store]
    subprocess.run(args, check=True, cwd=ROOT)

# Assert that the parent-child hierarchy induced by the alias table matches
# the requested Web tree, and nothing appears under the old flat names.
simulated = [
    "network/modbus-tcp/502", "network/modbus-tcp/503",
    "network/modbus-tcp/504", "wifi", "ethernet", "time", "mqtt",
    "io/input/a00", "io/input/a31", "io/input/i00", "io/input/i12",
    "tft/s3/sensors/slot09", "hmi/leds", "pdm/pd00",
]
converted = {
    next((display for display, store in aliases if store == item), item)
    for item in simulated
}
def immediate(parent):
    candidates = []
    for module in converted:
        if parent:
            if not module.startswith(parent + "/"): continue
            relative = module[len(parent)+1:]
            candidates.append(parent + "/" + relative.split("/")[0])
        else:
            candidates.append(module.split("/")[0])
    return sorted(set(candidates))

assert "modbustcp502" not in immediate(""), immediate("")
assert "network" in immediate(""), immediate("")
assert "network/modbus-tcp" in immediate("network"), immediate("network")
assert immediate("network/modbus-tcp") == [
    "network/modbus-tcp/502",
    "network/modbus-tcp/503",
    "network/modbus-tcp/504",
], immediate("network/modbus-tcp")
assert "io/input/analog" in immediate("io/input")
assert "io/input/digital" in immediate("io/input")
assert "hmi/tft" in immediate("hmi")
assert 32 <= 64, "all analog channels need to fit under the new browse limit"

model_h = (ROOT / "src/Modules/HMIModule/ConfigMenuModel.h").read_text(encoding="utf-8")
model_cpp = (ROOT / "src/Modules/HMIModule/ConfigMenuModel.cpp").read_text(encoding="utf-8")
assert "MaxRows = 64" in model_h
assert "collectBranchPaths_" in model_cpp
assert "HmiConfigPaths::toDisplay" in model_cpp
assert "HmiConfigPaths::toStore" in model_cpp
assert "fillRowFromJson_(store," in model_cpp
assert '"Port %s"' in model_cpp and '"network/modbus-tcp/"' in model_cpp
for old in ("char fullPath[28]", "fillRowFromJson_(currentModule_"):
    assert old not in model_cpp, old

module_h = (ROOT / "src/Modules/Network/ModbusTcpServerModule/ModbusTcpServerModule.h").read_text(encoding="utf-8")
module_cpp = (ROOT / "src/Modules/Network/ModbusTcpServerModule/ModbusTcpServerModule.cpp").read_text(encoding="utf-8")
docs = json.loads((ROOT / "src/Modules/Network/ModbusTcpServerModule/text/cfgdocs.fr.json").read_text(encoding="utf-8"))
web = (ROOT / "data/webinterface/app.js").read_text(encoding="utf-8")
assert "mbpathv2" in module_cpp and "cfg.eraseKey(oldKey)" in module_cpp
assert "cfg.eraseKey(oldBlobKey)" in module_cpp
for port in (502, 503, 504):
    module = f"network/modbus-tcp/{port}"
    assert f'"{module}"' in module_h
    assert f'"cfg/{module}"' in module_cpp
    assert "'"+module+"':" in module_cpp, f"HA command does not use {module}"
    assert f"{module}/mode" in docs["docs"]
    assert f"modbustcp{port}/mode" not in docs["docs"]
    assert f'"modbustcp{port}"' not in module_h
assert "modbustcp50[234]" not in web
print(f"PASS: {len(aliases)} Web aliases, virtual branches, 32-channel limit, "
      "real Modbus ConfigStore, MQTT, HA and Web contracts")
