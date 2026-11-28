#!/usr/bin/env python3
"""Generate genuine Nextion picture assets (IDs 42..58) and pageCfgMenu PNG.

The PNG uses sample dynamic data, not a screenshot of the HMI interpreter.
Every decorative button in the preview is a bitmap actually used by Nextion.
"""
from pathlib import Path
import argparse
import tomllib
from PIL import Image, ImageDraw, ImageFont

NAVY=(4,18,37)
W,H,S=480,320,3

def B(box):
    return tuple(round(v*S) for v in box)

def rr(d,box,r,fill,outline=None,width=1):
    d.rounded_rectangle(B(box),radius=round(r*S),fill=fill,
                        outline=outline,width=max(1,round(width*S)))

def line(d,points,color,width=1):
    d.line([(round(x*S),round(y*S)) for x,y in points],fill=color,
           width=max(1,round(width*S)),joint="curve")

def ellipse(d,box,fill,outline=None,width=1):
    d.ellipse(B(box),fill=fill,outline=outline,width=max(1,round(width*S)))

def poly(d,points,fill):
    d.polygon([(round(x*S),round(y*S)) for x,y in points],fill=fill)

def panel(d,box,r=8,base=(9,39,63),accent=(21,107,148),shine=(26,77,105)):
    x1,y1,x2,y2=box
    rr(d,(x1+1,y1+3,x2+1,y2+3),r,(0,7,17))
    rr(d,box,r,(9,33,53),accent)
    rr(d,(x1+2,y1+2,x2-2,y2-2),r-2,base)
    rr(d,(x1+3,y1+2,x2-3,y1+8),r-3,shine)
    line(d,[(x1+10,y2-3),(x2-10,y2-3)],(2,23,39))

def new(w,h):
    im=Image.new("RGB",(w*S,h*S),NAVY)
    return im,ImageDraw.Draw(im)

def shrink(im,w,h):
    return im.resize((w,h),Image.Resampling.LANCZOS)

def background():
    im,d=new(W,H)
    panel(d,(5,3,475,29),7,(7,35,56),(18,80,113),(17,63,90))
    line(d,[(4,31),(476,31)],(22,108,148))
    for i in range(6):
        y=37+38*i
        panel(d,(5,y,475,y+34),9)
        rr(d,(8,y+8,11,y+25),2,(24,199,244))
    line(d,[(2,267),(478,267)],(25,112,151))
    # Compact pagination frame: 62 px instead of 84.
    panel(d,(184,279,246,308),7,(6,40,67),(31,108,153),(18,72,108))
    return shrink(im,W,H)

def field(on=False):
    # Use the same dimensions as the native HMI value components.
    im,d=new(185,30)
    panel(d,(0,0,184,29),7,(11,83,104) if on else (12,54,78),
          (47,222,227) if on else (31,134,170),
          (18,115,137) if on else (22,86,121))
    return shrink(im,185,30)

def chevron(on=False):
    im,d=new(41,34)
    panel(d,(0,0,40,33),8,(13,91,104) if on else (13,69,96),
          (71,235,227) if on else (17,155,203),
          (38,127,144) if on else (33,99,125))
    poly(d,[(14,10),(24,17),(14,24),(19,24),(29,17),(19,10)],(205,255,255))
    return shrink(im,41,34)

