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
# The previous rendering drew a 185px 3D inset, making each row appear
# split into two buttons. Every 185px off-state value sprite must now be
# pixel-identical to the underlying *full-width* row background.
native_bg=Image.open(args.source/"pictures/picture-0042.png").convert("RGB")
off=Image.open(args.source/"pictures/picture-0043.png").convert("RGB")
on=Image.open(args.source/"pictures/picture-0044.png").convert("RGB")
native_crop=native_bg.crop((234,39,419,69))
assert ImageChops.difference(off,native_crop).getbbox() is None, (
    "A separate inset 185px value-button is visible; use a continuous full-width row"
)
assert on.size==off.size and on.tobytes()!=off.tobytes(), "boolean ON tint must remain distinct"
for a,b in ((43,44),(45,46),(47,48),(49,50),(51,52),(53,54),(55,56),(57,58)):
    im1=Image.open(args.source/"pictures"/f"picture-{a:04d}.png")
    im2=Image.open(args.source/"pictures"/f"picture-{b:04d}.png")
    assert im1.tobytes()!=im2.tobytes(),(a,b)
touch=["tPath"]
for i in range(6):
    y=37+38*i
    for name,x,dy,w,h in ((f"tL{i}",15,0,452,34),
                          (f"tV{i}",234,2,185,30),
                          (f"bR{i}",5,0,470,34)):
        o=c[name]
        assert (o["x"],o["y"],o["w"],o["h"])==(x,y+dy,w,h),name
        touch.append(name)
        assert f"on {name}." in events,name
    assert c[f"tL{i}"]["type"]=="text" and c[f"tL{i}"]["sta"]==0
    assert c[f"tL{i}"]["picc"]=="picture-0042"
    assert c[f"tL{i}"]["font"]=="Segoe24_MenuItems", "label must be readable at 24px"
    assert c[f"tV{i}"]["type"]=="dual-state-button" and c[f"tV{i}"]["sta"]==2
    assert c[f"tV{i}"]["xcen"]==1, "values must be centred"
    assert c[f"tV{i}"]["font"]=="Segoe24_MenuItems", "value must be 24px"
    assert c[f"bR{i}"]["type"]=="hotspot"
    # A full-width visual button must NOT contain a second inset button.
    assert c[f"bR{i}"]["w"]==470
    assert c[f"tV{i}"]["x"]>=c[f"bR{i}"]["x"]
    # The entire visible caption remains touchable, including the former arrow end.
    assert c[f"tL{i}"]["x"] + c[f"tL{i}"]["w"] == 467
    assert "pic" not in c[f"bR{i}"], "native arrow image must not be used"
    assert c[f"bR{i}"]["x"] == 5 and c[f"bR{i}"]["x"] + c[f"bR{i}"]["w"] == 475
    assert f"on tL{i}.down:" in events
    label_event=events.split(f"on tL{i}.down:",1)[1].split(chr(10)+"on ",1)[0]
    assert "if(vaCfgEdit.val==0)" in label_event
    assert f"printh 23 02 52 0{i}" in label_event
    assert f"click tV{i},1" in label_event
    assert f"on bR{i}.down:" in events
    assert f"click tV{i},1" in events
    assert f"printh 23 02 52 0{i}" in events
    assert f"on bR{i}.up:" not in events
for name,x,y,w,h in (("bHome",0,268,56,52),("bBack",60,268,56,52),
                     ("bPrev",120,268,50,52),("bNext",232,268,50,52),
                     ("bValid",365,268,110,52),("bReboot",291,268,62,52)):
    o=c[name]
    assert (o["x"],o["y"],o["w"],o["h"])==(x,y,w,h)
    assert o["type"]=="button" and o["sta"]==2
    touch.append(name)
    sprite=Image.open(args.source/"pictures"/(o["pic"]+".png")).convert("RGB")
    assert image.crop((x,y,x+w,y+h)).tobytes()==sprite.tobytes(),name
    # A muted sprite is embedded in the *real page background*, too:
    # older ESP32 firmware may hide disabled buttons. They must not vanish.
    backing=Image.open(args.source/"pictures/picture-0042.png").convert("RGB")
    faint=backing.crop((x,y,x+w,y+h))
    bright_pixels=sum(
        1 for yy in range(8,32) for xx in range(5,w-5)
        if max(faint.getpixel((xx,yy)))>100
    )
    assert bright_pixels>15,(name,"background lacks disabled icon",bright_pixels)
    assert faint.tobytes()!=sprite.tobytes(),(name,"fallback must look disabled")
