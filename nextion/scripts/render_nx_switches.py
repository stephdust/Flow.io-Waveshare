#!/usr/bin/env python3
"""Generate 3D switch-state graphics for the NX4832K035 pageHomeSwtch.

All bitmaps are regenerated in the scratch source by run_nextion.py.
The native button IDs and touch/serial events are deliberately untouched.
"""
from pathlib import Path
import argparse
import math
import tomllib
from PIL import Image, ImageDraw, ImageFont

NAVY=(4,18,37)
S=3
KINDS=("filtration","orp","ph","pump-ph","pump-chlore","winter","light","robot")

def make_sprite(kind, on, w=70, h=75):
    im=Image.new("RGB",(w*S,h*S),NAVY)
    d=ImageDraw.Draw(im)
    cx,cy=w/2,h/2
    def coords(b): return tuple(round(v*S) for v in b)
    def ellipse(b,fill,outline=None,width=1): d.ellipse(coords(b),fill=fill,outline=outline,width=max(1,int(width*S)))
    def rect(b,fill,r=3,outline=None,width=1): d.rounded_rectangle(coords(b),radius=r*S,fill=fill,outline=outline,width=max(1,width*S))
    def line(points,fill,width=1): d.line([(round(x*S),round(y*S)) for x,y in points],fill=fill,width=max(1,round(width*S)),joint="curve")
    def poly(points,fill,outline=None):
        d.polygon([(round(x*S),round(y*S)) for x,y in points],fill=fill)
        if outline: line(points+[points[0]],outline)
    r=29 if w==70 else 21
    ellipse((cx-r+1,cy-r+3,cx+r+1,cy+r+3),(0,7,21))
    ellipse((cx-r,cy-r,cx+r,cy+r),(3,47,82),outline=(32,201,245) if on else (76,146,190),width=2)
    ellipse((cx-r+4,cy-r+4,cx+r-4,cy+r-4),(3,29,59),outline=(8,114,170))
    ellipse((cx-r+7,cy-r+6,cx+r-7,cy+r-8),(11,69,117) if on else (26,54,86))
    d.arc(coords((cx-r+6,cy-r+4,cx+r-6,cy+r-6)),194,348,fill=(146,240,255),width=2*S)
    if on: ellipse((cx+r-9,cy-r+5,cx+r-4,cy-r+10),(65,247,143),outline=(215,255,234))
    if kind=="filtration":
        ellipse((cx-13,cy-14,cx+13,cy+12),(5,112,171),outline=(173,243,255),width=2)
        line([(cx-10,cy-3),(cx-3,cy+5),(cx+13,cy-12)],(215,255,250),4)
    elif kind in ("orp","ph"):
        poly([(cx-8,cy-15),(cx+8,cy-15),(cx+7,cy-5),(cx+7,cy+4),(cx+12,cy+13),(cx-12,cy+13),(cx-7,cy+4),(cx-7,cy-5)],(219,239,250),(255,255,255))
        poly([(cx-8,cy+5),(cx+8,cy+5),(cx+11,cy+12),(cx-11,cy+12)],(255,154,47) if kind=="orp" else (12,191,243))
        line([(cx-3,cy-12),(cx-3,cy+3)],(111,176,213),1)
    elif kind in ("pump-ph","pump-chlore"):
        ellipse((cx-15,cy-13,cx+15,cy+14),(182,208,223),outline=(245,250,255),width=2)
        ellipse((cx-11,cy-9,cx+11,cy+10),(11,58,87))
        ellipse((cx-6,cy-5,cx+6,cy+7),(246,91,117) if kind=="pump-ph" else (29,225,164),outline=(220,250,253),width=2)
        rect((cx-16,cy-12,cx-7,cy-7),(137,180,211),2)
        rect((cx+7,cy+8,cx+17,cy+12),(137,180,211),2)
    elif kind=="winter":
        for a in range(0,360,60):
            th=math.radians(a)
            ux,uy=math.cos(th),math.sin(th)
            line([(cx-ux*15,cy-uy*15),(cx+ux*15,cy+uy*15)],(16,123,192),4)
            line([(cx-ux*15,cy-uy*15),(cx+ux*15,cy+uy*15)],(225,252,255),2)
            for sign in (-1,1):
                x,y=cx+ux*sign*10,cy+uy*sign*10
                ex,ey=cx+ux*sign*5,cy+uy*sign*5
                px,py=-uy,ux
                for k in (-1,1):line([(x+px*k*5,y+py*k*5),(ex,ey)],(180,237,255),1.6)
        ellipse((cx-3,cy-3,cx+3,cy+3),(250,255,255))
    elif kind=="light":
        ellipse((cx-13,cy-16,cx+13,cy+9),(255,206,62),outline=(255,248,179),width=2)
        ellipse((cx-7,cy-14,cx+4,cy-4),(255,249,186))
        rect((cx-7,cy+7,cx+7,cy+13),(179,209,221),2)
        rect((cx-5,cy+13,cx+5,cy+17),(214,230,242),2)
    elif kind=="robot":
        rect((cx-14,cy-10,cx+14,cy+12),(60,177,221),5,outline=(224,248,255),width=2)
        rect((cx-10,cy-7,cx+10,cy+1),(14,69,126),3)
        ellipse((cx-8,cy-4,cx-4,cy),(136,244,251))
        ellipse((cx+4,cy-4,cx+8,cy),(136,244,251))
        rect((cx-10,cy+7,cx+10,cy+11),(3,62,99),2)
    elif kind=="home":
        poly([(cx-16,cy-2),(cx,cy-17),(cx+16,cy-2),(cx+13,cy+1),(cx+13,cy+15),(cx-13,cy+15),(cx-13,cy+1)],(225,241,247),(120,223,250))
        poly([(cx-18,cy-1),(cx,cy-19),(cx+18,cy-1),(cx+15,cy+2),(cx,cy-12),(cx-15,cy+2)],(29,172,244),(202,250,255))
        rect((cx-4,cy+5,cx+5,cy+15),(7,85,139),1)
    return im.resize((w,h),Image.Resampling.LANCZOS)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--preview",type=Path)
    args=p.parse_args()
    dst=args.source/"pictures"
    dst.mkdir(parents=True,exist_ok=True)
    for i,kind in enumerate(KINDS):
        for state in range(2):
            make_sprite(kind,bool(state)).save(dst/f"picture-{24+2*i+state:04d}.png")
    for state in range(2):
        make_sprite("home",bool(state),56,52).save(dst/f"picture-{40+state:04d}.png")
    # Produce a true-size preview from the EXACT picture files used by nxwright,
    # never from a separate concept illustration. Sample states are illustrative.
    if args.preview:
        page=tomllib.loads((args.source/"pages/pageHomeSwtch.page.toml").read_text(encoding="utf-8"))
        components={c["name"]:c for c in page["component"]}
        canvas=Image.new("RGB",(480,320),NAVY)
        enabled={"btAuto","btAutoPH","btLight"}
        names=("btAuto","btAutoORP","btAutoPH","btPHPump",
               "btWinter","btLight","btRobot","btCHLPump")
        for name in names:
            c=components[name]
            which="pic2" if name in enabled else "pic"
            sprite=Image.open(dst/(c[which]+".png")).convert("RGB")
            assert sprite.size==(c["w"],c["h"]),(name,sprite.size)
            canvas.paste(sprite,(c["x"],c["y"]))
        home=components["bHome"]
        sprite=Image.open(dst/(home["pic"]+".png")).convert("RGB")
        assert sprite.size==(home["w"],home["h"])
        canvas.paste(sprite,(home["x"],home["y"]))
        draw=ImageDraw.Draw(canvas)
        font_candidates=("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                         "C:/Windows/Fonts/arialbd.ttf","DejaVuSans.ttf")
        def font(size):
            for path in font_candidates:
                try: return ImageFont.truetype(path,size)
                except OSError: pass
            return ImageFont.load_default()
        # Text is rendered at the 480x320 target resolution for audit,
        # with original Nextion text component rectangles and coordinates.
        for i in range(8):
            c=components[f"t{i}"]
            linebreaks=c["txt"].replace(chr(13)+chr(10), chr(10)).replace(chr(13), "").replace("   ","").replace("  ","").strip()
            cx=c["x"]+c["w"]/2
            draw.multiline_text((cx,c["y"]+c["h"]/2),linebreaks,
                font=font(12),fill=(255,255,255),anchor="mm",
                align="center",spacing=0)
        # HOME caption is an actual Nextion text component, not preview-only artwork.
        caption=components["tHomeCaption"]
        draw.text((caption["x"]+caption["w"]/2,caption["y"]+caption["h"]/2),
                  caption["txt"],font=font(14),fill=(255,255,255),anchor="mm")
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        canvas.save(args.preview,optimize=True)
        print("[NEXTION] Switch preview from actual generated sprite images:",args.preview)
    print("[NEXTION] Generated 18 pageHomeSwtch bitmaps (including Home).")

if __name__=="__main__":
    main()
