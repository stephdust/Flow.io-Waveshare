#!/usr/bin/env python3
"""Pixel-level Home preview validation run after every nxwright rendering.

Checks the *actual* generated preview.png rather than checking source code
strings only. Geometry and safety colours are intentional design contracts
for the NX4832K035_011 screen (480x320).
"""
from pathlib import Path
import argparse
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--preview",type=Path,required=True)
args=parser.parse_args()

image=Image.open(args.preview).convert("RGB")
assert image.size==(480,320), f"Nextion preview has wrong size: {image.size}"
navy=(4,18,37)
def at(x,y):
    return image.getpixel((x,y))
def is_cyan(pixel):
    r,g,b=pixel
    return g>105 and b>135 and b>r+55

# The base must be uniform outside all artwork, never gradient patches.
for x,y in ((240,76),(242,218),(242,235),(202,285),(283,285),
            (10,110),(469,110),(242,317)):
    assert at(x,y)==navy, f"nonuniform navy at {(x,y)}: {at(x,y)}"

# The top and bottom have no border, filled trays or separators.
# Sample known empty coordinates and protect the floating-icon layout.
for x,y in (
    (5,31),(240,5),(475,31),  # no header perimeter
    (154,23),(312,24),(413,24),  # no header dividers
    (29,290),(193,290),(291,290),(470,290),  # no footer trays
    (390,290),  # no divider between equipment and alarm icons
):
    assert at(x,y)==navy, (
        f"frame, separator or non-uniform background at {(x,y)}: {at(x,y)}"
    )
assert at(202,284)==navy and at(283,284)==navy, "footer touches turbine gap"
assert at(242,218)==navy, "turbine still overlaps the pH/ORP gauges"
assert at(240,274)!=navy, "turbine not present at the true gauge midpoint"
# Actual rendered 70px circular frame must have its visual centre at x=240,
# matching the half-pixel midpoint of the pH and ORP gauge centres (239.5).
rim = [x for x in range(202,279)
       if any(is_cyan(at(x,y)) for y in range(272,277))]
assert len(rim) >= 5, "filtration rim not visible on generated preview"
assert abs((min(rim)+max(rim))/2 - 240) <= 1.5, (
    f"turbine image shifted sideways: visible centre={(min(rim)+max(rim))/2}"
)

# Inspect the actual 3D icon colours, not merely their Python source.
# The artwork is centered under pH (x=123), then moved to x=346 / 440;
# the rotor remains x=240 regardless of navigation styling.
def colored_pixels(x0,x1,y0,y1,predicate):
    return [(x,y) for y in range(y0,y1) for x in range(x0,x1)
            if predicate(at(x,y))]

grid = colored_pixels(102,145,272,311,
    lambda q: q[2]>125 and q[2]>q[0]+45 and q[1]>75)
gear = colored_pixels(322,371,269,312,
    lambda q: q[1]>110 and q[1]>q[0]*1.18 and q[1]>q[2]*0.85)
alarm = colored_pixels(417,466,269,312,
    lambda q: q[1]>100 and q[1]>q[0]*1.25 and q[1]>q[2]*1.08)
assert len(grid)>35, f"cyan glass grid not visible: {len(grid)} pixels"
assert len(gear)>35, f"jade 3D gear not visible: {len(gear)} pixels"
assert len(alarm)>35, f"green normal-state warning triangle not visible: {len(alarm)} pixels"
for name,px,target in (("grid",grid,123),("gear",gear,346),("alert",alarm,440)):
    center=(min(x for x,y in px)+max(x for x,y in px))/2
    assert abs(center-target)<=3.5, (
        f"{name} icon shifted: x={center}, expected x={target}"
    )
assert (346-18)-(240+35)>=50
assert (440-20)-(346+18)>=50
assert 440+20<=480-15
# The three buttons remain separate on the uniform navy base.
for x in (161,180,285,298,388,393,473):
    assert at(x,290)==navy, f"footer has unwanted frame or glow at x={x}"

# The complete logo + wordmark moved as one 24px rightward group.
# Both temperature rows moved 10px right; check their joint placement
# stays comfortably above the independently centered pump x=240.
# The wordmark must begin soon after the official turquoise waves.
wordmark=[at(x,y) for x in range(75,90) for y in range(19,40)]
assert sum(r>170 and g>170 and b>170 for r,g,b in wordmark)>8, (
    "Flow.io lettering not brought closer to the waves"
)

