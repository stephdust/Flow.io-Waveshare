#!/usr/bin/env python3
"""Rebuild glossy Nextion Home pictures from nxwright source (480x320 only).

HomeGaugepic atlas (logical picture #3) is compact: gauges at y=0..299,
flat-background Home at y=300..619, five 70x70 pressure rings plus eleven
42x42 turbine centres packed in a single row at y=620..689, and five 43x38
RSSI icons in a single row at y=690..727.
tmAnim.timer stays at 50ms; the ring redraws only if pressure status changes
while a separate, shared 10-phase core animates on every tick.
The native tProp component/IDs and ESP32 serial protocol remain unchanged.
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
    # Solid panel with no blurred halo: much smaller Nextion bitmap.
    ImageDraw.Draw(im).rounded_rectangle(rect,radius=r*S,fill=(*fill,255),
                                          outline=(*edge,255),width=S)
    return im


def make_background():
    # Uniform dark base reduces encoded RGB565 variation without altering
    # native text, hot spots, gauge/turbine icons or screen coordinates.
    image=Image.new('RGBA',(480*S,320*S),(*NAVY,255))
    image=panel(image,(5,4,475,58),13,(3,26,52),(7,197,245))
    image=panel(image,(5,262,475,315),13,(3,25,48),(6,202,246))
    d=ImageDraw.Draw(image)
    for x in (154,300,413):line(d,[(x,13),(x,48)],(9,161,217),.7)
    for x in (194,294,387):line(d,[(x,270),(x,307)],(7,155,209),.8)
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
    # Two real temperatures share the 154..300px header column:
    # drop = pool water (top), sun/cloud = outdoor air (bottom).
    # Readings remain native text widgets, never baked into the bitmap.
    # Compact icons deliberately leave x=187..296 clear for dynamic text.
    drop=[(171,9),(167,14),(164,19),(163,23),(164,27),(167,29),
          (171,30),(175,28),(178,25),(178,21),(175,15),(171,9)]
    line(d,drop,(188,237,255),1.5)
    line(d,[(166,22),(167,25),(170,27)],(9,207,244),1.4)
    # Partly cloudy outline like the 5"/7" Home pages, simplified for 480x320.
    d.arc((163*S,33*S,171*S,41*S),185,355,fill=(255,216,96),width=2*S)
    for a,b in [((167,30),(167,32)),((160,35),(162,36)),((172,34),(174,33))]:
        line(d,[a,b],(255,216,96),1.1)
    d.arc((160*S,40*S,172*S,53*S),130,280,fill=WHITE,width=1.6*S)
    d.arc((169*S,37*S,181*S,51*S),188,356,fill=WHITE,width=1.6*S)
    line(d,[(162,50),(178,50)],WHITE,1.6)
    # Nominal markers, WITHOUT colored value capsules.
    for x,value in ((123,'7.5'),(357,'700')):
        text(d,value,x,72,16,(94,249,50))
        d.polygon([(x*S,87*S),((x-6)*S,78*S),((x+6)*S,78*S)],fill=WHITE)
    # Footer: four useful actions (grid/config, centre pump/filtration,
    # gear/switches and triangle/alarms). No redundant 'play' button.
    # Grid is centered in the freed left footer section, with a matching
    # transparent b0 hotspot. Icons never render opaque touch rectangles.
    for xx in (88,104):
        for yy in (273,288):
            d.rounded_rectangle((xx*S,yy*S,(xx+10)*S,(yy+10)*S),
                                radius=2*S,outline=WHITE,width=2*S)
    # Home switches / controls. Use a recognizable gear, not the former
    # ambiguous curved arrow. Its hitbox is m0 (x=309..387, y=268..313).
    gear_x,gear_y=349,290
    for spoke in range(8):
        angle=spoke*math.pi/4
        co,si=math.cos(angle),math.sin(angle)
        d.line([(round((gear_x+12*co)*S),round((gear_y+12*si)*S)),
                (round((gear_x+16*co)*S),round((gear_y+16*si)*S))],
               fill=(*WHITE,),width=4*S)
    d.ellipse(((gear_x-12)*S,(gear_y-12)*S,
               (gear_x+12)*S,(gear_y+12)*S),
              outline=(*AQUA,),width=2*S)
    d.ellipse(((gear_x-5)*S,(gear_y-5)*S,
               (gear_x+5)*S,(gear_y+5)*S),
              outline=(*WHITE,),width=2*S)
    line(d,[(450,276),(433,304),(467,304),(450,276)],WHITE,2)
    line(d,[(450,285),(450,296)],WHITE,2)
    d.ellipse((448*S,298*S,452*S,302*S),fill=WHITE)
    # Time, date, water and outdoor-air temperatures stay live widgets. Wi-Fi
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
FAN_RING_ATLAS_Y=620
FAN_CORE_SIZE=42
FAN_CORE_X=FAN_X+(FAN_SIZE-FAN_CORE_SIZE)//2
FAN_CORE_Y=FAN_Y+(FAN_SIZE-FAN_CORE_SIZE)//2
FAN_CORE_ATLAS_X=350
FAN_FRAMES=11


def _cubic(a,b,c,d,steps=12):
    return [((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+3*(1-t)*t*t*c[0]+t**3*d[0],
             (1-t)**3*a[1]+3*(1-t)**2*t*b[1]+3*(1-t)*t*t*c[1]+t**3*d[1])
            for t in (i/steps for i in range(steps+1))]


def _turn(point, theta, centre=FAN_CORE_SIZE/2):
    """Rotate a blade point around the exact 21px centre."""
    u, v = point
    cs, sn = math.cos(theta), math.sin(theta)
    return ((centre + u*cs - v*sn)*S,
            (centre + u*sn + v*cs)*S)


def _blend(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))


def ring_frame(bg,status):
    """Full 360-degree glossy cyan bezel; pressure adds a small accent.

    The earlier split arcs looked like a broken circle. All five PSI
    variants now use the same uninterrupted 70px circular frame.
    The opaque 42px core sits entirely inside the bezel (its corners are
    29.7px from centre, while the bezel starts at radius 31px).
    """
    assert 0 <= status <= 4
    im = bg.crop((FAN_X*S, FAN_Y*S, (FAN_X+FAN_SIZE)*S,
                  (FAN_Y+FAN_SIZE)*S)).convert("RGBA")
    shades = ((120,153,181), (96,239,79), (255,216,73),
              (255,143,54), (255,70,92))
    active = shades[status]

    # Soft outer glow, without any opaque corners in the HMI bitmap.
    glow = Image.new("RGBA", im.size, (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((4*S,4*S,66*S,66*S),
               outline=(0,185,250,115), width=3*S)
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(2*S)))

    d = ImageDraw.Draw(im)
    # Continuous dark recessed basin. The 42px animation sprite uses the
    # same flat inner RGB value, so no central square is visible.
    d.ellipse((2*S,2*S,68*S,68*S),
              fill=(3,17,31,255), outline=(5,77,133,255),width=2*S)
    d.ellipse((3*S,3*S,67*S,67*S),
              outline=(8,207,250,255),width=3*S)
    # Upper-left specular reflection + lower-right depth create a true 3D rim.
    d.arc((4*S,4*S,66*S,66*S),194,325,
          fill=(220,250,255,255),width=2*S)
    d.arc((4*S,4*S,66*S,66*S),15,143,
          fill=(4,89,162,255),width=2*S)
    d.ellipse((7*S,7*S,63*S,63*S),
              outline=(17,114,171,255),width=S)
    # Thin status cue *inside* the full cyan circumference; no more broken
    # or detached pressure arcs.
    d.arc((9*S,9*S,61*S,61*S),224,306,
          fill=(*active,255),width=S)
    return im.convert("RGB")


def blade_frame(frame):
    """Four curved, metallic cyan 3D blades + a reflective raised hub.

    0 = muted stationary OFF, 1..10 = glossy ON rotation phases.
    These eleven pressure-independent 42px frames keep the compact
    1035x728 atlas and 50ms animation, with no extra memory allocation.
    """
    assert 0 <= frame < FAN_FRAMES
    im = Image.new("RGBA", (FAN_CORE_SIZE*S,FAN_CORE_SIZE*S),
                   (3,17,31,255))
    phase = (max(0, frame-1)*math.pi/20) if frame else 0
    is_on = frame != 0

    # Curved asymmetric outline, repeated by a precise quarter-turn:
    # four identical swept blades like the approved dashboard mock-up.
    blade_curves = [
        ((1,-4),(-2,-5),(-7,-8),(-9,-12)),
        ((-9,-12),(-11,-15),(-11,-19),(-6,-19)),
        ((-6,-19),(-1,-20),(5,-18),(7,-14)),
        ((7,-14),(9,-11),(8,-7),(4,-4)),
        ((4,-4),(3,-3),(2,-3),(1,-4)),
    ]
    outline = [point for curve in blade_curves
               for point in _cubic(*curve, steps=9)]
    w, h = im.size

    for blade in range(4):
        angle = phase + blade*math.pi/2
        co, si = math.cos(angle),math.sin(angle)
        coords = [_turn(pt, angle) for pt in outline]

        # A soft offset silhouette provides thickness behind each blade.
        shadow_mask = Image.new("L", (w,h),0)
        sd = ImageDraw.Draw(shadow_mask)
        sd.polygon([(x+0.9*S,y+1.15*S) for x,y in coords],fill=185)
        shadow = Image.new("RGBA", (w,h), (0,4,22,0))
        shadow.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(1.0*S)))
        im = Image.alpha_composite(im,shadow)

        mask = Image.new("L", (w,h),0)
        ImageDraw.Draw(mask).polygon(coords,fill=255)
        # Per-pixel light across the swept surface. Blue shadow at the
        # lower edge rises to a pale cyan ridge on the opposite edge.
        # The gradient follows each rotation rather than rotating a static
        # highlight independently of the shape.
        surface = Image.new("RGB",(w,h))
        px = surface.load()
        cx = cy = FAN_CORE_SIZE/2
        for yy in range(h):
            ry = yy/S-cy
            for xx in range(w):
                rx = xx/S-cx
                local_x = rx*co+ry*si
                local_y = -rx*si+ry*co
                t = (local_x+11)/20
                if t < 0.53:
                    colour = _blend((7,68,146),(2,181,244),t/0.53)
                else:
                    colour = _blend((2,181,244),(194,252,255),
                                    (t-0.53)/0.47)
                # Tip is slightly darker than the lit curved shoulder.
                depth = 0.86 if local_y < -17 else 1.0
                if not is_on:
                    colour = _blend((24,57,79),(94,152,177),t)
                px[xx,yy] = tuple(round(v*depth) for v in colour)
        im.paste(surface,(0,0),mask)

        d = ImageDraw.Draw(im)
        d.line(coords+[coords[0]],fill=(5,113,193,255),width=max(1,S//2))
        if is_on:
            # Fine curved reflective ridge; not a thick white stick.
            shine = [(-6,-13),(-5,-16),(-3,-17),(-1,-17),(2,-15)]
            d.line([_turn(pt,angle) for pt in shine],
                   fill=(208,251,255,215),width=max(1,S//2))

    # Layered central bearing: dark drop shadow, polished steel/cyan rim,
    # recessed blue centre and a small upper-left specular glint.
    d = ImageDraw.Draw(im)
    cx = cy = FAN_CORE_SIZE/2
    d.ellipse(((cx-4+0.8)*S,(cy-4+1.1)*S,
               (cx+4+0.8)*S,(cy+4+1.1)*S),fill=(0,5,28,255))
    d.ellipse(((cx-4.1)*S,(cy-4.1)*S,
               (cx+4.1)*S,(cy+4.1)*S),
              fill=(17,156,214,255),outline=(224,251,255,255),
              width=max(1,S//2))
    d.ellipse(((cx-2.6)*S,(cy-2.6)*S,
               (cx+2.6)*S,(cy+2.6)*S),
              fill=(2,53,128,255))
    d.ellipse(((cx-1.6)*S,(cy-2.0)*S,
               (cx-0.2)*S,(cy-0.5)*S),
              fill=(236,254,255,255))
    return im.convert("RGB")


WIFI_X,WIFI_Y,WIFI_W,WIFI_H=428,11,43,38
WIFI_ATLAS_Y=690
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
    # The widest sprites are the two gauge strips (5 x 207 = 1035 px).
    # All smaller assets are packed horizontally below the background.
    atlas=Image.new('RGB',(1035,WIFI_ATLAS_Y+WIFI_H),NAVY)
    for state in range(5):
        for y,kind in ((0,'pH'),(150,'ORP')):
            im=gauge_sprite(bg,kind,state).resize((207,150),Image.Resampling.LANCZOS)
            atlas.paste(im,(state*207,y))
        ring=ring_frame(bg,state).resize((FAN_SIZE,FAN_SIZE),Image.Resampling.LANCZOS)
        atlas.paste(ring,(state*FAN_SIZE,FAN_RING_ATLAS_Y))
    for frame in range(FAN_FRAMES):
        core=blade_frame(frame).resize((FAN_CORE_SIZE,FAN_CORE_SIZE),Image.Resampling.LANCZOS)
        atlas.paste(core,(FAN_CORE_ATLAS_X+frame*FAN_CORE_SIZE,FAN_RING_ATLAS_Y))
    for level in range(WIFI_LEVELS):
        tile=wifi_frame(bg,level).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS)
        atlas.paste(tile,(level*WIFI_W,WIFI_ATLAS_Y))
    atlas.paste(bg.resize((480,320),Image.Resampling.LANCZOS),(0,300))
    atlas.save(pictures/'picture-0003.png',optimize=True)
    demo=bg.resize((480,320),Image.Resampling.LANCZOS)
    demo.paste(atlas.crop((414,0,621,150)),(20,89))
    demo.paste(atlas.crop((414,150,621,300)),(253,89))
    # Preview uses the exact shaded 3D sprites from the firmware atlas.
    demo.paste(ring_frame(bg,1).resize((70,70),Image.Resampling.LANCZOS),
               (FAN_X,FAN_Y))
    demo.paste(blade_frame(4).resize((42,42),Image.Resampling.LANCZOS),
               (FAN_CORE_X,FAN_CORE_Y))
    demo.paste(wifi_frame(bg,4).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS),
               (WIFI_X,WIFI_Y))
    d=ImageDraw.Draw(demo)
    sample_font=preview_font(26)
    d.text((123,184),'7.50',font=sample_font,fill=WHITE,anchor='mm')
    d.text((357,184),'706',font=sample_font,fill=WHITE,anchor='mm')
    d.text((187,20),'27.3°C',font=preview_font(16),
           fill=WHITE,anchor='lm')
    d.text((187,42),'7.3°C',font=preview_font(16),
           fill=WHITE,anchor='lm')
    d.text((360,22),'10:47',font=preview_font(20),
           fill=WHITE,anchor='mm')
    d.text((360,42),'27/11/26',font=preview_font(12),
           fill=WHITE,anchor='mm')
    preview.parent.mkdir(parents=True,exist_ok=True)
    demo.save(preview,optimize=True)
    print('Home atlas=1035x728: 5 rings + 11 small turbine frames + 5 RSSI tiers')
    print('Preview SHA256',hashlib.sha256(preview.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--preview',required=True,type=Path)
    options=parser.parse_args()
    render(options.source,options.preview)
