#!/usr/bin/env python3
"""Regression checks for live water + outdoor temperatures on 3.5in Home.

The ESP32 already publishes both globals.vaWaterTemp.txt and
globals.vaAirTemp.txt; the HMI only needs to display them.
"""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
page = tomllib.loads((BASE / "pages/pageHome.page.toml").read_text(encoding="utf-8"))
globals_page = tomllib.loads((BASE / "pages/globals.page.toml").read_text(encoding="utf-8"))
source = (BASE / "pages/pageHome.nx").read_text(encoding="utf-8")
renderer = (ROOT / "nextion/scripts/render_nx_home.py").read_text(encoding="utf-8")
components = page["component"]
byname = {component["name"]: component for component in components}
global_components = {component["name"] for component in globals_page["component"]}

def event(name):
    match = re.search(
        r"(?ms)^on " + re.escape(name) + r":\n(.*?)(?=^on |\Z)", source
    )
    assert match, f"missing Nextion event: {name}"
    return match.group(1)

water = byname["tWaterTemp"]
air = byname["tAirTemp"]
assert components[-1]["name"] == "tAirTemp", "new widget must be appended to preserve existing IDs"
assert "vaWaterTemp" in global_components and "vaAirTemp" in global_components
assert water["type"] == air["type"] == "text"
assert water["vscope"] == air["vscope"] == 1
assert water["x"] == air["x"] == 187
assert water["w"] == air["w"] == 109
assert water["font"] == air["font"] == "SegoeUI_16"
assert water["bco"] == air["bco"] == "#031a34"
assert 154 < water["x"] and water["x"] + water["w"] < 300
assert 154 < air["x"] and air["x"] + air["w"] < 300
assert water["y"] == 10 and water["h"] == 19
assert air["y"] == 32 and air["h"] == 19
assert water["y"] + water["h"] < air["y"]
assert air["y"] + air["h"] <= 58
for field in ("tTime", "tDate", "tWifiState"):
    other = byname[field]
    assert other["x"] >= 304, f"{field} overlaps temperature column"

post = event("pageHome.loadend")
update = event("bUpdateGauge.down")
assert "ref tWaterTemp" in post and "ref tAirTemp" in post
assert "tWaterTemp.txt=globals.vaWaterTemp.txt" in update
assert "tAirTemp.txt=globals.vaAirTemp.txt" in update
assert "click bUpdateGauge,1" in post, "refresh both values after wake"
assert "drop=[(171,9)" in renderer
assert "d.arc((163*S,33*S,171*S,41*S)" in renderer
assert "d.text((187,20),'27.3°C'" in renderer
assert "d.text((187,42),'7.3°C'" in renderer
print("PASS: water/outdoor temperatures use existing ESP32 globals")
print("PASS: two readable rows fit the Home header without moving time/date/Wi-Fi")
print("PASS: appended component keeps legacy IDs; wake refresh restores both values")
