#!/usr/bin/env python3
"""Rebuild glossy Nextion Home pictures from nxwright source (480x320 only).

HomeGaugepic atlas (logical picture #3) is compact: ONE 207x150 pH dial at
(0,0) and ONE ORP dial at (207,0), a 480x320 flat-background Home at y=150,
five 70x70 pressure rings plus eleven 42x42 shared turbine phases at y=470,
and five 43x38 RSSI icons at y=540. Atlas size: 812x578 (not 1035x728).
The needles remain dynamic Nextion draw commands, never baked into the dial.
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
    # Entire page uses one uniform navy background. Both the header and
    # footer have NO panels, borders, separators or contrast patches.
    # The only cyan lines belong to the actual icons and circular pump.
    image=Image.new('RGBA',(480*S,320*S),(*NAVY,255))
    d=ImageDraw.Draw(image)
    # Top fields are freely spaced without their previous frame/dividers.
    # Footer controls remain invisible Nextion touch targets with floating icons.
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
    # Tighten wordmark to the official waves, while staying left of x=154.
    text(d,'flow',51,31,20,anchor='lm')
    text(d,'.io',101,31,20,(11,212,248),anchor='lm')
    # Water temperature: sharp small blue droplet with a RED thermometer.
    # No Gaussian halo and no thick overlapping white contours: crisp at
    # the actual 480x320 resolution and after RGB565 conversion.
    # Draw on a transparent layer so the two icons can be shifted as a
    # matched pair without moving the logo or leaving artifacts behind.
    weather_icons=Image.new('RGBA',(480*S,320*S),(0,0,0,0))
    d=ImageDraw.Draw(weather_icons)
    water_drop=[
        (171,6),(174,10),(178,16),(180,20),(180,23),
        (177,27),(173,29),(168,29),(164,27),(162,23),
        (162,20),(165,14)
    ]
    d.polygon([(x*S,y*S) for x,y in water_drop],
              fill=(3,48,103,255))
    d.line([(x*S,y*S) for x,y in water_drop+[water_drop[0]]],
           fill=(39,203,251,255),width=S,joint='curve')
    # White glass tube, red mercury column and a distinct red bulb.
    d.rounded_rectangle((169*S,12*S,173*S,24*S),
                        radius=2*S,fill=(233,251,255,255))
    d.rounded_rectangle((170*S,15*S,172*S,25*S),
                        radius=S,fill=(242,48,62,255))
    d.ellipse((167*S,21*S,175*S,29*S),
              fill=(230,249,255,255))
    d.ellipse((169*S,23*S,173*S,27*S),
              fill=(248,48,60,255))
    d.ellipse((170*S,23*S,171*S,24*S),
              fill=(255,129,111,255))

    # Sun behind the cloud: genuine cloud silhouette, not two tiny
    # disconnected curves that looked like a malformed symbol on hardware.
    sun=(175,39)
    d.ellipse(((sun[0]-5)*S,(sun[1]-5)*S,
               (sun[0]+5)*S,(sun[1]+5)*S),
              fill=(255,202,36,255),outline=(255,238,131,255),width=S)
    for angle in range(0,360,45):
        theta=math.radians(angle)
        d.line([(round((sun[0]+7*math.cos(theta))*S),
                 round((sun[1]+7*math.sin(theta))*S)),
                (round((sun[0]+9*math.cos(theta))*S),
                 round((sun[1]+9*math.sin(theta))*S))],
               fill=(255,220,80,255),width=S)
    # Opaque navy cloud covers only the lower left of the sun.
    cloud=(3,26,52,255)
    d.ellipse((159*S,44*S,173*S,53*S),fill=cloud)
    d.ellipse((165*S,40*S,178*S,53*S),fill=cloud)
    d.ellipse((171*S,45*S,183*S,53*S),fill=cloud)
    d.line([(162*S,49*S),(163*S,46*S),(167*S,44*S),
            (169*S,43*S),(172*S,43*S),(175*S,46*S),
            (178*S,46*S),(181*S,49*S),(180*S,52*S),
            (162*S,52*S),(160*S,50*S),(162*S,49*S)],
           fill=(232,250,255,255),width=2*S,joint='curve')
    # Group both temperature icons on the same x=194 vertical axis:
    # both icons +23 px. The right edge of each icon is
    # <=205px, just BEFORE the native text widgets starting at x=207.
    # This prevents Nextion text refresh from painting over the icons.
    image.alpha_composite(
        weather_icons.crop((159*S,5*S,184*S,30*S)),(182*S,5*S))
    image.alpha_composite(
        weather_icons.crop((159*S,30*S,184*S,55*S)),(182*S,30*S))
    d=ImageDraw.Draw(image)
    # No static setpoint values/arrows: current pH and ORP are shown by
    # their live readings and gauge indicators, never by fixed annotations.
    # Exactly three independent 3D colour icons, floating on flat navy.
    # Centres: config=123 (directly below pH); equipment=346; alarm=440.
    # Keep >50px clear space from pump rim to gear and gear to alarm.
    # The pump stays fixed at x=240, regardless of footer geometry.
    # Each small icon has its own dark bevel, colour body and highlight;
    # absolutely no surrounding frame, panel or dividing line.

    # 1. CONFIGURATION — four polished cyan/blue glass tiles.
    grid_cx,grid_cy=123,290
    for xx in (108,124):
        for yy in (275,291):
            d.rounded_rectangle(((xx+1)*S,(yy+3)*S,(xx+14)*S,(yy+16)*S),
                                radius=3*S,fill=(1,35,74,255))
            d.rounded_rectangle((xx*S,yy*S,(xx+13)*S,(yy+13)*S),
                                radius=3*S,fill=(7,100,172,255),
                                outline=(46,222,252,255),width=2*S)
            d.rounded_rectangle(((xx+2)*S,(yy+2)*S,(xx+11)*S,(yy+6)*S),
                                radius=2*S,fill=(90,234,255,255))
            d.line([((xx+3)*S,(yy+11)*S),((xx+10)*S,(yy+11)*S)],
                   fill=(3,62,132,255),width=S)
    # Highlight on one tile is a specular reflection, not a notification.
    d.ellipse((111*S,277*S,114*S,280*S),fill=(234,255,255,255))

    # 2. EQUIPMENT — 10 machined teeth, jade/teal face, metallic gold hub.
    gear_x,gear_y=346,290
    gear_points=[]
    for tooth in range(10):
        for angle_offset,radius in ((-.40,13),(-.28,18),(.28,18),(.40,13)):
            theta=2*math.pi*(tooth+angle_offset)/10-math.pi/2
            gear_points.append((round((gear_x+radius*math.cos(theta))*S),
                                round((gear_y+radius*math.sin(theta))*S)))
    d.polygon([(x+S,y+2*S) for x,y in gear_points],
              fill=(1,46,54,255))
    d.polygon(gear_points,fill=(4,134,132,255))
    d.line(gear_points+[gear_points[0]],fill=(117,255,225,255),
           width=2*S,joint='curve')
    d.arc(((gear_x-12)*S,(gear_y-12)*S,(gear_x+12)*S,(gear_y+12)*S),
          196,336,fill=(213,255,238,255),width=2*S)
    d.ellipse(((gear_x-9)*S,(gear_y-9)*S,
               (gear_x+9)*S,(gear_y+9)*S),
              fill=(3,36,64,255),outline=(35,224,194,255),width=2*S)
    d.ellipse(((gear_x-5)*S,(gear_y-5)*S,
               (gear_x+5)*S,(gear_y+5)*S),
              fill=(237,190,69,255),outline=(255,241,172,255),width=S)
    d.ellipse(((gear_x-2)*S,(gear_y-3)*S,
               (gear_x+1)*S,(gear_y)*S),fill=(255,254,233,255))

    # 3. ALARMS — amber/bronze faceted triangle, ruby accent, light glyph.
    alarm_x,alarm_y=440,290
    alert_pts=[(alarm_x,271),(alarm_x-20,306),(alarm_x+20,306)]
    d.polygon([((x+1)*S,(y+2)*S) for x,y in alert_pts],
              fill=(63,23,19,255))
    d.polygon([(x*S,y*S) for x,y in alert_pts],
              fill=(129,49,26,255))
    d.line([(x*S,y*S) for x,y in alert_pts+[alert_pts[0]]],
           fill=(255,193,53,255),width=3*S,joint='curve')
    # A thin upper facet catches light without a large glow/halo.
    line(d,[(alarm_x,275),(alarm_x-17,304)],(255,244,156),1)
    line(d,[(alarm_x-15,305),(alarm_x+15,305)],(248,95,54),1)
    d.rounded_rectangle(((alarm_x-2)*S,282*S,
                         (alarm_x+2)*S,295*S),radius=2*S,
                        fill=(255,251,231,255))
    d.ellipse(((alarm_x-3)*S,298*S,
               (alarm_x+3)*S,304*S),fill=(255,250,231,255))
    d.ellipse(((alarm_x-1)*S,299*S,
               alarm_x*S,300*S),fill=(255,255,255,255))
    # Time, date, water and outdoor-air temperatures stay live widgets. Wi-Fi
    # signal tiers are drawn dynamically from atlas frames (RSSI from ESP32).
    return image.convert('RGB')


def _shade(rgb, intensity):
    """3D illumination confined to a dial stroke, not the flat navy base."""
    return tuple(max(0,min(255,round(value*intensity))) for value in rgb)


def gauge_sprite(kind):
    """Five-colour 3D semicircle, without ANY gradient in the background.

    Each frame deliberately starts from the same exact solid NAVY. Shading
    affects only arc/scale strokes, preventing the visible rectangular patches
    the earlier blurred gauge background created on the real Nextion.
    """
    assert kind in ('pH','ORP')
    image=Image.new('RGB',(207*S,150*S),NAVY)
    d=ImageDraw.Draw(image)
    # Original reference palette, symmetrical around the GOOD setpoint:
    # red / yellow / green / yellow / red (not an alert at the centre).
    colors=((254,39,86),(255,212,32),(98,252,55),
            (255,212,32),(254,39,86))
    ring=tuple(q*S for q in (7,11,200,182))
    # Thin dark outer lip and blue inner recess: polished/raised 3D dial.
    d.arc(tuple(q*S for q in (5,9,202,184)),180,360,
          fill=(6,69,137),width=17*S)
    d.arc(tuple(q*S for q in (6,10,201,183)),180,360,
          fill=(8,133,203),width=2*S)
    for i,c in enumerate(colors):
        start,end=180+i*36+.5,180+(i+1)*36-.5
        # The shadow, coloured body and specular highlight are contained
        # entirely in the arc's 15px radial band. Background stays NAVY.
        d.arc(ring,start,end,fill=_shade(c,.46),width=15*S)
        d.arc(tuple(q*S for q in (10,13,197,179)),
              start,end,fill=c,width=11*S)
        d.arc(tuple(q*S for q in (12,15,195,177)),
              start+1,end-1,fill=_shade(c,1.30),width=3*S)
        # A fine inside rim provides depth between the arc and the dial.
        d.arc(tuple(q*S for q in (19,24,188,169)),
              start+1,end-1,fill=_shade(c,.52),width=S)
    # Fine raised white scale ticks (same layout, subtler blue shadow).
    cx,cy=103,103
    for i in range(15):
        a=math.pi+i*math.pi/14
        co,si=math.cos(a),math.sin(a)
        r2=67 if i%3==0 else 71
        line(d,[(cx+co*76+1,cy+si*76*.89+1),
                (cx+co*r2+1,cy+si*r2*.89+1)],(5,102,171),
             1.8 if i%3==0 else 1)
        line(d,[(cx+co*76,cy+si*76*.89),
                (cx+co*r2,cy+si*r2*.89)],WHITE,
             1.3 if i%3==0 else .7)
    # Live measurements are native Nextion components; the needle is drawn
    # by pageHome.nx only after the current gauge frame is blitted.
    text(d,kind,103,135,20)
    if kind=='pH':
        text(d,'6.8',21,116,16)
        text(d,'8.2',187,116,16)
    else:
        text(d,'600',21,116,15)
        text(d,'800',187,116,15)
    return image


def gauge_needle_points(origin_x,index):
    """Same 21-position geometry as pageHome.nx, 0..280 => 0..20."""
    theta=math.pi+index*math.pi/20
    cx,cy=origin_x+103,159
    tx=round(cx+81*math.cos(theta))
    ty=round(cy+59*math.sin(theta))
    nx,ny=-math.sin(theta),math.cos(theta)
    return cx,cy,tx,ty,nx,ny


def draw_preview_gauge_cursor(image, origin_x, percent):
    """Show the *long* 3D measurement needle and bearing, never a rim tick."""
    idx=max(0,min(20,(int(percent)+7)//14))
    cx,cy,tx,ty,nx,ny=gauge_needle_points(origin_x,idx)
    d=ImageDraw.Draw(image)
    d.line((cx+2,cy+2,tx+1,ty+1),fill=(2,41,97),width=4)
    d.line((round(cx-2*nx),round(cy-2*ny),
            round(tx-nx),round(ty-ny)),fill=(1,127,202),width=2)
    d.line((round(cx+2*nx),round(cy+2*ny),
            round(tx+nx),round(ty+ny)),fill=AQUA,width=2)
    d.line((cx,cy,tx,ty),fill=(234,253,255),width=1)
    d.ellipse((cx-6,cy-6,cx+6,cy+6),fill=(2,30,73))
    d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=AQUA)
    d.ellipse((cx-3,cy-3,cx+3,cy+3),fill=(5,81,151))
    d.ellipse((cx-2,cy-3,cx,cy-1),fill=WHITE)


FAN_X,FAN_Y,FAN_SIZE=205,239,70
FAN_RING_ATLAS_Y=470
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
    812x578 atlas and 50ms animation, with no extra memory allocation.
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


WIFI_X,WIFI_Y,WIFI_W,WIFI_H=423,11,43,38
WIFI_ATLAS_Y=540
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


# Red alert overlay is drawn in a separate atlas tile so HMI can switch
# from static amber to active red using globals.vaAlarms, without redrawing
# any gauges or altering their live cursor / temperature widgets.
ALARM_X,ALARM_Y,ALARM_W,ALARM_H=418,269,44,40
ALARM_NORMAL_ATLAS_X=500
ALARM_ACTIVE_ATLAS_X=544


def alarm_active_sprite():
    im=Image.new('RGB',(ALARM_W*S,ALARM_H*S),NAVY)
    d=ImageDraw.Draw(im)
    triangle=[(22,2),(2,37),(42,37)]
    d.polygon([((x+1)*S,(y+2)*S) for x,y in triangle],
              fill=(62,5,20))
    d.polygon([(x*S,y*S) for x,y in triangle],
              fill=(189,22,50))
    d.line([(x*S,y*S) for x,y in triangle+[triangle[0]]],
           fill=(255,83,104),width=3*S,joint='curve')
    d.line([(20*S,8*S),(6*S,34*S)],
           fill=(255,184,184),width=S)
    d.rounded_rectangle((20*S,14*S,24*S,27*S),
                        radius=2*S,fill=(255,251,245))
    d.ellipse((19*S,30*S,25*S,36*S),fill=(255,251,245))
    return im.resize((ALARM_W,ALARM_H),Image.Resampling.LANCZOS)


def render(source,preview):
    project=(source/'app.toml').read_text(encoding='utf-8')
    if 'screen = "NX4832K035"' not in project or 'rotation = 90' not in project:
        raise ValueError('only NX4832K035 at 90 degrees is supported')
    pictures=source/'pictures'
    assert (pictures/'picture-0003.png').is_file(), 'expected an editable RGB Home atlas'
    bg=make_background()
    # Only two visually different gauges exist: no fivefold pH/ORP copies.
    # Ring pressure variants and animated rotor cores remain independent.
    # The core sequence ends at x=350+11*42=812 (width of compact atlas).
    atlas=Image.new('RGB',(812,WIFI_ATLAS_Y+WIFI_H),NAVY)
    ph=gauge_sprite('pH').resize((207,150),Image.Resampling.LANCZOS)
    orp=gauge_sprite('ORP').resize((207,150),Image.Resampling.LANCZOS)
    atlas.paste(ph,(0,0))
    atlas.paste(orp,(207,0))
    # Static amber tile + red alarm tile from same 44x40 screen rectangle.
    # The Nextion chooses the tile using the ESP32's vaAlarms bit mask.
    atlas.paste(bg.crop((ALARM_X*S,ALARM_Y*S,
                         (ALARM_X+ALARM_W)*S,(ALARM_Y+ALARM_H)*S))
                .resize((ALARM_W,ALARM_H),Image.Resampling.LANCZOS),
                (ALARM_NORMAL_ATLAS_X,0))
    atlas.paste(alarm_active_sprite(),(ALARM_ACTIVE_ATLAS_X,0))
    for state in range(5):
        ring=ring_frame(bg,state).resize((FAN_SIZE,FAN_SIZE),Image.Resampling.LANCZOS)
        atlas.paste(ring,(state*FAN_SIZE,FAN_RING_ATLAS_Y))
    for frame in range(FAN_FRAMES):
        core=blade_frame(frame).resize((FAN_CORE_SIZE,FAN_CORE_SIZE),Image.Resampling.LANCZOS)
        atlas.paste(core,(FAN_CORE_ATLAS_X+frame*FAN_CORE_SIZE,FAN_RING_ATLAS_Y))
    for level in range(WIFI_LEVELS):
        tile=wifi_frame(bg,level).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS)
        atlas.paste(tile,(level*WIFI_W,WIFI_ATLAS_Y))
    # Home background starts immediately after the gauge row at y=150.
    atlas.paste(bg.resize((480,320),Image.Resampling.LANCZOS),(0,150))
    atlas.save(pictures/'picture-0003.png',optimize=True)
    demo=bg.resize((480,320),Image.Resampling.LANCZOS)
    demo.paste(atlas.crop((0,0,207,150)),(20,89))
    demo.paste(atlas.crop((207,0,414,150)),(253,89))
    # Preview uses the exact shaded 3D sprites from the firmware atlas.
    demo.paste(ring_frame(bg,1).resize((70,70),Image.Resampling.LANCZOS),
               (FAN_X,FAN_Y))
    demo.paste(blade_frame(4).resize((42,42),Image.Resampling.LANCZOS),
               (FAN_CORE_X,FAN_CORE_Y))
    demo.paste(wifi_frame(bg,4).resize((WIFI_W,WIFI_H),Image.Resampling.LANCZOS),
               (WIFI_X,WIFI_Y))
    # Preview the same live white/cyan measurement bars as the HMI script.
    # ESP32 value=7.60 around pH setpoint 7.50 -> percentage 146;
    # ORP 706 around 700 -> percentage 144. Both must be in green.
    draw_preview_gauge_cursor(demo, 20, 146)
    draw_preview_gauge_cursor(demo, 253, 144)
    d=ImageDraw.Draw(demo)
    sample_font=preview_font(26)
    d.text((123,184),'7.60',font=sample_font,fill=WHITE,anchor='mm')
    d.text((357,184),'706',font=sample_font,fill=WHITE,anchor='mm')
    d.text((296,18),'27.3°C',font=preview_font(22),
           fill=WHITE,anchor='rm')
    d.text((296,43),'7.3°C',font=preview_font(22),
           fill=WHITE,anchor='rm')
    d.text((360,22),'10:47',font=preview_font(25),
           fill=WHITE,anchor='mm')
    d.text((357,44),'27/11/26',font=preview_font(20),
           fill=WHITE,anchor='mm')
    preview.parent.mkdir(parents=True,exist_ok=True)
    demo.save(preview,optimize=True)
    print('Home atlas=812x578: 2 unique gauges + 5 rings + 11 turbine phases + 5 RSSI tiers')
    print('Preview SHA256',hashlib.sha256(preview.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--preview',required=True,type=Path)
    options=parser.parse_args()
    render(options.source,options.preview)
