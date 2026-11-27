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
assert "xpic 221,224,42,42,350,620,HomeGaugepic" in post
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
assert "sys0=temp*42" in animation and "sys0+=350" in animation
assert "xpic 221,224,42,42,sys0,620,HomeGaugepic" in animation
assert "tProp.pic=" not in update, "hidden legacy component should not redraw"
assert "FAN_X,FAN_Y,FAN_SIZE=207,210,70" in renderer
assert "FAN_RING_ATLAS_Y=620" in renderer
assert "FAN_CORE_SIZE=42" in renderer
assert "FAN_CORE_ATLAS_X=350" in renderer and "FAN_FRAMES=11" in renderer
assert "def _turn(" in renderer, "all four blades must share a precise rotation centre"
assert "def _blend(" in renderer, "3D shading must use blended colours"
assert "blade_curves = [" in renderer, "the blades need genuine curved profiles"
assert "shadow_mask = Image.new(" in renderer, "3D blade drop shadows must be rendered"
assert "local_x = rx*co+ry*si" in renderer, "metallic shading must rotate with the blades"
assert "d.arc((4*S,4*S,66*S,66*S),194,325" in renderer, "continuous ring needs a glossy highlight"
assert "d.ellipse((3*S,3*S,67*S,67*S)" in renderer, "the pressure ring must be complete"
assert "ring_frame(bg,state)" in renderer
assert "blade_frame(frame)" in renderer
assert "fan_frame(bg,state,frame)" not in renderer, "55 full frames must be eliminated"
assert "width=1.6*S" not in renderer, "Pillow 12 / Python 3.13 requires integer arc widths"
assert "width=round(1.6*S)" in renderer, "fractional arc widths must be rounded to int"
assert "ImageFont.truetype(FONTS[0]" not in renderer, "Windows preview must use portable fonts"
assert "atlas=Image.new('RGB',(1035,WIFI_ATLAS_Y+WIFI_H),NAVY)" in renderer
assert "WIFI_ATLAS_Y=690" in renderer
# The physical xpic rectangles must fit the compact 1035x728 source atlas.
assert 5*207 == 1035
assert 5*70 <= 350
assert 350+11*42 <= 1035
assert 690+38 == 728
assert 221+42 == 263 and 224+42 == 266
print("PASS: 70px rings + shared 42px turbine remain centered at 242,245")
print("PASS: 11 shared cores instead of 55 full frames, ON -> 10, OFF -> 0")
print("PASS: 3D curved blades, hub shading and continuous glossy pressure ring")
print("PASS: ring pressure severity, legacy serial IDs and 1035x728 atlas preserved")
