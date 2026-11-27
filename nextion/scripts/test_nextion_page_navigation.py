#!/usr/bin/env python3
"""Audit the touch navigation graph for the 3.5in Nextion HMI.

Only direct HMI 'page NAME' commands are considered here; an ESP32 serial
command can open additional pages, so an unlinked page is not proof that
its assets are dead. Never delete those page pictures based on this graph.
"""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
app = tomllib.loads((SRC / "app.toml").read_text(encoding="utf-8"))
pages = app["pages"]
assert len(pages) == 9, "review page inventory before asset cleanup"
program = (SRC / "program.nx").read_text(encoding="utf-8")
assert re.search(r"(?m)^page pageHome\b", program), "startup Home lost"

edges = {}
for name in pages:
    path = SRC / "pages" / f"{name}.nx"
    assert path.is_file(), f"missing script for {name}"
    body = path.read_text(encoding="utf-8")
    edges[name] = {destination for destination in
                   re.findall(r"(?m)^\s*page\s+(page\w+)\s*(?://.*)?$", body)}
    assert edges[name] <= set(pages), f"{name} references removed page"

reachable = {"pageHome"}
while True:
    updated = reachable | set().union(*(edges[name] for name in reachable))
    if updated == reachable:
        break
    reachable = updated

assert {"pageHome", "pageCfgMenu", "pageAlarms", "pageHomeSwtch",
        "pageKeyBoard", "pageKeyPad", "pageReboot"} <= reachable, (
    f"lost access to an existing user page: {reachable}"
)
disconnected = sorted(set(pages) - reachable - {"globals"})
assert set(disconnected) <= {"pageSetTime"}, (
    f"unexplained page with no native touch path: {disconnected}"
)
if "pageSetTime" in disconnected:
    print("NOTICE: pageSetTime has no direct native 'page pageSetTime' "
          "link; it may still be opened by a serial command. "
          "Keep picture-0005 and the date/time page.")
print(f"PASS: {len(pages)} pages; native Home graph reaches "
      f"{len(reachable)} pages")
print("PASS: config, alarm, switches, keypad, keyboard and reboot linked")
