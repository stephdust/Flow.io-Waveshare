#!/usr/bin/env python3
"""Regression gate for the footer's Home-switch icon touch target."""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
page = tomllib.loads((BASE / "pages/pageHome.page.toml").read_text(encoding="utf-8"))
source = (BASE / "pages/pageHome.nx").read_text(encoding="utf-8")
components = {c["name"]: c for c in page["component"]}

def bounds(name):
    c = components[name]
    return int(c["x"]), int(c["y"]), int(c["w"]), int(c["h"])

def overlaps(a, b):
    ax, ay, aw, ah = bounds(a)
    bx, by, bw, bh = bounds(b)
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah

x, y, w, h = bounds("m0")
assert components["m0"]["type"] == "hotspot"
assert (x, y, w, h) == (305, 268, 82, 46)
# The visible bottom icon occupies approximately x=331..367, y=273..305.
assert x <= 331 and x+w >= 367 and y <= 273 and y+h >= 305
# No accidental touch capture over gauge, header or central pump.
assert y >= 262 and y+h <= 316
assert not overlaps("m0", "m1")
assert not overlaps("m0", "b0")
assert not overlaps("m0", "b1")
assert re.search(r"(?m)^on m0.down:\n  page pageHomeSwtch\s*$", source)
print("PASS: bottom switch hotspot matches icon and does not steal gauge touches")
print("PASS: existing Home-switch action and component identity preserved")
