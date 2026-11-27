#!/usr/bin/env python3
"""Regression gate: each visible Home control has its own matching touch zone.

All coordinates are in native NX4832K035_011 480x320 pixels. This is a
static contract check; physical calibration must still be tested on hardware.
"""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
page = tomllib.loads((BASE / "pages/pageHome.page.toml").read_text(encoding="utf-8"))
source = (BASE / "pages/pageHome.nx").read_text(encoding="utf-8")
art = (ROOT / "nextion/scripts/render_nx_home.py").read_text(encoding="utf-8")
components = {c["name"]: c for c in page["component"]}

# x/y/width/height: visible hit zones, tuned to the drawn icon plus finger
# margin. No zone should capture a neighbouring button or a gauge.
targets = {
    "b0": (8, 268, 72, 45),       # grid / configuration
    "m2": (103, 268, 81, 46),     # triangle / filtration
    "m1": (207, 210, 70, 70),     # central pump / filtration
    "m0": (309, 268, 78, 45),     # gear / equipment switches
    "b1": (412, 268, 62, 45),     # triangle alarm / alarms page
}
# Grounded visible artwork bounds (x0, y0, x1, y1).
drawings = {
    "b0": (23, 273, 49, 298),
    "m2": (130, 273, 161, 314),
    "m1": (207, 210, 277, 280),
    "m0": (333, 274, 365, 306),
    "b1": (433, 276, 467, 304),
}

def bounds(name):
    c = components[name]
    return (int(c["x"]), int(c["y"]), int(c["w"]), int(c["h"]))

def overlap(a, b):
    ax, ay, aw, ah = bounds(a)
    bx, by, bw, bh = bounds(b)
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah

def event(name):
    match = re.search(
        r"(?ms)^on " + re.escape(name) + r":\n(.*?)(?=^on |\Z)", source
    )
    assert match, f"missing Nextion event {name}"
    return match.group(1)

for name, expected in targets.items():
    assert components[name]["type"] == "hotspot", f"{name} must not paint an opaque button"
    assert bounds(name) == expected, f"{name} touch target not aligned"
    x, y, w, h = expected
    assert 0 <= x and 0 <= y and x+w <= 480 and y+h <= 320
    if name != "m1":
        assert y >= 262 and y+h <= 315, f"{name} leaves footer"
    ix0, iy0, ix1, iy1 = drawings[name]
    assert x <= ix0 and x+w >= ix1
    assert y <= iy0 and y+h >= iy1

for i, first in enumerate(targets):
    for second in list(targets)[i+1:]:
        assert not overlap(first, second), f"{first} and {second} steal touches"

# The old 97x98 pump hotspot used to overlap both gauges. It must now be
# exactly the full visual circle (x=207..277,y=210..280).
assert bounds("m1") == (207, 210, 70, 70)

# Native status glyphs used to paint opaque boxes ON the footer, obstructing
# icons and intercepting touches. Keep them entirely above its top edge.
for name in ("tpHInject", "tChlInject", "tSWGRunning"):
    c = components[name]
    assert int(c["y"])+int(c["h"]) <= 262, f"{name} covers the footer"
    assert c["bco"] == "#041225"
    for touched in ("b0", "m2", "m0", "b1"):
        assert not overlap(name, touched), f"{name} overlays {touched}"

# Hidden internal refresh buttons are NOT user touch targets.
load = event("pageHome.load")
for hidden in ("bUpdateGauge", "bDateTime", "bInjectUpdt"):
    assert f"vis {hidden},0" in load

# Controls keep existing action IDs: grid=config; gear=switches;
# pump or play=filtration; alarm=alarms (never a second config action).
assert "page pageCfgMenu" in event("b0.up")
assert "page pageHomeSwtch" in event("m0.down")
assert "printh 23 03 60 09 01" in event("m1.down")
assert "printh 23 03 60 09 01" in event("m2.down")
assert "page pageAlarms" in event("b1.down")
assert "on b1.up:" not in source, "alarm release must not navigate elsewhere"

# The former footer arrow was ambiguous and has been replaced by a gear
# centered on the equipment-switches touch area.
assert "gear_x,gear_y=349,290" in art
assert "d.arc((331*S,273*S,362*S,305*S)" not in art
assert "d.polygon([(143*S,273*S)" in art
assert "line(d,[(450,276),(433,304),(467,304),(450,276)]" in art
assert "FAN_X,FAN_Y,FAN_SIZE=207,210,70" in art

print("PASS: 5 visible controls have aligned and nonoverlapping hotspots")
print("PASS: status glyphs and refresh services do not steal footer touches")
print("PASS: play and centre pump toggle filtration; alarm has one action")
print("PASS: no footer button paints opaque rectangles over the icons")
