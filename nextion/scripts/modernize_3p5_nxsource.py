#!/usr/bin/env python3
"""Modernize the EXTRACTED/EDITABLE nxwright NX4832K035 7.0.0 source.

This NEVER edits binary HMI resources. Do not use the older binary .pa/.i patcher.
Only one page (pageHome) and picture IDs 3, 20, 21, 22, 23, 24 change.
The program, all other pages, fonts, and component IDs are left intact.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw

from build_3p5_v7_modern import render_atlas, rgb565


def update_component(source: str, name: str, attributes: dict[str, str]) -> str:
    pattern = r'(?ms)(^\[\[component\]\]\nname = "' + re.escape(name) + r'"\n.*?)(?=^\[\[component\]\]|\Z)'
    hits = list(re.finditer(pattern, source))
    if len(hits) != 1:
        raise ValueError(f'expected exactly one component {name}, found {len(hits)}')
    match = hits[0]
    part = match.group(1)
    for attribute, value in attributes.items():
        attr = re.compile(r'(?m)^' + re.escape(attribute) + r' = [^\n]+$')
        if len(attr.findall(part)) != 1:
            raise ValueError(f'{name}.{attribute} is absent or ambiguous')
        part = attr.sub(f'{attribute} = {value}', part)
    return source[:match.start()] + part + source[match.end():]


def edit_home_text(source_folder: Path) -> None:
    script = source_folder / 'pages' / 'pageHome.nx'
    data = script.read_text(encoding='utf-8')
    old = "on pageHome.loadend:\n  // Update the values\n  click bUpdateGauge,1"
    new = """on pageHome.loadend:
  // Draw the complete navy Flow.io background from the extra atlas rows.
  // Leave native component IDs, timers and touch events unchanged.
  vis tPHTitle,0
  vis tOrpTitle,0
  xpic 0,0,480,320,0,150,HomeGaugepic
  // Force BOTH gauge sprites to be redrawn after every page load/wake.
  vaPrvpHPercen.val=-1
  vaPrvOrpPercen.val=-1
  // Restore live native components that the background image covered.
  ref tWaterTemp
  ref tTime
  ref tDate
  ref tWifiState
  ref tFConnectState
  ref tpH
  ref tORP
  ref tProp
  ref tpHInject
  ref tChlInject
  ref tSWGRunning
  ref tErrMessage
  ref b0
  ref b1
  // Update the values
  click bUpdateGauge,1"""
    if data.count(old) != 1:
        raise ValueError("unexpected pageHome.loadend source")
    data = data.replace(old, new)
    for component in ("tpH", "tORP"):
        for color in ("Red_Color", "Orange_Color", "Green_Color"):
            before = f"{component}.bco={color}"
            if data.count(before) != 1:
                raise ValueError(f"unrecognized gauge color command {before}")
            data = data.replace(before, f"{component}.bco={rgb565((4,18,37))}")
    # Blue when the state is unknown, green when WiFi is up, cyan with MQTT.
    if data.count("tWifiState.pco=1178") != 1 or data.count("tWifiState.pco=65535") != 1:
        raise ValueError("unexpected WiFi source")
    data = data.replace("tWifiState.pco=1178", f"tWifiState.pco={rgb565((45,239,142))}")
    data = data.replace("tWifiState.pco=65535", f"tWifiState.pco={rgb565((6,224,234))}")
    script.write_text(data, encoding='utf-8')

    toml_path = source_folder / 'pages' / 'pageHome.page.toml'
    page = toml_path.read_text(encoding='utf-8')
    if page.count('bco = "#21557b"') < 10:
        raise ValueError("unexpected Home page styling")
    page = page.replace('[page]\nname = "pageHome"', '[page]\nname = "pageHome"', 1)
    page = page.replace('bco = "#21557b"', 'bco = "#041225"')
    # The header and footer are solid navy in the Atlas; avoid old blue boxes.
    for name in ('tWaterTemp','tTime','tDate','tWifiState','tFConnectState'):
        page = update_component(page, name, {'bco':'"#041b33"'})
    for name in ('tpH','tORP'):
        page = update_component(page, name, {'bco':'"#041225"'})
    for name in ('b0','b1'):
        page = update_component(page, name, {'bco':'"#041c35"','bco2':'"#041c35"'})
    for name in ('tpHInject','tChlInject','tSWGRunning'):
        page = update_component(page, name, {'bco':'"#041c35"'})
    # tPHTitle and tOrpTitle remain in the project (same IDs), but the native
    # page post-init hides them because their captions are rendered in the Atlas.
    toml_path.write_text(page, encoding='utf-8')


def refresh_spinner_images(source_folder: Path, atlas: Image.Image) -> None:
    icons = source_folder / 'pictures'
    # The base is exactly the background that will be under the native
    # propeller, including the header/footer transition, so no visible square.
    base = atlas.crop((207, 150+210, 277, 150+280)).convert('RGB')
    colors = [(153,168,181), (65,221,132), (248,208,42),
              (254,132,27), (244,62,81)]
    for i, color in enumerate(colors):
        upscale = base.resize((210,210), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(upscale)
        draw.arc((15,15,195,195), 30,300,fill=color,width=15)
        for k in range(4):
            angle=k*math.pi/2
            x=35+19*math.cos(angle)
            y=35+19*math.sin(angle)
            draw.ellipse((int((x-8)*3),int((y-5)*3),
                          int((x+7)*3),int((y+5)*3)),fill=(220,247,255))
        draw.ellipse((93,93,117,117),fill=(32,133,187))
        target=icons/f'picture-{20+i:04}.png'
        if not target.is_file():
            raise ValueError(f"original native filtration picture missing: {target}")
        upscale.resize((70,70),Image.Resampling.LANCZOS).save(target,optimize=True)


def modernize(source: Path, logo: Path, preview: Path) -> None:
    toml = (source/'app.toml').read_text(encoding='utf-8')
    if not re.search(r'^screen = "NX4832K035"$',toml,re.M):
        raise ValueError('only NX4832K035, not 5-inch/7-inch')
    if not re.search(r'^rotation = 90$',toml,re.M):
        raise ValueError('expected a 90 degree NX4832K035 project')
    if not re.search(r'^    "pageHome",$',toml,re.M) or not re.search(r'^    "picture-0003",$',toml,re.M):
        raise ValueError('source is not the expected version 7.0.0')
    before_program=hashlib.sha256((source/'program.nx').read_bytes()).hexdigest()
    old = source/'pictures/picture-0003.jpg'
    if not old.is_file():
        raise ValueError('expected original 5-frame 1035x150 HomeGaugepic JPEG')
    with Image.open(old) as im:
        if im.size != (1035,150):
            raise ValueError('original HomeGaugepic image has unexpected dimensions')
    atlas=render_atlas(logo,preview)
    if atlas.size != (1035,470):
        raise ValueError('new atlas dimensions mismatch')
    atlas.save(source/'pictures/picture-0003.png',optimize=True)
    old.unlink()
    refresh_spinner_images(source,atlas)
    edit_home_text(source)
    if hashlib.sha256((source/'program.nx').read_bytes()).hexdigest()!=before_program:
        raise ValueError('global protocol constants changed unexpectedly')
    print('MODERNIZED NXWRIGHT SOURCE',source)
    print('Changed: pageHome.nx, pageHome.page.toml, picture-0003 and pictures 20-24')
    print('UNCHANGED: global variables, version 7.0.0, other pages, fonts and navigation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--logo',type=Path,required=True)
    parser.add_argument('--preview',type=Path,required=True)
    args=parser.parse_args()
    modernize(args.source,args.logo,args.preview)


if __name__=='__main__':
    main()
