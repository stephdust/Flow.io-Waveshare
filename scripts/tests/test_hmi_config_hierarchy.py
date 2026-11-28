#!/usr/bin/env python3
"""Verify ONE Web ConfigStore hierarchy across Web and all Nextion panels.

Generate the Web metadata in the real Waveshare profile, generate the C++
header from THAT metadata, then compile/test the native C++ path resolver.
Also verify every declared virtual branch and the MQTT/HA Modbus contract.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts/generate_hmi_config_paths.py"
METADATA = ROOT / "data/webinterface/cfgmods.json"
GENERATED = ROOT / "src/Modules/HMIModule/ConfigMenuPaths_Generated.h"

profile_env = dict(os.environ, FLOW_CFGDOC_PROFILE="waveshare",
                   FLOW_CFGDOC_TFT_ENABLED="1")
subprocess.run([sys.executable, "scripts/generate_config_docs.py"],
               check=True, cwd=ROOT, env=profile_env)
subprocess.run([sys.executable, str(GENERATOR)], check=True, cwd=ROOT)
subprocess.run([sys.executable, str(GENERATOR), "--check"], check=True, cwd=ROOT)

web_meta = json.loads(METADATA.read_text(encoding="utf-8"))["meta"]
aliases = sorted({
    (item["display"], item["store"])
    for item in web_meta["cfg_tree_aliases"]
})
branches = {
    item["display"]: sorted(set(item["children"]))
    for item in web_meta["cfg_tree_virtual_branches"]
}
header = (ROOT / "src/Modules/HMIModule/ConfigMenuPaths.h").read_text(encoding="utf-8")
assert '#include "ConfigMenuPaths_Generated.h"' in header
assert 'static constexpr Alias kAliases[]' not in header, "manual alias list returned"
assert "ioRef(" not in header, "manual analog/digital mapping returned"
assert not any(f'{{"{store}", "{display}"}}' in header for display, store in aliases)

CPP = r"""
#include "src/Modules/HMIModule/ConfigMenuPaths.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char** argv) {
    if (argc < 3) return 7;
    if (strcmp(argv[1], "aliases") == 0) {
        if ((argc - 2) % 2 != 0) return 8;
        for (int i = 2; i < argc; i += 2) {
            char store[128] = {};
            char display[128] = {};
            if (!HmiConfigPaths::toStore(argv[i], store, sizeof(store)) ||
                strcmp(store, argv[i+1]) != 0) {
                fprintf(stderr, "toStore: %s => %s, expected %s\n",
                        argv[i], store, argv[i+1]); return 1;
            }
            if (!HmiConfigPaths::toDisplay(argv[i+1], display, sizeof(display)) ||
                strcmp(display, argv[i]) != 0) {
                fprintf(stderr, "toDisplay: %s => %s, expected %s\n",
                        argv[i+1], display, argv[i]); return 2;
            }
        }
        return 0;
    }
    if (strcmp(argv[1], "branch") == 0) {
        const char* branch = argv[2];
        if (!HmiConfigPaths::isVirtualBranch(branch) ||
            HmiConfigPaths::virtualChildCount(branch) != (size_t)(argc - 3))
            return 3;
        char store[128] = {};
        if (HmiConfigPaths::toStore(branch, store, sizeof(store)))
            return 4;  // A virtual folder is NEVER an editable physical module.
        for (int i = 3; i < argc; ++i) {
            char child[128] = {};
            if (!HmiConfigPaths::virtualChildAt(branch, (size_t)(i-3),
                  child, sizeof(child)) || strcmp(child, argv[i]) != 0) {
                fprintf(stderr, "virtual child: %s expected %s\n", child, argv[i]);
                return 5;
            }
        }
        return 0;
    }
    if (strcmp(argv[1], "through") == 0 && argc == 4) {
        char path[128] = {};
        if (!HmiConfigPaths::toDisplay(argv[2], path, sizeof(path)) ||
            strcmp(path, argv[3]) != 0) return 6;
        if (!HmiConfigPaths::toStore(path, path, sizeof(path))) return 9;
        // Don't alias source/destination in real callers, unlike this test.
        return 0;
    }
    return 10;
}
"""

with tempfile.TemporaryDirectory(prefix="flowio-shared-menu-") as directory:
    work = Path(directory)
    source = work / "check.cpp"
    binary = work / "check"
    source.write_text(CPP, encoding="utf-8")
    subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
         "-I", str(ROOT), str(source), "-o", str(binary)],
        check=True, cwd=ROOT,
    )
    args = [str(binary), "aliases"]
    for display, store in aliases:
        args += [display, store]
    subprocess.run(args, check=True, cwd=ROOT)

    # Every explicit child shown by the Web is present in the Nextion
    # virtual branch, including folders without a physical ConfigStore module.
    for branch, children in branches.items():
        subprocess.run(
            [str(binary), "branch", branch] +
            [f"{branch}/{child}" for child in children],
            check=True, cwd=ROOT,
        )

    # Longest-prefix mapping must retain arbitrary nested store paths.
    # A virtual branch itself cannot be edited; its physical descendants can.
    for display, store in aliases:
        subprocess.run([str(binary), "aliases",
                        display + "/sub/field", store + "/sub/field"],
                       check=True, cwd=ROOT)

    # A new item in Web metadata must flow through without changing any
    # hand-maintained C++ mapping list. The generated header is untracked data.
    synthetic = work / "test-web-cfgmods.json"
    generated = work / "generated.h"
    modified = {
        "meta": {
            "cfg_tree_aliases": web_meta["cfg_tree_aliases"] + [
                {"display": "example/future-device", "store": "futuredevice"}
            ],
            "cfg_tree_virtual_branches": web_meta["cfg_tree_virtual_branches"] + [
                {"display": "example", "children": ["future-device"]}
            ],
        }
    }
    synthetic.write_text(json.dumps(modified), encoding="utf-8")
    subprocess.run([sys.executable, str(GENERATOR),
                    "--source", str(synthetic),
                    "--output", str(generated)], check=True, cwd=ROOT)
    generated_text = generated.read_text(encoding="utf-8")
    assert '"futuredevice", "example/future-device"' in generated_text
    assert '{"example",' in generated_text
    assert '"example/future-device"' in generated_text
    print(f"PASS: {len(aliases)} exact Web aliases and "
          f"{len(branches)} explicit virtual folders shared by all Nextion panels")

# Model must use generated virtual children instead of guessing paths.
model_h = (ROOT / "src/Modules/HMIModule/ConfigMenuModel.h").read_text(encoding="utf-8")
model_cpp = (ROOT / "src/Modules/HMIModule/ConfigMenuModel.cpp").read_text(encoding="utf-8")
assert "MaxRows = 64" in model_h
assert "collectBranchPaths_" in model_cpp
assert "HmiConfigPaths::toDisplay" in model_cpp
assert "HmiConfigPaths::toStore" in model_cpp
assert "HmiConfigPaths::isVirtualBranch(branch)" in model_cpp
assert "HmiConfigPaths::virtualChildAt(branch," in model_cpp
assert "HmiConfigPaths::virtualChildCount(module)" in model_cpp
assert "fillRowFromJson_(store," in model_cpp
assert '"Port %s"' in model_cpp and '"network/modbus-tcp/"' in model_cpp
for old_text in ("char fullPath[28]", "fillRowFromJson_(currentModule_"):
    assert old_text not in model_cpp, old_text

# Assert the visible parent/child hierarchy from the one metadata list.
def displayed(store):
    choices = [(display, prefix) for display, prefix in aliases
               if store == prefix or store.startswith(prefix + "/")]
    if not choices: return store
    target, origin = max(choices, key=lambda a: len(a[1]))
    return target + store[len(origin):]

simulated = [
    "network/modbus-tcp/502", "network/modbus-tcp/503",
    "network/modbus-tcp/504", "wifi", "ethernet", "time", "mqtt",
    "io/input/a00", "io/input/i00", "tft/s3/sensors/slot09",
]
converted = set(displayed(name) for name in simulated)
def immediate(parent):
    if parent in branches:
        return [parent + "/" + child for child in branches[parent]]
    result = set()
    for path in converted:
        if parent:
            if not path.startswith(parent + "/"): continue
            remaining = path[len(parent) + 1:]
            result.add(parent + "/" + remaining.split("/")[0])
        else:
            result.add(path.split("/")[0])
    return sorted(result)

assert "network" in immediate(""), immediate("")
assert "network/modbus-tcp" in immediate("network")
assert immediate("network/modbus-tcp") == [
    "network/modbus-tcp/502",
    "network/modbus-tcp/503",
    "network/modbus-tcp/504",
]
assert "io/input/analog" in immediate("io/input")
assert "io/input/digital" in immediate("io/input")
assert "hmi" in branches and "hmi/tft" in immediate("hmi")
assert "modbustcp502" not in immediate("")

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
print(f"PASS: {len(aliases)} Web aliases, shared virtual branches, "
      "real Modbus ConfigStore, MQTT, HA and Web contracts")

# The widened text label is the primary entry point for BOTH folders and
# leaves, now that the right-hand arrows are intentionally invisible.
hmi_module_cpp = (ROOT / "src/Modules/HMIModule/HMIModule.cpp").read_text(encoding="utf-8")
row_dispatch = hmi_module_cpp.split("case HmiEventType::RowActivate: {", 1)[1]
row_dispatch = row_dispatch.split("case HmiEventType::RowEdit:", 1)[0]
assert row_dispatch.index("menu_.enterRow(e.row)") < row_dispatch.index("menu_.editRow(e.row)")
assert "if (!changed) changed = menu_.editRow(e.row);" in row_dispatch
print("PASS: text tap opens folders first and editable leaf values second")
