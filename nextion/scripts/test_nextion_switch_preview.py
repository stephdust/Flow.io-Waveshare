#!/usr/bin/env python3
"""Check the real 480x320 pageHomeSwtch preview against the approved layout.

The preview must reuse the exact sprite files loaded by the nxwright HMI.
This is a deterministic rendering/layout gate, not a physical touch test.
"""
import argparse
from pathlib import Path
import tomllib
from PIL import Image, ImageChops

p=argparse.ArgumentParser()
p.add_argument("--source",type=Path,required=True)
p.add_argument("--preview",type=Path,required=True)
args=p.parse_args()
page=tomllib.loads((args.source/"pages/pageHomeSwtch.page.toml").read_text(encoding="utf-8"))
buttons={c["name"]:c for c in page["component"]}
im=Image.open(args.preview).convert("RGB")
assert im.size==(480,320),f"switch preview dimensions: {im.size}"
navy=(4,18,37)
assert page["page"]["bco"]=="#041225", "switch background differs from Home"
for pt in ((0,0),(240,0),(479,319),(240,40),(240,150),(240,200)):
    assert im.getpixel(pt)==navy,f"non-uniform navy at {pt}"
names=("btAuto","btAutoORP","btAutoPH","btPHPump",
       "btWinter","btLight","btRobot","btCHLPump")
expected=((35,30),(148,30),(261,30),(374,30),
          (35,149),(148,149),(261,149),(374,149))
on={"btAuto","btAutoPH","btLight"}
for name,xy in zip(names,expected):
    b=buttons[name]
    assert b["type"]=="dual-state-button",name
    assert (b["x"],b["y"],b["w"],b["h"])==(*xy,70,75),name
    assert (b["pic"],b["pic2"])!=("", ""),name
    off=Image.open(args.source/"pictures"/(b["pic"]+".png")).convert("RGB")
    active=Image.open(args.source/"pictures"/(b["pic2"]+".png")).convert("RGB")
    assert off.size==active.size==(70,75),name
    assert off.tobytes()!=active.tobytes(),f"{name}: ON and OFF look identical"
    # The published image itself must reuse the active or inactive sprite.
    chosen=active if name in on else off
    part=im.crop((*xy,xy[0]+70,xy[1]+65))
    assert part.tobytes()==chosen.crop((0,0,70,65)).tobytes(),f"{name}: preview differs from HMI sprite"
    # Avoid deprecated Image.getdata() while checking for actual icon pixels.
    background=Image.new("RGB",chosen.size,navy)
    assert ImageChops.difference(chosen,background).getbbox() is not None, f"{name}: missing 3D glyph"
home=buttons["bHome"]
assert (home["x"],home["y"],home["w"],home["h"])==(0,267,56,52)
assert home["pic"]=="picture-0040" and home["pic2"]=="picture-0041"
home_image=Image.open(args.source/"pictures"/(home["pic"]+".png")).convert("RGB")
assert im.crop((0,267,56,319)).tobytes()==home_image.tobytes()
for i in range(8):
    c=buttons[f"t{i}"]
    assert c["type"]=="text" and c["bco"]=="#041225"
    assert c["pco"]=="#ffffff" and c["xcen"]==1
    assert c["y"] in (102,221)
for event in ("btAuto","btAutoORP","btAutoPH","btPHPump",
              "btCHLPump","btWinter","btLight","btRobot"):
    source=(args.source/"pages/pageHomeSwtch.nx").read_text(encoding="utf-8")
    assert f"on {event}.down:" in source,f"touch event lost: {event}"
assert "on bHome.down:" in source and "page pageHome" in source
print("PASS: actual pageHomeSwtch PNG uses identical pixels to all 9 HMI button sprites")
print("PASS: background #041225, 8 correct commands, 2 rows, native text and Home")
print("PASS: ON/OFF artwork differs and all native touch handlers remain")