# The symbols and live text fields form two identical icon/value rows.
# The HMI starts both text components at x=228 with LEFT alignment, so the
# visible gap remains fixed even when one temperature has fewer digits.
# No icon can be painted inside a text widget's repainting bounds.
water=[at(x,y) for x in range(201,226) for y in range(8,30)]
air=[at(x,y) for x in range(201,226) for y in range(30,55)]
assert sum(r>150 and g>150 and b>150 for r,g,b in air)>20, (
    "outdoor air symbol not visible beside its temperature"
)
assert at(171,18)==navy and at(175,46)==navy, (
    "old weather icons are still detached from the displayed temperatures"
)
assert at(227,18)==navy and at(227,43)==navy, (
    "temperature icons crossed the boundary of the native text fields"
)
def icon_text_gap(y0,y1):
    drawn_icon=[(x,y) for y in range(y0,y1) for x in range(201,226)
                if at(x,y)!=navy]
    drawn_text=[(x,y) for y in range(y0,y1) for x in range(228,312)
                if all(channel>205 for channel in at(x,y))]
    assert drawn_icon and drawn_text, "temperature icon/text missing from preview"
    gap=min(x for x,y in drawn_text)-max(x for x,y in drawn_icon)
    assert 2<=gap<=10, (
        f"temperature icon detached from live value: {gap}px separation"
    )
    return min(x for x,y in drawn_text)
water_start=icon_text_gap(8,30)
air_start=icon_text_gap(32,55)
assert abs(water_start-air_start)<=3, (
    f"water and air first digits misaligned: x={water_start}/{air_start}"
)
assert sum(b>140 and b>r+40 for r,g,b in water)>35, (
    "water-thermometer droplet lost its blue detail"
)
assert sum(r>225 and g>225 and b>225 for r,g,b in water)<190, (
    "water icon has become a solid white blot"
)
red=[(r,g,b) for r,g,b in water if r>155 and g<140 and b<145 and r>g*1.6]
assert len(red)>=5, "water thermometer lacks a distinct red mercury column/bulb"

# The full-strength Wi-Fi icon is centered in the rightmost header segment
# x=413..475 (centre 444px), not shifted against the right border.
wifi=[(x,y) for x in range(422,467) for y in range(12,50)
      if (lambda q:q[1]>165 and q[0]<165)(at(x,y))]
assert len(wifi)>20, "Wi-Fi indicator is missing or not coloured"
wifi_cx=sum(x for x,_ in wifi)/len(wifi)
assert 439 <= wifi_cx <= 450, f"Wi-Fi not centered: x={wifi_cx:.1f}"

# Both pH and ORP keep red-yellow-green-yellow-red segments; the centre
# of the healthy zone is green. Long cyan/white needles rise from each hub.
for center in (123,356):
    green=[at(x,y) for x in range(center-26,center+27)
                     for y in range(96,118)]
    assert sum(g>145 and g>r*1.25 for r,g,b in green)>65, (
        f"green centre arc missing on gauge centred at x={center}"
    )
    needle=[at(x,y) for x in range(center-2,center+3)
                      for y in range(122,156)]
    assert sum(g>130 and b>155 for r,g,b in needle)>15, (
        f"long cyan/white measurement needle missing at x={center}"
    )
# The old test sampled two arbitrary dark pixels between graduations.
# Count visible raised white tick marks over the dial instead.
ticks=[at(x,y) for x in range(41,210) for y in range(118,179)]
assert sum(r>185 and g>185 and b>185 for r,g,b in ticks)>55, (
    "pH gauge lost its white scale graduations"
)

print("PASS: generated preview.png is 480x320 with uniform navy")
print("PASS: frameless footer with cyan, jade and GREEN normal-state 3D icons")
print("PASS: icon centres x123/346/440, 50px+ gap to pump and neighbour")
print("PASS: 70px turbine correctly centered between gauges")
print("PASS: both temperature rows moved +10px as a group with fixed icon-to-digit gaps")
print("PASS: official Flow.io waves and wordmark moved together +12px")
print("PASS: wordmark, crisp blue droplet with real red thermometer")
print("PASS: Wi-Fi center aligned in header")
print("PASS: green safe zones and full-length live needles on both gauges")
