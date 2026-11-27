#!/usr/bin/env python3
"""Rebuild glossy Nextion Home pictures from nxwright source (480x320 only).

HomeGaugepic atlas (logical picture #3) stays 1035px wide:
pH gauge sprites at y=0..149, ORP sprites at y=150..299, backdrop at y=300..619.
The atlas additionally contains 5 pressure-status rows of 11 turbine frames
(y=620..969). Four asymmetric cyan blades rotate around the exact 35px center.
tmAnim.timer remains 50ms and gates frames on globals.vaStates bit 0:
filtration OFF -> frame 0, ON -> animation frames 1..10.
The native tProp component/IDs are retained but hidden; no ESP32 change.
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


def preview_font(n):
    # Preview is rendered at 480x320, not at the supersampled 3x scale.
    # Use the same portable font choices as the production atlas renderer.
    for candidate in FONTS:
        try: return ImageFont.truetype(candidate,n)
        except OSError: pass
    raise RuntimeError('No vector font available for Nextion preview')


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
    for x in (154,300,413):line(d,[(x,13),(x,48)],(9,161,217),.7)
    for x in (92,194,294,387):line(d,[(x,270),(x,307)],(7,155,209),.8)
    # Exact three-wave emblem from the repository's existing Flow.io logo.
    # Crop the wave-only half: keep the original contours (not three fake lines).
    logo_path=Path(__file__).resolve().parents[2]/'data/webinterface/logo-flowio.png'
    wave_source=Image.open(logo_path).convert('RGBA')
    if wave_source.width<140 or wave_source.height<40:
        raise ValueError('unexpected official Flow.io wordmark size')
    wave=wave_source.crop((0,0,int(wave_source.width*.42),wave_source.height))
    bbox=wave.getbbox()
    if not bbox:
        raise ValueError('official Flow.io waves are empty')
    wave=wave.crop(bbox)
    wave.thumbnail((57*S,33*S),Image.Resampling.LANCZOS)
    image.paste(wave,(8*S,14*S+((33*S-wave.height)//2)),wave)
    d=ImageDraw.Draw(image)
    text(d,'flow',65,31,20,anchor='lm')
    text(d,'.io',115,31,20,(11,212,248),anchor='lm')
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
    # Time, date, and water temperature remain live native widgets. Wi-Fi
    # signal tiers are drawn dynamically from atlas frames (RSSI from ESP32).
    return image.convert('RGB')


def gauge_sprite(bg,kind,active):
    x=20 if kind=='pH' else 253
    image=bg.crop((x*S,89*S,(x+207)*S,239*S)).convert('RGBA')
    # Create a smooth dark center with an exactly solid NAVY patch behind
    # the live Nextion text backgrounds; no rounded capsule or white outline.
    shade=Image.new('RGBA',image.size,(*NAVY,255))
    mask=Image.new('L',image.size,0)
    md=ImageDraw.Draw(mask)
    md.ellipse((27*S,30*S,179*S,163*S),fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(11*S))
    image=Image.composite(shade,image,mask)
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
    # No capsule around the live values.  The 72x40 Nextion text boxes use
    # NAVY bco, so blend the gauge center into that exact solid shade
    # (softened toward the ring), with no visible rectangular frame.
    # This preserves dynamic pH/ORP text on the real device.
    text(d,kind,103,135,13)
    # Range endpoints sit above the central turbine (which overlaps y=210..280).
    if kind=='pH':
        text(d,'6.8',21,109,11)
        text(d,'8.2',188,109,11)
    else:
        text(d,'600',19,109,10)
        text(d,'800',188,109,10)
    return image.convert('RGB')


FAN_X,FAN_Y,FAN_SIZE=207,210,70
FAN_ATLAS_Y=620
FAN_FRAMES=11


def _cubic(a,b,c,d,steps=12):
    return [((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+3*(1-t)*t*t*c[0]+t**3*d[0],
             (1-t)**3*a[1]+3*(1-t)**2*t*b[1]+3*(1-t)*t*t*c[1]+t**3*d[1])
            for t in (i/steps for i in range(steps+1))]


def fan_frame(bg,status,frame):
    """70x70 high-contrast turbine, perfectly centered at (35,35).

    There are 11 frames: 0 is the stationary OFF glyph, 1..10 are active
    rotational phases covering 90 degrees (4-fold symmetry), avoiding jumps.
    Pressure condition remains the same 0..4, independently of ON/OFF.
    """
    assert 0<=status<=4 and 0<=frame<FAN_FRAMES
    im=bg.crop((FAN_X*S,FAN_Y*S,(FAN_X+FAN_SIZE)*S,
                (FAN_Y+FAN_SIZE)*S)).convert('RGBA')
    colors=((152,176,195),(107,248,44),(246,216,40),
            (248,146,30),(245,71,81))
    active=colors[status]
    rect=(3*S,3*S,67*S,67*S)
    im=halo(im,lambda d:d.ellipse(rect,outline=(*AQUA,150),width=3*S),3)
    d=ImageDraw.Draw(im)
    d.ellipse(rect,fill=(4,24,44,255),outline=(*AQUA,255),width=1*S)
    d.ellipse((6*S,6*S,64*S,64*S),
              fill=(3,17,31,255),outline=(111,158,188,255),width=S)
    # Continuous status ring around the spinner. Green/yellow/orange/red
    # follows the same pressure severity as the old image 20..24.
    d.arc((5*S,5*S,65*S,65*S),5,170,
          fill=(185,205,222,255),width=4*S)
    d.arc((5*S,5*S,65*S,65*S),187,338,
          fill=(*active,255),width=4*S)
    curves=[
      ((-3,-7),(-8,-9),(-18,-23),(-8,-26)),
      ((-8,-26),(-5,-30),(10,-29),(13,-25)),
      ((13,-25),(16,-20),(13,-17),(9,-13)),
      ((9,-13),(7,-11),(6,-7),(-3,-7)),
    ]
    # Frame 0 is held when filtration is off. Active phases 1..10 run
    # continuously at 50ms per frame with a seamless 4-blade turn.
    phase=(max(0,frame-1)*math.pi/20) if frame else 0
    for blade in range(4):
        angle=phase+blade*math.pi/2
        co,si=math.cos(angle),math.sin(angle)
        outline=[pt for c in curves for pt in _cubic(*c)]
        # Thin, airy turbine: 28% smaller blades, same exact center.
        coords=[((35+.72*(u*co-v*si))*S,(35+.72*(u*si+v*co))*S)
                for u,v in outline]
        d.polygon(coords,fill=(23,195,244,255))
        d.line(coords+[coords[0]],fill=(228,252,255,255),width=S)
        highlights=[(-6,-21),(1,-26),(8,-25)]
        d.line([((35+.72*(u*co-v*si))*S,(35+.72*(u*si+v*co))*S)
                for u,v in highlights],
               fill=(144,235,255,255),width=S)
    d.ellipse((32*S,32*S,38*S,38*S),
              fill=(6,74,128,255),outline=(*WHITE,255),width=S)
    return im.convert('RGB')



WIFI_X,WIFI_Y,WIFI_W,WIFI_H=428,11,43,38
WIFI_ATLAS_Y=970
WIFI_LEVELS=5


def wifi_frame(bg,level):
    """Live RSSI tier frames: 0=offline, 1=red, 2=amber, 3=cyan, 4=green.

    Outer arcs are additive: higher levels illuminate more segments,
    with one consistent color per newly activated arc. No simulated RSSI.
    """
    assert 0<=level<5
    image=bg.crop((WIFI_X*S,WIFI_Y*S,(WIFI_X+WIFI_W)*S,
                   (WIFI_Y+WIFI_H)*S)).convert('RGBA')
    colors=((255,80,88),(255,197,38),(9,218,250),(111,243,40))
    inactive=(64,93,119)
    d=ImageDraw.Draw(image)
    cx,cy=21.5,31
    for ring in range(1,4):
        radius=6+ring*5.7
        box=tuple(round(q*S) for q in
                  (cx-radius,cy-radius,cx+radius,cy+radius))
        color=colors[ring] if level>=ring+1 else inactive
        d.arc(box,205,335,fill=(*color,255),width=3*S)
    # The central indicator follows the *current* RSSI tier, so a strong
    # connection has a green dot (not a misleading red one).
    dot=colors[level-1] if level>=1 else inactive
    d.ellipse(((cx-3)*S,(cy-3)*S,(cx+3)*S,(cy+3)*S),fill=(*dot,255))
    if level>=1:
        image=halo(image,lambda od: od.ellipse(
            ((cx-2)*S,(cy-2)*S,(cx+2)*S,(cy+2)*S),
            fill=(*colors[level-1],95)),1)
    return image.convert('RGB')


def render(source,preview):
    project=(source/'app.toml').read_text(encoding='utf-8')
    if 'screen = "NX4832K035"' not in project or 'rotation = 90' not in project:
        raise ValueError('only NX4832K035 at 90 degrees is supported')
    pictures=source/'pictures'
    assert (pictures/'picture-0003.png').is_file(), 'expected an editable RGB Home atlas'
    bg=make_background()
    atlas=Image.new('RGB',(1035,WIFI_ATLAS_Y+WIFI_LEVELS*WIFI_H),NAVY)
    for state in range(5):
        for y,kind in ((0,'pH'),(150,'ORP')):
            im=gauge_sprite(bg,kind,state).resize((207,150),Image.Resampling.LANCZOS)
            atlas.paste(im,(state*207,y))
        for frame in range(FAN_FRAMES):
            turbine=fan_frame(bg,state,frame)
            turbine=turbine.resize((FAN_SIZE,FAN_SIZE),Image.Resampling.LANCZOS)
            atlas.paste(turbine,(frame*FAN_SIZE,FAN_ATLAS_Y+state*FAN_SIZE))
    for level in range(WIFI_LEVELS):
        tile=wifi_frame(bg,level).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS)
        atlas.paste(tile,(0,WIFI_ATLAS_Y+level*WIFI_H))
    atlas.paste(bg.resize((480,320),Image.Resampling.LANCZOS),(0,300))
    atlas.save(pictures/'picture-0003.png',optimize=True)
    demo=bg.resize((480,320),Image.Resampling.LANCZOS)
    demo.paste(atlas.crop((414,0,621,150)),(20,89))
    demo.paste(atlas.crop((414,150,621,300)),(253,89))
    # Preview frame is the same real turbine bitmap used by the Nextion timer.
    demo.paste(fan_frame(bg,1,4).resize((70,70),Image.Resampling.LANCZOS),
               (FAN_X,FAN_Y))
    demo.paste(wifi_frame(bg,4).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS),
               (WIFI_X,WIFI_Y))
    d=ImageDraw.Draw(demo)
    sample_font=preview_font(26)
    d.text((123,184),'7.50',font=sample_font,fill=WHITE,anchor='mm')
    d.text((357,184),'706',font=sample_font,fill=WHITE,anchor='mm')
    d.text((248,32),'22.7°C',font=preview_font(21),
           fill=WHITE,anchor='mm')
    d.text((360,22),'10:47',font=preview_font(20),
           fill=WHITE,anchor='mm')
    d.text((360,42),'27/11/26',font=preview_font(12),
           fill=WHITE,anchor='mm')
    preview.parent.mkdir(parents=True,exist_ok=True)
    demo.save(preview,optimize=True)
    print('Home atlas=1035x1160: 5x11 turbine frames + 5 RSSI icon levels')
    print('Preview SHA256',hashlib.sha256(preview.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--preview',required=True,type=Path)
    options=parser.parse_args()
    render(options.source,options.preview)
