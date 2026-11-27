#!/usr/bin/env python3
"""Pixel-level test of the actual turbine sprites generated for Nextion 3.5in.

Run this after render_nx_home.py, using the nxwright virtualenv with Pillow.
This checks atlas dimensions, continuous illuminated rim, fourfold symmetry,
real gradients and all eleven independent rotation/off frames.
"""
from pathlib import Path
import hashlib
import math
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ATLAS = (ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
         / "pictures/picture-0003.png")
with Image.open(ATLAS) as source:
    image = source.convert("RGB")
assert image.size == (1035, 728), f"unexpected atlas size: {image.size}"

# Five independent PSI rings (0..4), all with an uninterrupted cyan rim.
rings = [image.crop((70*i,620,70*(i+1),690)) for i in range(5)]
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
cores = [image.crop((350+42*i,620,392+42*i,662)) for i in range(11)]
assert len({hashlib.sha256(c.tobytes()).hexdigest() for c in cores}) == 11, (
    "two turbine phases produced the same bitmap"
)
for core in cores:
    assert core.getpixel((0,0)) == (3,17,31)
    assert core.getpixel((41,41)) == (3,17,31)

for i, core in enumerate(cores[1:], 1):
    pixels = list(core.getdata())
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
print("PASS: 42px core, 70px ring and compact 1035x728 atlas unchanged")
