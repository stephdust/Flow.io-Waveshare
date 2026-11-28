#!/usr/bin/env python3
"""Regression gate for the actual pageCfgMenu HMI sprites, hit boxes and actions.

A generated PNG with mock values is NOT a native Nextion simulator screenshot.
"""
from pathlib import Path
import argparse
import re
import tomllib
from PIL import Image,ImageChops

p=argparse.ArgumentParser()
p.add_argument("--source",type=Path,required=True)
p.add_argument("--preview",type=Path,required=True)
args=p.parse_args()
page=tomllib.loads((args.source/"pages/pageCfgMenu.page.toml").read_text(encoding="utf-8"))
events=(args.source/"pages/pageCfgMenu.nx").read_text(encoding="utf-8")
c={o["name"]:o for o in page["component"]}
image=Image.open(args.preview).convert("RGB")
assert image.size==(480,320)
assert page["page"]["bco"]=="#041225" and page["page"]["sta"]==2
assert page["page"]["pic"]=="picture-0042"
assert image.getpixel((0,0))==(4,18,37)
sizes={42:(480,320),43:(185,30),44:(185,30),45:(41,34),46:(41,34)}
for n in range(47,59):
    sizes[n]=((56,52) if n in (47,48,49,50) else
              (50,52) if n in (51,52,53,54) else
              (110,52) if n in (55,56) else (62,52))
for number,expected in sizes.items():
    img=Image.open(args.source/"pictures"/f"picture-{number:04d}.png")
    assert img.size==expected,(number,img.size)
    assert ImageChops.difference(img.convert("RGB"),Image.new("RGB",img.size,(4,18,37))).getbbox() is not None,number
for a,b in ((43,44),(45,46),(47,48),(49,50),(51,52),(53,54),(55,56),(57,58)):
    im1=Image.open(args.source/"pictures"/f"picture-{a:04d}.png")
    im2=Image.open(args.source/"pictures"/f"picture-{b:04d}.png")
    assert im1.tobytes()!=im2.tobytes(),(a,b)
touch=["tPath"]
for i in range(6):
    y=37+38*i
    for name,x,dy,w,h in ((f"tL{i}",15,0,212,34),
                          (f"tV{i}",234,2,185,30),
                          (f"bR{i}",426,0,41,34)):
        o=c[name]
        assert (o["x"],o["y"],o["w"],o["h"])==(x,y+dy,w,h),name
        touch.append(name)
        assert f"on {name}." in events,name
    assert c[f"tL{i}"]["type"]=="text" and c[f"tL{i}"]["sta"]==0
    assert c[f"tL{i}"]["picc"]=="picture-0042"
    assert c[f"tV{i}"]["type"]=="dual-state-button" and c[f"tV{i}"]["sta"]==2
    assert c[f"bR{i}"]["type"]=="button" and c[f"bR{i}"]["sta"]==2
for name,x,y,w,h in (("bHome",0,268,56,52),("bBack",60,268,56,52),
                     ("bPrev",120,268,50,52),("bNext",232,268,50,52),
                     ("bValid",365,268,110,52),("bReboot",291,268,62,52)):
    o=c[name]
    assert (o["x"],o["y"],o["w"],o["h"])==(x,y,w,h)
    assert o["type"]=="button" and o["sta"]==2
    touch.append(name)
    sprite=Image.open(args.source/"pictures"/(o["pic"]+".png")).convert("RGB")
    assert image.crop((x,y,x+w,y+h)).tobytes()==sprite.tobytes(),name
for i,one in enumerate(touch):
    a=c[one]
    assert 0<=a["x"] and 0<=a["y"] and a["x"]+a["w"]<=480 and a["y"]+a["h"]<=320
    for other in touch[i+1:]:
        b=c[other]
        overlap=a["x"]<b["x"]+b["w"] and b["x"]<a["x"]+a["w"] and a["y"]<b["y"]+b["h"] and b["y"]<a["y"]+a["h"]
        assert not overlap,(one,other)
# Keep the original Home sprite, but remove its overlapping text rectangle.
assert c["tHomeCaption"]["txt"]=="" and c["tHomeCaption"]["w"]<=2
assert c["tPath"]["sta"]==0 and c["tPath"]["picc"]=="picture-0042"
for key in ("t0","nPage","nPages"):
    assert c[key]["sta"]==0 and c[key]["picc"]=="picture-0042"
assert c["nPage"]["x"]==178 and c["nPages"]["x"]+c["nPages"]["w"]==225
assert c["bBack"]["x"]==c["bHome"]["x"]+c["bHome"]["w"]+4
# Every caption is IN its real bitmap; disabled buttons still have their label.
for name in ("bHome","bBack","bPrev","bNext","bReboot","bValid"):
    button=c[name]
    sprite=Image.open(args.source/"pictures"/(button["pic"]+".png")).convert("RGB")
    white=sum(1 for pixel in sprite.crop((3,36,sprite.width-3,49)).getdata()
              if min(pixel)>210)
    assert white>=10,(name,"missing native bitmap caption",white)
# Native Nextion 3D images should not be obscured by text components.
assert c["tHomeCaption"]["txt"]==""
for key in ("tPath",)+tuple(f"tL{i}" for i in range(6))+("t0","nPage","nPages"):
    assert c[key]["sta"]==0 and c[key]["picc"]=="picture-0042", key
assert re.search(r"(?m)^on bHome.down:\n(?:[^\n]*\n)*?  page pageHome",events)
assert "on bHome.up:" not in events
assert "on bReboot.down:" in events and "tmReboot.en=1" in events
assert "on bReboot.up:" in events and "ref bReboot" in events
assert "vaRebtCounter.val<=50" in events and "page pageReboot" in events
assert re.search(r"(?m)^on bBack.up:\n  printh 23 02 51 02",events)
assert "else if(vaEditType5.val==3)" in events
for name in ("bPrev","bNext","bValid"):
    assert f"on {name}." in events
# The ESP32 must leave unavailable navigation icons visible but inert.
driver=(Path(__file__).resolve().parents[2]/
        "src/Modules/HMIModule/Drivers/NextionDriver.cpp").read_text(encoding="utf-8")
for name in ("bHome","bBack","bValid","bPrev","bNext"):
    assert f'vis {name},1' in driver,name
    assert f'tsw {name},%u' in driver,name

print("PASS: pageCfgMenu original row handlers and 6x3 non-overlapping touch areas")
print("PASS: 3D Home/Back/Prev/Next/Valid/Reboot have baked-in readable captions")
print("PASS: Nextion PNG matches all six real footer sprites")
print("PASS: original Home pictogram, 56px pager, real Nextion text crop")
print("PASS: Home simple, Reboot long-press 2.5s, row5 Boolean fixed")
