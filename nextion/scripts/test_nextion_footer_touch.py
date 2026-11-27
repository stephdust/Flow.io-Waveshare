#!/usr/bin/env python3
"""Regression gate: four useful Home touch zones match the visible artwork.

NX4832K035_011 uses 480x320 coordinates. Physical touch accuracy still
requires confirmation on the actual Nextion display.
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
    "b0": (89, 266, 68, 48),      # 3D grid centred exactly under pH (x=123)
    "m1": (205, 239, 70, 70),     # central pump / filtration toggle
    "m0": (314, 266, 64, 48),     # jade gear centred at x=346
    "b1": (409, 266, 62, 48),     # amber warning centred at x=440
}
# Grounded visible artwork bounds (x0, y0, x1, y1).
drawings = {
    "b0": (108, 275, 138, 310),
    "m1": (205, 239, 275, 309),
    "m0": (327, 271, 365, 310),
    "b1": (420, 271, 460, 308),
}

def bounds(name):
    c = components[name]
    return int(c["x"]), int(c["y"]), int(c["w"]), int(c["h"])

def overlaps(a, b):
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
        assert not overlaps(first, second), f"{first} and {second} steal touches"

# The central pump is the ONLY filtration control. Do not retain a redundant
# play triangle, invisible touch area or firmware event.
assert "m2" not in components
assert "on m2.down:" not in source
assert "d.polygon([(143*S,273*S)" not in art
assert "d.arc((130*S,300*S,161*S,314*S)" not in art
assert "for xx in (108,124):" in art
assert "for x in (194,294,387):" not in art, "footer dividers must be removed"
# The entire footer is a flat navy canvas with three floating icons.
# No frames/filled trays and no separators may be drawn behind hotspots.
assert "# Entire page uses one uniform navy background." in art
assert "image=panel(image" not in art, "removed header/footer frame returned"
assert "line(d,[(401,278),(401,302)]" not in art, "removed footer divider returned"
assert "for x in (154,300,413):" not in art, "removed header dividers returned"
assert "FAN_X,FAN_Y,FAN_SIZE=205,239,70" in art
assert abs((205+35)-(123+356)/2) < 1, "rotor must be centered between both gauges"
assert 239 >= 89+150, "rotor should not overlap gauge image rectangles"
assert "d.polygon([(143*S,273*S)" not in art, "removed play glyph came back"

# Native status glyphs used to paint opaque boxes ON the footer, obstructing
# icons and intercepting touches. Keep them entirely above its top edge.
for name in ("tpHInject", "tChlInject", "tSWGRunning"):
    c = components[name]
    assert int(c["y"])+int(c["h"]) <= 262, f"{name} covers the footer"
    assert c["bco"] == "#041225"
    for touched in ("b0", "m0", "b1"):
        assert not overlaps(name, touched), f"{name} overlays {touched}"

# Hidden internal refresh buttons are NOT user touch targets.
load = event("pageHome.load")
for hidden in ("bUpdateGauge", "bDateTime", "bInjectUpdt"):
    assert f"vis {hidden},0" in load

# Existing actions: grid=config; gear=switches; centre pump=filtration;
# alarm=alarms (never a second config action on release).
assert "page pageCfgMenu" in event("b0.up")
assert "page pageHomeSwtch" in event("m0.down")
assert "printh 23 03 60 09 01" in event("m1.down")
assert "page pageAlarms" in event("b1.down")
assert "on b1.up:" not in source

# The old footer arrow has been replaced by a clear gear.
assert "grid_cx,grid_cy=123,290" in art
assert "gear_x,gear_y=346,290" in art
assert "alarm_x,alarm_y=440,290" in art
assert (346-18)-(240+35)>=50, "gear too close to filtration rim"
assert (440-20)-(346+18)>=50, "alarm too close to equipment gear"
assert 440+20<=480-15, "alarm lacks its right-hand breathing space"
assert 123 == 20+103, "grid must be directly under centred pH title"
assert "fill=(7,100,172,255)" in art and "fill=(90,234,255,255)" in art, (
    "cyan/blue glass facets were lost from config icon"
)
assert "fill=(4,134,132,255)" in art and "fill=(237,190,69,255)" in art, (
    "jade gear and gold 3D bearing were lost"
)
assert "fill=(63,244,147,255)" in art and "fill=(6,107,71,255)" in art, (
    "normal alarm icon must be emerald green, not amber"
)
assert "ALARM_ACTIVE_ATLAS_X=544" in art and "def alarm_active_sprite():" in art
assert "fill=(255,83,104)" in art, "active alarm symbol must be red"
assert "text(d,\'flow\',51,31,20" in art
assert "text(d,\'.io\',101,31,20" in art
assert "d.arc((331*S,273*S,362*S,305*S)" not in art
assert "line(d,[(442,276),(427,304),(457,304),(442,276)]" not in art
assert "gear_points=[]" in art, "the equipment button must have real gear teeth"
assert "for tooth in range(10):" in art, "the gear must not revert to sun-like spokes"

print("PASS: four visible controls have aligned, non-overlapping hotspots")
print("PASS: play triangle and duplicate touch action have been removed")
print("PASS: central turbine remains the only filtration toggle")
print("PASS: 3D cyan/jade/green nav icons at x=123/346/440, red when alarm active")
print("PASS: 50px+ icon gaps from pump, centered rotor unchanged at x240")
print("PASS: no footer button paints opaque rectangles over icons")
