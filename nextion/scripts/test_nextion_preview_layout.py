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

# Two separate footer frames with open central gap, unlike a continuous bar.
assert any(is_cyan(at(x,284)) for x in (192,193)), "left footer border absent"
assert any(is_cyan(at(x,284)) for x in (290,291,292)), "right footer border absent"
# The one-pixel divider is deliberately dim. Source tests verify its position;
# avoid false negatives from JPEG-like downsampling of thin RGB565 strokes.
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

# The wordmark must begin soon after the official turquoise waves.
wordmark=[at(x,y) for x in range(49,62) for y in range(19,40)]
assert sum(r>170 and g>170 and b>170 for r,g,b in wordmark)>8, (
    "Flow.io lettering not brought closer to the waves"
)

# The upper water symbol must be blue/cyan and contain a thermometer,
# not the opaque bright white blob shown in the earlier hardware photo.
water=[at(x,y) for x in range(161,183) for y in range(8,30)]
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
print("PASS: compact twin footer frames, free pump gap, lowered 3D turbine")
print("PASS: wordmark, crisp blue droplet with real red thermometer")
print("PASS: Wi-Fi center aligned in header")
print("PASS: green safe zones and full-length live needles on both gauges")
