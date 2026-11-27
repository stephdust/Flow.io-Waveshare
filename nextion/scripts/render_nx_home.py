#!/usr/bin/env python3
"""Rebuild glossy Nextion Home pictures from nxwright source (480x320 only).

HomeGaugepic atlas (logical picture #3) stays 1035px wide:
pH gauge sprites at y=0..149, ORP sprites at y=150..299, backdrop at y=300..619.
Five tProp background pictures (#20..24) carry a colored rim ONLY.
The actual spinning propeller is a NATIVE Nextion font character driven by
tmAnim.timer and globals.vaStates bit 0; never bake static blades into the TFT.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S=3
NAVY=(4,18,37)
WHITE=(245,251,255)
AQUA=(5,211,247)
FONTS=('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
       '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
       'C:/Windows/Fonts/arialbd.ttf','DejaVuSans-Bold.ttf')


def font(n):
    for candidate in FONTS:
        try: return ImageFont.truetype(candidate,n*S)
        except OSError: pass
    raise RuntimeError('No vector font available for Nextion rendering')


def text(d,value,x,y,n,color=WHITE,anchor='mm'):
    d.text((round(x*S),round(y*S)),str(value),fill=color,font=font(n),anchor=anchor)


def line(d,points,color,width=1):
    d.line([(round(x*S),round(y*S)) for x,y in points],
           fill=color,width=max(1,round(width*S)),joint='curve')


def halo(im,painter,blur=4):
    overlay=Image.new('RGBA',im.size,(0,0,0,0))
    painter(ImageDraw.Draw(overlay))
    return Image.alpha_composite(im,overlay.filter(ImageFilter.GaussianBlur(blur*S)))


def panel(im,coords,r,fill,edge):
    rect=tuple(round(q*S) for q in coords)
    im=halo(im,lambda d:d.rounded_rectangle(rect,radius=r*S,
                                            outline=(*edge,150),width=3*S))
    ImageDraw.Draw(im).rounded_rectangle(rect,radius=r*S,fill=(*fill,255),
                                          outline=(*edge,255),width=S)
    return im


def make_background():
    small=Image.new('RGB',(480,320))
    pixels=small.load()
    for y in range(320):
        for x in range(480):
            glow=math.exp(-((x-250)/190)**2-((y-136)/155)**2)
            pixels[x,y]=(round(3+4*glow),round(14+17*glow),round(34+32*glow))
    image=small.resize((480*S,320*S),Image.Resampling.BICUBIC).convert('RGBA')
    image=panel(image,(5,4,475,58),13,(3,26,52),(7,197,245))
    image=panel(image,(5,262,475,315),13,(3,25,48),(6,202,246))
    d=ImageDraw.Draw(image)
    for x in (154,298,413):line(d,[(x,13),(x,49)],(9,161,217),.7)
    for x in (92,194,294,387):line(d,[(x,270),(x,307)],(7,155,209),.8)
    # Three cyan Flow.io waves / lowercase wordmark.
    for j in range(3):
        path=[(16+t,14.7+7.5*j+1.6*math.sin(t/6)-t*.03) for t in range(42)]
        line(d,path,(10,207,250),3)
    text(d,'flow',61,30,20,anchor='lm')
    text(d,'.io',112,30,20,(11,212,248),anchor='lm')
    # Pool thermometer / water ripples; water temperature stays live text.
    line(d,[(170,13),(170,39)],WHITE,5.4)
    line(d,[(170,16),(170,41)],(248,44,55),3.2)
    d.ellipse((163*S,37*S,177*S,51*S),fill=(252,42,50),outline=WHITE,width=2*S)
    for j in range(2):
        line(d,[(182+k,36+j*7+1.6*math.sin(k/2)) for k in range(15)],(10,218,244),1.6)
    # Nominal markers, WITHOUT colored value capsules.
    for x,value in ((123,'7.5'),(357,'700')):
        text(d,value,x,72,16,(94,249,50))
        d.polygon([(x*S,87*S),((x-6)*S,78*S),((x+6)*S,78*S)],fill=WHITE)
    # Four nav groups: native touch widgets remain active on top.
    for xx in (23,39):
        for yy in (273,288):
            d.rounded_rectangle((xx*S,yy*S,(xx+10)*S,(yy+10)*S),
                                radius=2*S,outline=WHITE,width=2*S)
    d.polygon([(143*S,273*S),(132*S,293*S),(135*S,301*S),
               (143*S,306*S),(152*S,301*S),(155*S,293*S)],fill=(9,214,254))
    d.arc((130*S,300*S,161*S,314*S),180,352,fill=AQUA,width=2*S)
    d.arc((331*S,273*S,362*S,305*S),45,315,fill=(10,223,237),width=3*S)
    d.polygon([(360*S,286*S),(367*S,294*S),(358*S,299*S)],fill=(12,227,240))
    line(d,[(450,276),(433,304),(467,304),(450,276)],WHITE,2)
    line(d,[(450,285),(450,296)],WHITE,2)
    d.ellipse((448*S,298*S,452*S,302*S),fill=WHITE)
    # Time/date/WiFi are rendered by live native widgets, not fake pixels.
    return image.convert('RGB')


def gauge_sprite(bg,kind,active):
    x=20 if kind=='pH' else 253
    image=bg.crop((x*S,89*S,(x+207)*S,239*S)).convert('RGBA')
    colors=((249,35,83),(255,147,29),(255,212,36),
            (105,247,51),(8,217,248))
    ring=tuple(q*S for q in (7,11,200,182))
    image=halo(image,lambda d:[d.arc(ring,180+i*36+2,180+(i+1)*36-2,
                                     fill=(*colors[i],150),width=13*S)
                               for i in range(5)])
    d=ImageDraw.Draw(image)
    for i,c in enumerate(colors):
        start,end=180+i*36+2,180+(i+1)*36-2
        d.arc(ring,start,end,fill=(*c,255),width=12*S)
        d.arc(tuple(q*S for q in (7,8,200,179)),start+3,end-3,
              fill=(*((250,251,255) if i==active else (80,196,219)),255),
              width=(2 if i==active else 1)*S)
    cx,cy=103,103
    for i in range(15):
        a=math.pi+i*math.pi/14
        co,si=math.cos(a),math.sin(a)
        r2=67 if i%3==0 else 71
        line(d,[(cx+co*76,cy+si*76*.89),
                (cx+co*r2,cy+si*r2*.89)],WHITE,1.3 if i%3==0 else .7)
    pill=tuple(q*S for q in (50,60,158,129))
    image=halo(image,lambda d:d.rounded_rectangle(
        pill,radius=25*S,outline=(*AQUA,140),width=4*S),2)
    d=ImageDraw.Draw(image)
    d.rounded_rectangle(pill,radius=25*S,fill=(*NAVY,255),
                        outline=(*AQUA,255),width=S)
    text(d,kind,103,119,12)
    if kind=='pH':
        text(d,'6.8',21,106,11)
        text(d,'8.2',188,106,11)
    else:
        text(d,'600',19,106,10)
        text(d,'800',188,106,10)
    return image.convert('RGB')


def fan_background(bg,index):
    # No blades: tProp.txt rotates through native Propeller_50 glyphs.
    image=bg.crop((207*S,210*S,277*S,280*S)).convert('RGBA')
    color=((141,185,208),(81,236,112),(247,220,51),
           (249,137,29),(241,62,81))[index]
    rect=tuple(q*S for q in (6,6,64,64))
    image=halo(image,lambda d:d.arc(rect,195,520,
                                     fill=(*color,155),width=6*S),3)
    ImageDraw.Draw(image).arc(rect,195,520,fill=(*color,255),width=5*S)
    return image.convert('RGB')


def render(source,preview):
    project=(source/'app.toml').read_text(encoding='utf-8')
    if 'screen = "NX4832K035"' not in project or 'rotation = 90' not in project:
        raise ValueError('only NX4832K035 at 90 degrees is supported')
    pictures=source/'pictures'
    assert (pictures/'picture-0003.png').is_file(), 'expected an editable RGB Home atlas'
    bg=make_background()
    atlas=Image.new('RGB',(1035,620),NAVY)
    for state in range(5):
        for y,kind in ((0,'pH'),(150,'ORP')):
            im=gauge_sprite(bg,kind,state).resize((207,150),Image.Resampling.LANCZOS)
            atlas.paste(im,(state*207,y))
        path=pictures/f'picture-{20+state:04}.png'
        if not path.is_file():raise ValueError('missing animated fan background: '+str(path))
        fan_background(bg,state).resize((70,70),Image.Resampling.LANCZOS).save(path,optimize=True)
    atlas.paste(bg.resize((480,320),Image.Resampling.LANCZOS),(0,300))
    atlas.save(pictures/'picture-0003.png',optimize=True)
    demo=bg.resize((480,320),Image.Resampling.LANCZOS)
    demo.paste(atlas.crop((414,0,621,150)),(20,89))
    demo.paste(atlas.crop((414,150,621,300)),(253,89))
    demo.paste(fan_background(bg,1).resize((70,70),Image.Resampling.LANCZOS),(207,210))
    d=ImageDraw.Draw(demo)
    # Sample rotating glyph drawn ONLY in preview. Real tProp uses native frames.
    for i in range(4):
        a=i*math.pi/2
        x=242+13*math.cos(a);y=245+13*math.sin(a)
        d.ellipse((round(x-8),round(y-7),round(x+8),round(y+7)),fill=WHITE)
    d.ellipse((239,242,245,248),fill=(34,125,203))
    sample_font=ImageFont.truetype(FONTS[0],26)
    d.text((123,184),'7.50',font=sample_font,fill=WHITE,anchor='mm')
    d.text((357,184),'706',font=sample_font,fill=WHITE,anchor='mm')
    d.text((248,32),'22.7°C',font=ImageFont.truetype(FONTS[0],21),
           fill=WHITE,anchor='mm')
    d.text((360,22),'10:47',font=ImageFont.truetype(FONTS[0],20),
           fill=WHITE,anchor='mm')
    d.text((360,42),'27/11/26',font=ImageFont.truetype(FONTS[0],12),
           fill=WHITE,anchor='mm')
    preview.parent.mkdir(parents=True,exist_ok=True)
    demo.save(preview,optimize=True)
    print('Home atlas=1035x620; pH/ORP distinct sprites; native pump rotation unchanged')
    print('Preview SHA256',hashlib.sha256(preview.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--preview',required=True,type=Path)
    options=parser.parse_args()
    render(options.source,options.preview)
