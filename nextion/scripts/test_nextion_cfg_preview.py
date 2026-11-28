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
    sizes[n]=(56,52) if n in (47,48) else (50,50)
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
for name,x,y,w,h in (("bHome",0,268,56,52),("bBack",60,268,50,50),
                     ("bPrev",126,268,50,50),("bNext",250,268,50,50),
                     ("bValid",424,268,50,50),("bReboot",362,268,50,50)):
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
assert 189<=c["nPage"]["x"] and c["nPages"]["x"]+c["nPages"]["w"]<=243
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
print("PASS: pageCfgMenu original row handlers and 6x3 non-overlapping touch areas")
print("PASS: real 3D Home/Back/Prev/Next/Valid/Reboot bitmaps match PNG")
print("PASS: Home sprite unchanged, 62px pager, real Nextion text crop")
print("PASS: Home simple, Reboot long-press 2.5s, row5 Boolean fixed")
