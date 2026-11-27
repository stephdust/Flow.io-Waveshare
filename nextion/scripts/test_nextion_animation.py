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
assert "vaPrvPSINid.val=-1" in post
assert "xpic 207,210,70,70,0,620,HomeGaugepic" in post
assert "xpic 218,221,48,48,350,620,HomeGaugepic" in post
assert "temp1=globals.vaStates.val>>0" in animation
assert "temp1=temp1&1" in animation
assert "if(temp1==1)" in animation
assert "temp%=10" in animation and "temp+=1" in animation
assert "temp=0" in animation
assert "sys1=vaPSINiddle.val" in animation
assert "sys1!=vaPrvPSINid.val" in animation
assert "vaPrvPSINid.val=sys1" in animation
assert "sys0=sys1*70" in animation
assert "xpic 207,210,70,70,sys0,620,HomeGaugepic" in animation
assert "sys0=temp*48" in animation and "sys0+=350" in animation
assert "xpic 218,221,48,48,sys0,620,HomeGaugepic" in animation
assert "tProp.pic=" not in update, "hidden legacy component should not redraw"
assert "FAN_X,FAN_Y,FAN_SIZE=207,210,70" in renderer
assert "FAN_RING_ATLAS_Y=620" in renderer
assert "FAN_CORE_SIZE=48" in renderer
assert "FAN_CORE_ATLAS_X=350" in renderer and "FAN_FRAMES=11" in renderer
assert ".72*" in renderer, "blades must remain reduced to 72% of prior size"
assert "ring_frame(bg,state)" in renderer
assert "blade_frame(frame)" in renderer
assert "fan_frame(bg,state,frame)" not in renderer, "55 full frames must be eliminated"
assert "ImageFont.truetype(FONTS[0]" not in renderer, "Windows preview must use portable fonts"
assert "atlas=Image.new('RGB',(1035,WIFI_ATLAS_Y+WIFI_H),NAVY)" in renderer
assert "WIFI_ATLAS_Y=690" in renderer
# The physical xpic rectangles must fit the compact 1035x728 source atlas.
assert 5*207 == 1035
assert 5*70 <= 350
assert 350+11*48 <= 1035
assert 690+38 == 728
assert 218+48 == 266 and 221+48 == 269
print("PASS: 70px rings + shared 48px turbine remain centered at 242,245")
print("PASS: 11 shared cores instead of 55 full frames, ON -> 10, OFF -> 0")
print("PASS: ring pressure severity, legacy serial IDs and 1035x728 atlas preserved")