def nav(kind,on=False,w=50,h=50):
    im,d=new(w,h)
    cx,cy=w/2,h/2
    r=min(w,h)/2-3
    accent=(255,100,75) if kind=="reboot" else (
        (57,242,166) if kind=="valid" else (42,201,245))
    rim=accent if on else (
        (191,75,66) if kind=="reboot" else (
        (38,196,150) if kind=="valid" else (65,123,169)))
    ellipse(d,(cx-r+1,cy-r+3,cx+r+1,cy+r+3),(0,7,21))
    ellipse(d,(cx-r,cy-r,cx+r,cy+r),(4,30,61),rim,2)
    ellipse(d,(cx-r+3,cy-r+3,cx+r-3,cy+r-3),
            (17,73,90) if on else (22,52,83))
    d.arc(B((cx-r+6,cy-r+6,cx+r-6,cy+r-6)),
          192,337,fill=(146,240,255),width=2*S)
    def L(points,color,width=3):
        line(d,[(cx+x,cy+y) for x,y in points],color,width)
    def P(points,color):
        poly(d,[(cx+x,cy+y) for x,y in points],color)
    if kind=="home":
        P([(-13,0),(0,-13),(13,0),(10,3),(10,13),(-10,13),(-10,3)],(235,247,252))
        P([(-15,0),(0,-15),(15,0),(12,3),(0,-9),(-12,3)],(12,172,251))
        rr(d,(cx-3,cy+6,cx+3,cy+13),1,(5,74,112))
    elif kind=="back":
        # Curved return-arrow glyph, distinct from page navigation arrows.
        P([(-15,-2),(-2,-14),(-2,-7),(8,-7),(13,-3),(13,8),
           (7,8),(7,0),(-2,0),(-2,8)],(228,250,255))
        L([(-15,-2),(-2,-14)],(36,188,245),2)
    elif kind in ("prev","next"):
        sign=-1 if kind=="prev" else 1
        P([(sign*-8,-13),(sign*6,0),(sign*-8,13),
           (sign*-3,13),(sign*11,0),(sign*-3,-13)],(219,249,255))
    elif kind=="valid":
        L([(-13,0),(-4,10),(13,-10)],(190,255,224),6)
        L([(-12,-1),(-4,9),(12,-11)],(41,237,147),3)
    elif kind=="reboot":
        d.arc(B((cx-13,cy-11,cx+13,cy+15)),47,315,
              fill=(255,175,153) if on else (250,119,107),width=4*S)
        L([(0,-17),(0,-2)],(255,235,218),4)
    else:
        raise ValueError(kind)
    return shrink(im,w,h)

def sample_text(canvas,c,text,size=16,color=(239,248,255)):
    # Text is sample data, clipped to native component bounds like the HMI.
    x,y,w,h=[c[k] for k in ("x","y","w","h")]
    try:
        f=ImageFont.truetype("DejaVuSans.ttf",size)
    except OSError:
        f=ImageFont.load_default(size=size)
    layer=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    box=d.textbbox((0,0),text,font=f)
    if box[2]-box[0]>w-4 or box[3]-box[1]>h-2:
        raise ValueError(f"caption overflow: {c['name']}: {text!r}")
    d.text((5-box[0],(h-(box[3]-box[1]))/2-box[1]),text,
           font=f,fill=(*color,255))
    canvas.paste(layer,(x,y),layer)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--preview",type=Path)
    args=parser.parse_args()
    dst=args.source/"pictures"
    dst.mkdir(parents=True,exist_ok=True)
    assets={
        42:background,43:lambda:field(False),44:lambda:field(True),
        45:lambda:chevron(False),46:lambda:chevron(True),
        47:lambda:nav("home",False,56,52),48:lambda:nav("home",True,56,52),
        49:lambda:nav("back",False),50:lambda:nav("back",True),
        51:lambda:nav("prev",False),52:lambda:nav("prev",True),
        53:lambda:nav("next",False),54:lambda:nav("next",True),
        55:lambda:nav("valid",False),56:lambda:nav("valid",True),
        57:lambda:nav("reboot",False),58:lambda:nav("reboot",True)}
    for number,render in assets.items():
        render().save(dst/f"picture-{number:04d}.png")
    if args.preview:
        page=tomllib.loads((args.source/"pages/pageCfgMenu.page.toml").read_text(encoding="utf-8"))
        c={x["name"]:x for x in page["component"]}
        image=Image.open(dst/"picture-0042.png").convert("RGB")
        for name in ("bHome","bBack","bPrev","bNext","bValid","bReboot"):
            o=c[name]
            image.paste(Image.open(dst/(o["pic"]+".png")).convert("RGB"),(o["x"],o["y"]))
        labels=("Paramètre 1","Paramètre 2","Paramètre 3","Paramètre 4","Paramètre 5","Paramètre 6")
        values=("Valeur","7,20","Activé","Auto","700 mV","Réglage")
        for i in range(6):
            for name in (f"tV{i}",f"bR{i}"):
                o=c[name]
                image.paste(Image.open(dst/(o["pic"]+".png")).convert("RGB"),(o["x"],o["y"]))
            sample_text(image,c[f"tL{i}"],labels[i])
            sample_text(image,c[f"tV{i}"],values[i],color=(205,250,255))
        sample_text(image,c["tPath"],c["tPath"].get("txt","flow>config"))
        # The former HOME caption overlapped Back; the house icon is retained.
        sample_text(image,c["nPage"],"1",16)
        sample_text(image,c["t0"],"/",16,(119,172,198))
        sample_text(image,c["nPages"],"3",16)
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        image.save(args.preview,optimize=True)
        print("[NEXTION] Config preview from actual HMI sprites:",args.preview)
    print("[NEXTION] Generated 17 pageCfgMenu pictures (42..58).")

if __name__=="__main__":
    main()
