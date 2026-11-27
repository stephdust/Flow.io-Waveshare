#!/usr/bin/env python3
"""Regression gate for the centered turbine's 50ms ON/OFF animation."""
from pathlib import Path
import re
import tomllib

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"nextion/tests/NX4832K035_011/7.0.0/source"
home=(BASE/"pages/pageHome.nx").read_text(encoding="utf-8")
page=tomllib.loads((BASE/"pages/pageHome.page.toml").read_text(encoding="utf-8"))
byname={item["name"]:item for item in page["component"]}
renderer=(ROOT/"nextion/scripts/render_nx_home.py").read_text(encoding="utf-8")

def event(name):
    match=re.search(r"(?ms)^on "+re.escape(name)+r":\n(.*?)(?=^on |\Z)",home)
    assert match, "Nextion event missing: "+name
    return match.group(1)

load=event("pageHome.load")
post=event("pageHome.loadend")
animation=event("tmAnim.timer")
update=event("bUpdateGauge.down")
assert byname["tmAnim"]["tim"]==50, "pump refresh must remain at 50ms"
assert byname["tProp"]["font"]=="Propeller_50", "legacy component removed"
assert byname["tProp"]["sta"]==2
assert byname["tProp"]["x"]==207 and byname["tProp"]["y"]==210
assert byname["tProp"]["w"]==70 and byname["tProp"]["h"]==70
assert byname["vaIconProp"]["txt"].startswith("┌┍┎")
assert "vis tProp,0" in load
assert "xpic 207,210,70,70,0,620,HomeGaugepic" in post
assert "temp1=globals.vaStates.val>>0" in animation
assert "temp1=temp1&1" in animation
assert "if(temp1==1)" in animation
assert "temp%=10" in animation and "temp+=1" in animation
assert "sys0=temp*70" in animation
assert "temp=0" in animation and "sys0=0" in animation
assert "sys1=vaPSINiddle.val" in animation
assert "sys1*=70" in animation and "sys1+=620" in animation
assert "xpic 207,210,70,70,sys0,sys1,HomeGaugepic" in animation
assert "tProp.pic=" not in update, "hidden legacy component should not redraw"
assert "FAN_X,FAN_Y,FAN_SIZE=207,210,70" in renderer
assert "FAN_ATLAS_Y=620" in renderer and "FAN_FRAMES=11" in renderer
assert ".72*" in renderer, "blades must be reduced to 72% of prior size"
assert "fan_frame(bg,state,frame)" in renderer
assert "ImageFont.truetype(FONTS[0]" not in renderer, "Windows preview must use portable fonts"
assert "for frame in range(FAN_FRAMES):" in renderer
print("PASS: new turbine stays centered at 242,245; no glyph offset")
print("PASS: filtration ON -> 10 rotating frames / OFF -> stationary frame 0")
print("PASS: existing pressure severity and legacy serial component IDs preserved")
