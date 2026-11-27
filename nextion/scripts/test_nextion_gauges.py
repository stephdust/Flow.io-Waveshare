#!/usr/bin/env python3
"""Home 3.5in gauge contract: correct safety colours and live needle bars.

This test runs before image generation so an invalid palette, fixed 7.5/700
marker or broken 0..280 measurement mapping cannot reach a TFT release.
"""
from pathlib import Path
import math
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
art = (ROOT / "nextion/scripts/render_nx_home.py").read_text(encoding="utf-8")
source = (BASE / "pages/pageHome.nx").read_text(encoding="utf-8")
page = tomllib.loads((BASE / "pages/pageHome.page.toml").read_text(encoding="utf-8"))
byname = {c["name"]: c for c in page["component"]}

palette = re.search(r"colors=\(\((254,39,86).*?\)\)", art, re.S)
assert palette, "red-amber-green-amber-red palette missing"
assert "colors=((254,39,86),(255,212,32),(98,252,55)," in art
assert "(255,212,32),(254,39,86))" in art
assert "text(d,value,x,72" not in art, "legacy setpoint labels reappeared"
assert "for x,value in ((123,'7.5'),(357,'700')):" not in art
assert "text(d,'6.8',21,109,16)" in art
assert "text(d,'8.2',187,109,16)" in art
assert "text(d,'600',21,109,15)" in art
assert "text(d,'800',187,109,15)" in art

def event(name):
    match = re.search(r"(?ms)^on " + re.escape(name) +
                      r":\n(.*?)(?=^on |\Z)", source)
    assert match, f"Nextion event missing: {name}"
    return match.group(1)

update = event("bUpdateGauge.down")
for field, destination_x in (("vapHPercent",20),("vaOrpPercent",253)):
    # ESP32 normalizes around its configured setpoint:
    # centre=140 on a 0..280 gauge, so the central green sector is active.
    assert f"sys0={field}.val+35" in update
    assert "sys0=sys0/70" in update
    assert f"sys2={field}.val" in update
    assert "sys2+=7" in update and "sys2=sys2/14" in update
    xpic = f"xpic {destination_x},89,207,150"
    assert xpic in update
    first_x = destination_x + 103
    for i in range(21):
        a = math.pi+i*math.pi/20
        inner_x = round(first_x + 77*math.cos(a))
        inner_y = round(89 + 96.5 + 66*math.sin(a))
        outer_x = round(first_x + 99*math.cos(a))
        outer_y = round(89 + 96.5 + 85*math.sin(a))
        # The source was generated using round-half-up; Python's round()
        # uses ties-to-even. Allow at most one pixel for that difference,
        # without weakening the colour, 21-position or alignment checks.
        match = re.search(
            rf"if\(sys2=={i}\)\s*\{{\s*line [^\n]+2047\s*"
            rf"line (\d+),(\d+),(\d+),(\d+),65535\s*"
            rf"line [^\n]+2047",
            update,
        )
        assert match, f"missing {field} measurement bar at phase {i}"
        actual = [int(x) for x in match.groups()]
        expected = [inner_x, inner_y, outer_x, outer_y]
        assert all(abs(a-b) <= 1 for a,b in zip(actual, expected)), (
            f"misaligned {field} cursor {i}: got {actual}, expected {expected}"
        )
        assert destination_x <= min(inner_x,outer_x) <= max(inner_x,outer_x) < destination_x+207
        assert 89 <= inner_y <= 239 and 89 <= outer_y <= 239

# Zero = far left red, 140 = central green, 280 = far right red.
bucket = lambda percent: min(4,(percent+35)//70)
assert [bucket(v) for v in (0,70,140,210,280)] == [0,1,2,3,4]
assert bucket(146) == bucket(144) == 2, "pH 7.60 and ORP 706 must be green"
assert "draw_preview_gauge_cursor(demo, 20, 146)" in art
assert "draw_preview_gauge_cursor(demo, 253, 144)" in art

# Existing touch/callback IDs must remain unchanged.
assert byname["tpH"]["x"] == 87 and byname["tORP"]["x"] == 321
assert "m2" not in byname
print("PASS: original-style danger/attention/good/attention/danger gauge colours")
print("PASS: 21 live measurement pointers on each dial (0..280)")
print("PASS: no static setpoint arrows and larger range endpoint labels")
print("PASS: central green zone at configured setpoints, no false warning")