for i,one in enumerate(touch):
    a=c[one]
    assert 0<=a["x"] and 0<=a["y"] and a["x"]+a["w"]<=480 and a["y"]+a["h"]<=320
    for other in touch[i+1:]:
        b=c[other]
        overlap=a["x"]<b["x"]+b["w"] and b["x"]<a["x"]+a["w"] and a["y"]<b["y"]+b["h"] and b["y"]<a["y"]+a["h"]
        # The widened text label may be behind its own value/hotspot.
        # Overlap across DIFFERENT rows or footer/header is never allowed.
        intentional_same_row = (
            one.startswith(("tL", "tV", "bR"))
            and other.startswith(("tL", "tV", "bR"))
            and one[-1] == other[-1]
        )
        assert not overlap or intentional_same_row,(one,other)
# Keep the original Home sprite, but remove its overlapping text rectangle.
assert c["tHomeCaption"]["txt"]=="" and c["tHomeCaption"]["w"]<=2
assert c["tPath"]["sta"]==0 and c["tPath"]["picc"]=="picture-0042"
assert c["tPath"]["x"]>=60, "gear icons must not overlap breadcrumb"
for key in ("t0","nPage","nPages"):
    assert c[key]["sta"]==0 and c[key]["picc"]=="picture-0042"
assert c["nPage"]["x"]==178 and c["nPages"]["x"]+c["nPages"]["w"]==225
assert c["bBack"]["x"]==c["bHome"]["x"]+c["bHome"]["w"]+4
# Every caption is IN its real bitmap; disabled buttons still have their label.
for name in ("bHome","bBack","bPrev","bNext","bReboot","bValid"):
    button=c[name]
    sprite=Image.open(args.source/"pictures"/(button["pic"]+".png")).convert("RGB")
    # Count the same bright pixels without Pillow's deprecated getdata().
    # The caption occupies y=36..48 and x=3..width-4.
    white=sum(1 for y in range(36,49)
              for x in range(3,sprite.width-3)
              if min(sprite.getpixel((x,y)))>210)
    assert white>=10,(name,"missing native bitmap caption",white)
# Native Nextion 3D images should not be obscured by text components.
assert c["tHomeCaption"]["txt"]==""
for key in ("tPath",)+tuple(f"tL{i}" for i in range(6))+("t0","nPage","nPages"):
    assert c[key]["sta"]==0 and c[key]["picc"]=="picture-0042", key
assert re.search(r"(?m)^on bHome.down:\n(?:[^\n]*\n)*?  page pageHome",events)
assert "on bHome.up:" not in events
assert "on bReboot.down:" in events and "tmReboot.en=1" in events
assert "on bReboot.up:" in events and "ref bReboot" in events
assert "vaRebtCounter.val<40" in events and "page pageReboot" in events
assert "fill bReboot.x+6,bReboot.y+49,vaRebtCounter.val,2,65535" in events
assert "vaRebtCounter.val,bReboot.h" not in events, "old overlay covered Reboot icon"
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
assert driver.count('"vaCfgEdit.val=%u"') == 2
assert driver.count('const bool fullRowMenu =') == 2
assert 'leftTouchable = false; // prevent duplicate events under the hotspot' in driver
assert 'view.mode == ConfigMenuMode::Edit && row.valueVisible && row.editable' in driver

assert c["vaCfgEdit"]["type"]=="variable"
# Every full-row hotspot routes browsing to RowActivate, and editing to
# the *existing* value widget; no duplicate event on release.
for i in range(6):
    block = events.split(f"on bR{i}.down:", 1)[1].split(chr(10)+"on ", 1)[0]
    assert "if(vaCfgEdit.val==0)" in block
    assert f"printh 23 02 52 0{i}" in block
    assert f"click tV{i},1" in block
assert c["tmReboot"]["tim"]==50
assert "40 ticks x 50 ms = 2 seconds" in events
assert "vaCfgEdit.val=0" in events
for i in range(6):
    assert f"on bR{i}.down:" in events
    assert f"if(vaCfgEdit.val==0)" in events
print("PASS: six 470px continuous visual buttons, label/value touch routing, native editors and 2.0s Reboot")
print("PASS: 3D Home/Back/Prev/Next/Valid/Reboot have baked-in readable captions")
print("PASS: Nextion PNG matches all six real footer sprites")
print("PASS: original Home pictogram, 56px pager, real Nextion text crop")
print("PASS: Home simple, Reboot long-press 2.0s, row5 Boolean fixed")

# All six sample captions contain accents; the preview font must support them.
renderer=(Path(__file__).resolve().parents[2]/"nextion/scripts/render_nx_config.py").read_text(encoding="utf-8")
assert 'ImageFont.truetype("DejaVuSans.ttf",size)' in renderer
assert c["tPath"]["font"]=="Segoe24_MenuItems"
print("PASS: 24px breadcrumb, arrow-free rows and accented preview labels supported")

print("PASS: 24px native fonts on 6 labels and 6 values, fallback icons for hidden navigation")
print("PASS: Reboot power symbol stays visible during long-press progress")
