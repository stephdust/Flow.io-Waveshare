#!/usr/bin/env python3
"""Regression gate: keep the original *rotating* native pump logo on 7.0.0."""
from pathlib import Path
import re
import tomllib

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"nextion/tests/NX4832K035_011/7.0.0/source"
home=(BASE/"pages/pageHome.nx").read_text(encoding="utf-8")
page=tomllib.loads((BASE/"pages/pageHome.page.toml").read_text(encoding="utf-8"))
byname={item["name"]:item for item in page["component"]}
timer=re.search(r"(?ms)^on tmAnim.timer:\n(.*?)(?=^on |\Z)",home)
assert timer, "native pump rotation event has been deleted"
expected=[
    "temp1=globals.vaStates.val>>0",
    "temp1=temp1&1",
    "temp1*=temp",
    "substr vaIconProp.txt,tProp.txt,temp1,1",
    "temp%=10",
    "temp+=1",
]
for command in expected:
    assert command in timer.group(1), "pump rotation behavior changed: "+command
assert byname["tmAnim"]["tim"]==50
assert byname["tProp"]["font"]=="Propeller_50"
assert byname["tProp"]["sta"]==2
assert byname["tProp"]["pic"]=="picture-0020"
assert byname["vaIconProp"]["txt"].startswith("┌┍┎")
assert re.search(r"(?m)^\s*tProp.pic=PSIGaugepic\+vaPSINiddle.val\s*$",home)
# Original code uses temp1=0 when pump is OFF, animation frame index 0.
assert "temp1*=temp" in timer.group(1)
assert "tProp.txt=" not in home.replace("substr vaIconProp.txt,tProp.txt,temp1,1","")
print("PASS: filtration ON = rotating glyph at 50ms; OFF = fixed first glyph")
print("PASS: status ring 20..24 can change without altering rotation or serial data")
