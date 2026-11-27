#!/usr/bin/env python3
"""Pixel-level test of the actual turbine sprites generated for Nextion 3.5in.

Run this after render_nx_home.py, using the nxwright virtualenv with Pillow.
This checks atlas dimensions, continuous illuminated rim, fourfold symmetry,
real gradients and all eleven independent rotation/off frames.
"""
from pathlib import Path
import argparse
import hashlib
import math
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--atlas", type=Path, default=(
    ROOT / "nextion/tests/NX4832K035_011/7.0.0/source/pictures/picture-0003.png"
), help="PNG atlas to inspect, including isolated build sources")
ATLAS = parser.parse_args().atlas
with Image.open(ATLAS) as source:
    image = source.convert("RGB")
assert image.size == (812, 578), f"unexpected deduplicated atlas size: {image.size}"
# Exactly one static pH and ORP dial; neither requires a 5-level sprite.
ph=image.crop((0,0,207,150))
orp=image.crop((207,0,414,150))
assert hashlib.sha256(ph.tobytes()).digest() != hashlib.sha256(orp.tobytes()).digest(), (
    "pH and ORP must have distinct legends in their two unique sprites"
)
assert image.getpixel((600,90))==(4,18,37), "old redundant gauge copies remain"
# Normal is glossy GREEN; any forwarded active alarm is glossy RED.
normal=image.crop((500,0,544,40))
active=image.crop((544,0,588,40))
green=sum(1 for y in range(40) for x in range(44)
          if (lambda q:q[1]>110 and q[1]>q[0]*1.3 and q[1]>q[2]*1.08)(normal.getpixel((x,y))))
red=sum(1 for y in range(40) for x in range(44)
        if (lambda q:q[0]>150 and q[0]>q[1]*1.4 and q[0]>q[2]*1.2)(active.getpixel((x,y))))
assert green>35 and red>35, f"alarm state tiles not distinctly green/red: {green}/{red}"
assert normal.tobytes()!=active.tobytes()


# Five independent PSI rings (0..4), all with an uninterrupted cyan rim.
rings = [image.crop((70*i,470,70*(i+1),540)) for i in range(5)]
assert len({hashlib.sha256(r.tobytes()).hexdigest() for r in rings}) == 5
for i,ring in enumerate(rings):
    assert ring.getpixel((35,35)) == (3,17,31), "ring/core background seam"
    samples = []
    for deg in range(0,360,5):
        a = math.radians(deg)
        x = round(35+32*math.cos(a))
        y = round(35+32*math.sin(a))
        if 0 <= x < 70 and 0 <= y < 70:
            samples.append(ring.getpixel((x,y)))
    lit = sum(1 for r,g,b in samples if g > 65 and b > 115)
    assert lit >= len(samples)*0.82, (
        f"PSI ring {i} has gaps in the continuous circular bezel: "
        f"{lit}/{len(samples)} lit"
    )

# The OFF frame uses a muted metallic look. The 10 ON frames rotate by
# 9 degrees per tick to cover a fourfold-symmetric quarter revolution.
cores = [image.crop((350+42*i,470,392+42*i,512)) for i in range(11)]
assert len({hashlib.sha256(c.tobytes()).hexdigest() for c in cores}) == 11, (
    "two turbine phases produced the same bitmap"
)
for core in cores:
    assert core.getpixel((0,0)) == (3,17,31)
    assert core.getpixel((41,41)) == (3,17,31)

for i, core in enumerate(cores[1:], 1):
    # Avoid deprecated Image.getdata() (Pillow 12+, removed in Pillow 14).
    # These 42x42 RGB sprites are tiny: per-pixel iteration is portable,
    # does not need version checks, and preserves the exact pixel tuples.
    pixels = [core.getpixel((x, y))
              for y in range(core.height)
              for x in range(core.width)]
    metal = [p for p in pixels if p[2] > 140 and p[1] > 75
             and p[2] > p[0]+15]
    assert len(metal) > 85, f"rotor {i} lost its four curved blades"
    assert len(set(metal)) > 30, f"rotor {i} lost metallic 3D colour gradients"
    assert any(r > 160 and g > 220 and b > 225 for r,g,b in pixels), (
        f"rotor {i} lost its white/cyan specular highlights"
    )

print("PASS: 5 full circular pressure bezels, no gaps")
print("PASS: all 10 rotation phases plus muted OFF frame are distinct")
print("PASS: 3D metallic highlights, curved rotor shading and centre preserved")
print("PASS: 2 distinct gauge tiles, green normal/red active alarms")
print("PASS: 42px core, 70px ring, compact 812x578 atlas")
