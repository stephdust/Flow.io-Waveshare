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
assert components[-1]["name"] == "tAirTemp", "outdoor widget must stay after legacy components"
assert "m2" not in byname, "redundant play hotspot must stay removed"
assert "vaWaterTemp" in global_components and "vaAirTemp" in global_components
assert water["type"] == air["type"] == "text"
assert water["vscope"] == air["vscope"] == 1
assert water["x"] == air["x"] == 185
assert water["w"] == air["w"] == 113
assert water["font"] == air["font"] == "SegoeUI_16"
assert water["bco"] == air["bco"] == "#041225"
assert byname["tTime"]["bco"] == byname["tDate"]["bco"] == "#041225", (
    "native header labels must not paint rectangular panels over uniform navy"
)
assert water["ycen"] == air["ycen"] == 1
assert 154 < water["x"] and water["x"] + water["w"] <= 300
assert 154 < air["x"] and air["x"] + air["w"] <= 300
assert water["y"] == 5 and water["h"] == 25
assert air["y"] == 30 and air["h"] == 25
assert water["y"] + water["h"] <= air["y"]
assert air["y"] + air["h"] <= 58
for field in ("tTime", "tDate", "tWifiState"):
    other = byname[field]
    assert other["x"] >= 304, f"{field} overlaps temperature column"
assert byname["tTime"]["x"] == byname["tDate"]["x"] == 304
assert byname["tTime"]["w"] == byname["tDate"]["w"] == 106
assert byname["tTime"]["y"] + byname["tTime"]["h"] <= byname["tDate"]["y"]
assert byname["tDate"]["y"] + byname["tDate"]["h"] <= 58
assert byname["tDate"]["x"] + byname["tDate"]["w"] < 413

post = event("pageHome.loadend")
update = event("bUpdateGauge.down")
assert "ref tWaterTemp" in post and "ref tAirTemp" in post
assert "tWaterTemp.txt=globals.vaWaterTemp.txt" in update
assert "tAirTemp.txt=globals.vaAirTemp.txt" in update
assert "click bUpdateGauge,1" in post, "refresh both values after wake"
assert "water_drop=[" in renderer and "(171,6),(174,10)" in renderer
assert "White glass tube, red mercury column and a distinct red bulb." in renderer
assert "d.rounded_rectangle((169*S,12*S,173*S,24*S)" in renderer
assert "fill=(242,48,62,255)" in renderer
assert "fill=(248,48,60,255)" in renderer
assert "sun=(175,39)" in renderer
assert "cloud=(3,26,52,255)" in renderer
assert "d.text((185,18),'27.3°C',font=preview_font(18)" in renderer
assert "d.text((185,43),'7.3°C',font=preview_font(18)" in renderer
assert "d.text((187,20),'27.3°C'" not in renderer
print("PASS: water/outdoor temperatures use existing ESP32 globals")
print("PASS: smaller 16px native temperature fonts, no text background rectangles")
print("PASS: appended component keeps legacy IDs; wake refresh restores both values")
