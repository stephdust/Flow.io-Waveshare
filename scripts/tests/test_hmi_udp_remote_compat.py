#!/usr/bin/env python3
"""Offline integration contract for local UART and FlowConnectDisplay UDP.

Run against an actual checkout of the *other* repository. CI checks out
stephdust/Flow.io-RemoteDisplay, applies the staged source patch in a sandbox,
and compiles BOTH firmwares without modifying RemoteDisplay/main.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--remote-root", type=Path, required=True)
parser.add_argument("--patched", action="store_true")
args = parser.parse_args()
remote = args.remote_root.resolve()
assert remote.is_dir(), f"RemoteDisplay checkout missing: {remote}"

def read(root: Path, rel: str) -> str:
    file = root / rel
    assert file.is_file(), f"Missing {file}"
    return file.read_text(encoding="utf-8")

protocol = "src/Core/Hmi/HmiUdpProtocol.h"
protocol_impl = "src/Core/Hmi/HmiUdpProtocol.cpp"
for path in (protocol, protocol_impl):
    assert read(ROOT, path) == read(remote, path), (
        f"{path} differs between Flow.io and RemoteDisplay; "
        "synchronize the two copies and review wire version"
    )
h = read(ROOT, protocol)
assert "HMI_UDP_VERSION = 7;" in h, "unexpected UDP wire version"
assert "HMI_UDP_MAX_PACKET = 512;" in h
assert "HMI_UDP_CONFIG_SNAPSHOT_ROWS = ConfigMenuModel::RowsPerPage" in h
assert "ConfigViewSnapshot = 34" in h
assert "HMI_UDP_FLAG_ACK_REQUIRED = 0x01" in h

def enum_body(root: Path, name: str) -> str:
    s = read(root, "src/Modules/HMIModule/Drivers/HmiDriverTypes.h")
    m = re.search(r"enum class " + name + r"\s*:\s*uint8_t\s*\{([^}]+)\}", s)
    assert m, f"enum {name} missing"
    return m.group(1)

# Config menu navigation, editing, text and context events must have matching
# IDs in the two binaries: UDP does not translate these event IDs.
assert enum_body(ROOT, "HmiEventType") == enum_body(remote, "HmiEventType"), (
    "HmiEventType IDs differ between the two firmware repositories"
)

for root in (ROOT, remote):
    f = read(root, "src/Modules/HMIModule/ConfigMenuModel.h")
    assert re.search(r"RowsPerPage\s*=\s*6\s*;", f), root
    assert "char breadcrumb[96]{};" in f
    assert "uint32_t contextRef = 0U;" in f
    assert "char label[28]{};" in f

flow_server = read(ROOT, "src/Modules/Network/HmiUdpServerModule/HmiUdpServerModule.cpp")
flow_driver = read(ROOT, "src/Modules/HMIModule/Drivers/RemoteHmiUdpDriver.cpp")
flow_hmi = read(ROOT, "src/Modules/HMIModule/HMIModule.cpp")
remote_client = read(remote, "src/Modules/FlowConnectDisplay/FlowConnectDisplayUdpClientModule/FlowConnectDisplayUdpClientModule.cpp")
remote_driver = read(remote, "src/Modules/HMIModule/Drivers/NextionDriver.cpp")

assert "return udpServer_->sendConfigViewSnapshot(view);" in flow_driver
assert "hmiUdpPayloadToEvent" in flow_server and "pushEvent_(event)" in flow_server
assert "HmiUdpMsgType::ConfigViewSnapshot" in flow_server
assert "HmiUdpMsgType::ConfigViewSnapshot" in remote_client
assert "configView_.contextRef = p->contextRef;" in remote_client
assert "copyText_(row.label, sizeof(row.label), src.label);" in remote_client
assert "copyText_(row.value, sizeof(row.value), src.value);" in remote_client
assert "nextion_.renderConfigMenu(configView_)" in remote_client
assert "hmiUdpEventToPayload(event, payload)" in remote_client
assert "requestFullRefresh_(" in remote_client and "ConfigEnter" in remote_client
assert "menu_.buildView(view)" in flow_hmi, "Flow.io must own the ConfigStore tree"
assert "kNextionLegacyV6DisplayVersion = \"6.0.0\"" in flow_hmi
assert "kNextionDisplayVersionExpected" in flow_hmi
assert "HmiUdpConfigTitle::format(payload.title" in flow_server
assert flow_server.count("HmiUdpConfigTitle::format(payload.title") == 2

# Keep the deployed protocol v7 unchanged. The 24-byte title is compacted on
# Flow.io but the full display paths always stay on the authoritative server.
assert "char title[24];" in h
assert "char label[24];" in h and "char value[24];" in h
# packed header 13, snapshot 33 + 6*52 = 345, full wire packet 358.
assert 13 + (1 + 1 + 1 + 1 + 1 + 4 + 24 + 6 * (4 + 24 + 24)) == 358
assert 358 <= 512

if args.patched:
    assert 'strcmp(displayVersion_, "7.0.0") == 0' in remote_driver
    assert 'threeDMenu || view.canBack' in remote_driver
    assert 'threeDMenu || view.canValidate' in remote_driver
    assert 'threeDMenu || canPrev' in remote_driver
    assert 'threeDMenu || canNext' in remote_driver
    assert "const bool restoreContext = contextRef != 0U" in remote_driver
    assert "return emitted || restoreContext;" in remote_driver

# Execute actual C++ formatting code, not a Python reimplementation.
CPP = r"""
#include "src/Core/Hmi/HmiUdpConfigTitle.h"
#include <stdio.h>
#include <string.h>

static int verify(const char* breadcrumb, const char* expected) {
    char text[24] = {};
    HmiUdpConfigTitle::format(text, sizeof(text), breadcrumb);
    if (strcmp(text, expected) != 0) {
        fprintf(stderr, "title '%s' => '%s', expected '%s'\n",
                breadcrumb, text, expected);
        return 1;
    }
    return 0;
}
int main() {
    if (verify("config", "config")) return 1;
    if (verify("config > network", "network")) return 2;
    if (verify("config > network > modbus-tcp > 502",
               "network/modbus-tcp/502")) return 3;
    if (verify("config > network > modbus-tcp > 502 [EDIT]",
               "network/modbus-tcp/502")) return 4;
    if (verify("config > io > input > analog > a20",
               "io/input/analog/a20")) return 5;
    if (verify("config > hmi > tft > sensors > slot09",
               "hmi/tft/sensors/slot09")) return 6;
    char tiny[8] = {};
    HmiUdpConfigTitle::format(tiny, sizeof(tiny),
                              "config > someextraordinarilylongnode");
    if (tiny[7] != '\0' || strlen(tiny) != 7U) return 7;
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="flowio-udp-contract-") as directory:
    work = Path(directory)
    source = work / "check.cpp"
    binary = work / "check"
    source.write_text(CPP, encoding="utf-8")
    subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-I", str(ROOT), str(source), "-o", str(binary)],
                   check=True, cwd=ROOT)
    subprocess.run([str(binary)], check=True, cwd=ROOT)

print("PASS: UDP v7 protocol bytes, 6-row snapshot, context, bidirectional "
      "Nextion events, 6/7-inch TFT version compatibility, compact title")
if args.patched:
    print("PASS: RemoteDisplay patched 7.0.0 3D navigation and same-page "
          "ConfigEnter context restoration; legacy 6.0.0 kept")
