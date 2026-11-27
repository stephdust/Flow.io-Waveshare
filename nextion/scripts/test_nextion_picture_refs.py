#!/usr/bin/env python3
"""Guard the compact 3.5in picture table against accidental ID drift.

Only unreferenced pictures AFTER index 20 are pruned. Keeping 0..20 at
their original positions protects xpic HomeGaugepic=3, LEDpic=1 and
PSIGaugepic=20. In particular picture-0005 is used on pageSetTime.
"""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"
app = tomllib.loads((SRC / "app.toml").read_text(encoding="utf-8"))
program = (SRC / "program.nx").read_text(encoding="utf-8")
pictures = app["pictures"]
expected = [f"picture-{i:04d}" for i in range(24)]
assert pictures == expected, "compact Nextion picture order changed"
found = sorted(p.stem for p in (SRC / "pictures").glob("picture-*.png"))
assert found == expected, "missing or unlisted picture-XXXX.png in source"

# References preserved by ID, including old numeric expressions on the RTC.
for expr in ("int HomeGaugepic=3", "int LEDpic=1", "int PSIGaugepic=20",
             "int kpad_shift_up=11", "int kpad_shift_down=14"):
    assert expr in program, f"binary-compatible picture mapping lost: {expr}"

for path in sorted((SRC / "pages").glob("*.page.toml")):
    page = tomllib.loads(path.read_text(encoding="utf-8"))
    for component in page.get("component", []):
        for key in ("pic", "picc", "pic1", "pic2", "picc1", "picc2",
                    "bpic", "ppic"):
            value = component.get(key)
            if isinstance(value, str) and value.startswith("picture-"):
                assert value in pictures, (
                    f"dangling image reference: {path.name} "
                    f"{component.get('name')} {key}={value}"
                )
            # Some legacy style=0 buttons still carry 40/41 in unused
            # fallback fields. These are unrelated to the 0..23 atlas.
            # Do not silently rewrite the old button visual conventions.

board = (SRC / "pages/pageKeyBoard.page.toml").read_text(encoding="utf-8")
sw = (SRC / "pages/pageHomeSwtch.page.toml").read_text(encoding="utf-8")
date = (SRC / "pages/pageSetTime.page.toml").read_text(encoding="utf-8")
assert '"picture-0021"' in board
assert '"picture-0022"' in sw and '"picture-0023"' in sw
assert '"picture-0005"' in date, "date/time page still uses picture 0005"
assert '"picture-0025"' not in board
assert '"picture-0031"' not in sw and '"picture-0032"' not in sw
assert (SRC / "pictures/picture-0005.png").is_file()
print("PASS: 24 compact image slots, all source PNGs accounted for")
print("PASS: Home, PSI/LED, keypad, date/time, switches IDs preserved")
print("PASS: no dangling named picture references across 9 HMI pages")
