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
assert "text(d,'6.8',21,116,16)" in art
assert "text(d,'8.2',187,116,16)" in art
assert "text(d,'600',21,116,15)" in art
assert "text(d,'800',187,116,15)" in art
assert "text(d,kind,103,135,20)" in art, "pH/ORP labels must be enlarged to 20px"

def event(name):
    match = re.search(r"(?ms)^on " + re.escape(name) +
                      r":\n(.*?)(?=^on |\Z)", source)
    assert match, f"Nextion event missing: {name}"
    return match.group(1)

update = event("bUpdateGauge.down")
# Limit each search to the corresponding HMI gauge. Previously the regular
# expression searched all of bUpdateGauge.down, so for ORP it matched the
# FIRST pH cursor (e.g. x=46) instead of ORP's x=279 cursor.
ph_start = update.index("  //// pH Gauge\n")
orp_start = update.index("  //// ORP Gauge\n", ph_start)
update_end = update.index("  doevents", orp_start)
sections = {
    "vapHPercent": update[ph_start:orp_start],
    "vaOrpPercent": update[orp_start:update_end],
}
for field, destination_x in (("vapHPercent",20),("vaOrpPercent",253)):
    section = sections[field]
    other = "vaOrpPercent" if field == "vapHPercent" else "vapHPercent"
    assert f"sys2={field}.val" in section
    assert f"sys2={other}.val" not in section, (
        f"{field} cursor test accidentally includes the other gauge"
    )
    cases = [int(x) for x in re.findall(r"if\(sys2==(\d+)\)", section)]
    assert cases == list(range(21)), (
        f"{field} must have exactly the 21 cursor positions 0..20: {cases}"
    )
    # ESP32 normalizes around its configured setpoint:
    # centre=140 on a 0..280 gauge, so the central green sector is active.
    assert f"sys0={field}.val+35" in section
    assert "sys0=sys0/70" in section
    assert f"sys2={field}.val" in section
    assert "sys2+=7" in section and "sys2=sys2/14" in section
    xpic = f"xpic {destination_x},89,207,150"
    assert xpic in section
    # Verify the real 3D needle instead of the obsolete 22px rim cursor.
    # Every Nextion position has four layered strokes from the dial centre
    # to the measured angle: shadow, blue side, cyan side, white highlight.
    cx = destination_x + 103
    cy = 159
    for i in range(21):
        a = math.pi+i*math.pi/20
        tx = round(cx + 81*math.cos(a))
        ty = round(cy + 59*math.sin(a))
        # Exact block parsing avoids fragile multiline regex escaping and
        # cannot accidentally match the other dial or a different phase.
        marker = f"    if(sys2=={i})\\n    {{\\n".replace("\\n", "\n")
        assert section.count(marker) == 1, (
            f"missing or duplicate {field} 3D needle at position {i}"
        )
        block = section.split(marker, 1)[1].split("\n    }", 1)[0]
        lines = [item.strip() for item in block.splitlines() if item.strip()]
        assert len(lines) == 4 and all(item.startswith("line ") for item in lines), (
            f"expected four 3D needle strokes for {field} phase {i}: {lines}"
        )
        strokes = []
        for line_text in lines:
            values = [int(x) for x in line_text[5:].split(",")]
            assert len(values) == 5, f"invalid needle stroke: {line_text}"
            strokes.append(values)
        assert [x[4] for x in strokes] == [841,2015,2047,65535], (
            f"missing 3D shadow/blue/cyan/highlight for {field} phase {i}"
        )
        # All four line origins stay inside the 7px central bearing.
        for x0,y0,x1,y1,_ in strokes:
            assert abs(x0-cx) <= 5 and abs(y0-cy) <= 5, (
                f"{field} phase {i} no longer starts at its hub"
            )
            assert abs(x1-tx) <= 3 and abs(y1-ty) <= 3, (
                f"{field} phase {i} tip at {(x1,y1)} not {(tx,ty)}"
            )
            assert destination_x <= min(x0,x1) <= max(x0,x1) < destination_x+207
            assert 89 <= min(y0,y1) <= max(y0,y1) <= 239
        dx = strokes[-1][2]-strokes[-1][0]
        dy = strokes[-1][3]-strokes[-1][1]
        assert dx*dx+dy*dy > 50*50, (
            f"{field} phase {i} is a short rim tick, not a full needle"
        )
    for instruction in (
        f"cirs {cx},159,6,841",
        f"cirs {cx},159,5,2047",
        f"cirs {cx},159,3,1068",
        f"cirs {cx-1},157,1,65535",
    ):
        assert instruction in section, (
            f"missing {field} layered 3D bearing: {instruction}"
        )

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
print("PASS: 21 full-length layered 3D needles and bearings on each dial (0..280)")
print("PASS: no static setpoint arrows, both gauge endpoint labels moved down 7px")
print("PASS: central green zone at configured setpoints, no false warning")
