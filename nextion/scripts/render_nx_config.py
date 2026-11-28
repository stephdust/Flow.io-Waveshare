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
    # Small cyan setting gears, behind the dynamic breadcrumb.
    for gx,gy in ((22,16),(40,16)):
        ellipse(d,(gx-6,gy-6,gx+6,gy+6),(86,222,252))
        ellipse(d,(gx-2,gy-2,gx+2,gy+2),NAVY)
        for dx,dy in ((-8,0),(8,0),(0,-8),(0,8)):
            rr(d,(gx+dx-2,gy+dy-2,gx+dx+2,gy+dy+2),1,
               (85,211,247))
    line(d,[(4,31),(476,31)],(22,108,148))
    for i in range(6):
        y=37+38*i
        panel(d,(5,y,475,y+34),9)
        rr(d,(8,y+8,11,y+25),2,(24,199,244))
    line(d,[(2,267),(478,267)],(25,112,151))
    # Compact pagination: 56 pixels between Prev and Next.
    panel(d,(173,279,229,310),7,(6,40,67),(31,108,153),(18,72,108))
    background_image=shrink(im,W,H)
    # Even older ESP32 firmware hides unavailable controls using 'vis 0'.
    # A muted version of each REAL button sprite belongs to the native
    # page background. When a button is enabled, its active sprite overlays
    # this backup. A disabled button is still visible but not clickable.
    for kind,x,width in (("home",0,56),("back",60,56),
                         ("prev",120,50),("next",232,50),
                         ("reboot",291,62),("valid",365,110)):
        off=nav(kind,False,width,52)
        muted=Image.blend(off,Image.new("RGB",off.size,NAVY),0.36)
        background_image.paste(muted,(x,268))
    return background_image

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

def nav(kind,on=False,w=50,h=52):
    """3D button with a small symbol AND a caption baked into its real HMI sprite.

    Keep the house glyph identical to the validated Home artwork: only
    the surrounding panel is reshaped to leave room for a legible label.
    """
    im,d=new(w,h)
    cx,cy=w/2,18
    accent=(65,232,128) if kind=="valid" else (
        (251,104,101) if kind=="reboot" else (51,192,246))
    base=(11,113,26) if kind=="valid" else (
        (158,19,30) if kind=="reboot" else (10,73,137))
    shine=(64,207,80) if kind=="valid" else (
        (230,65,68) if kind=="reboot" else (29,158,225))
    panel(d,(1,1,w-2,h-2),9,base,accent,shine)
    if on:
        rr(d,(3,3,w-4,h-4),7,base,(201,252,255),1)
    def L(points,color,width=3):
        line(d,[(cx+x,cy+y) for x,y in points],color,width)
    def P(points,color):
        poly(d,[(cx+x,cy+y) for x,y in points],color)
    if kind=="home":
        # Unmodified glyph: white walls, cyan roof and dark blue door.
        P([(-13,0),(0,-13),(13,0),(10,3),(10,13),(-10,13),(-10,3)],(235,247,252))
        P([(-15,0),(0,-15),(15,0),(12,3),(0,-9),(-12,3)],(12,172,251))
        rr(d,(cx-3,cy+6,cx+3,cy+13),1,(5,74,112))
    elif kind=="back":
        # Curved return-arrow, unlike Prev/Next single chevrons.
        P([(-15,-4),(-1,-16),(-1,-9),(6,-9),
           (13,-5),(15,1),(15,9),(8,9),(8,2),
           (4,-2),(-1,-2),(-1,5)],(239,251,255))
        L([(-15,-4),(-1,-16)],(86,222,255),1)
    elif kind in ("prev","next"):
        direction=-1 if kind=="prev" else 1
        L([(direction*-8,-11),(direction*4,0),(direction*-8,11)],
          (243,252,255),5)
    elif kind=="valid":
        L([(-13,-1),(-4,8),(13,-11)],(221,255,237),6)
        L([(-12,-2),(-4,7),(12,-12)],(116,252,159),3)
    elif kind=="reboot":
        # The former arc was open at the RIGHT while its power stem was at
        # the TOP. Two aligned arcs deliberately leave the gap at the top.
        # This is an unmistakable white power symbol with a red 3D bezel.
        bezel=B((cx-12,cy-11,cx+12,cy+13))
        d.arc(bezel,315,359,fill=(255,246,242),width=4*S)
        d.arc(bezel,0,225,fill=(255,246,242),width=4*S)
        L([(0,-16),(0,-1)],(255,250,247),4)
    else:
        raise ValueError(kind)
    # Label is part of the actual PNG sprite referenced by the Nextion.
    label={"home":"Home","back":"Back","prev":"Prev",
           "next":"Next","reboot":"Reboot","valid":"Valid"}[kind]
    font=ImageFont.load_default(size=13*S)
    d.text((round(cx*S),round(37*S)),label,font=font,
           fill=(246,253,255),anchor="mt")
    return shrink(im,w,h)


def sample_text(canvas,c,text,size=16,color=(239,248,255)):
    # Text is sample data, clipped to native component bounds like the HMI.
    x,y,w,h=[c[k] for k in ("x","y","w","h")]
    try:
        # Keep accented French labels readable in the actual preview PNG.
        # The Pillow built-in default font substitutes missing glyphs with boxes.
        f=ImageFont.truetype("DejaVuSans.ttf",size)
    except OSError as exc:
        raise RuntimeError(
            "DejaVuSans.ttf is required for French text in the Nextion preview"
        ) from exc
    layer=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    box=d.textbbox((0,0),text,font=f)
    if box[2]-box[0]>w-4 or box[3]-box[1]>h-2:
        raise ValueError(f"caption overflow: {c['name']}: {text!r}")
    # Center numbers within the compact 1/3 capsule; other text is left aligned.
    left=((w-(box[2]-box[0]))/2 if c.get("xcen",0)==1 else 5)-box[0]
    d.text((left,(h-(box[3]-box[1]))/2-box[1]),text,
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
        49:lambda:nav("back",False,56,52),50:lambda:nav("back",True,56,52),
        51:lambda:nav("prev",False,50,52),52:lambda:nav("prev",True,50,52),
        53:lambda:nav("next",False,50,52),54:lambda:nav("next",True,50,52),
        55:lambda:nav("valid",False,110,52),56:lambda:nav("valid",True,110,52),
        57:lambda:nav("reboot",False,62,52),58:lambda:nav("reboot",True,62,52)}
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
            for name in (f"tV{i}",):
                o=c[name]
                image.paste(Image.open(dst/(o["pic"]+".png")).convert("RGB"),(o["x"],o["y"]))
            # Approximate the HMI's 24px Segoe labels, not the old 16px UI.
            # Native font identity is verified separately by the source test.
            sample_text(image,c[f"tL{i}"],labels[i],size=23)
            sample_text(image,c[f"tV{i}"],values[i],size=23,
                        color=(205,250,255))
        sample_text(image,c["tPath"],c["tPath"].get("txt","flow>config"),size=23)
        # The former HOME caption overlapped Back; the house icon is retained.
        sample_text(image,c["nPage"],"1",13)
        sample_text(image,c["t0"],"/",13,(119,172,198))
        sample_text(image,c["nPages"],"3",13)
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        image.save(args.preview,optimize=True)
        print("[NEXTION] Config preview from actual HMI sprites:",args.preview)
    print("[NEXTION] Generated 17 pageCfgMenu pictures (42..58).")

if __name__=="__main__":
    main()
