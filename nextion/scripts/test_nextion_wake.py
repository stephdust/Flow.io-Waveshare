#!/usr/bin/env python3
"""Check Home wake redraw contract without hardware or a firmware compilation."""
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nextion/tests/NX4832K035_011/7.0.0/source"


def get_event(source: str, event: str) -> str:
    matched = re.search(r"(?ms)^on " + re.escape(event) + r":\n(.*?)(?=^on |\Z)", source)
    assert matched, "event missing: " + event
    return matched.group(1)


def main() -> None:
    project = tomllib.loads((BASE / "app.toml").read_text(encoding="utf-8"))
    assert project["screen"] == "NX4832K035"
    assert project["rotation"] == 90
    assert project["pages"].index("pageHome") == 1, "wup=1 must refer to Home"
    source = (BASE / "pages/pageHome.nx").read_text(encoding="utf-8")
    initial = get_event(source, "pageHome.load")
    final = get_event(source, "pageHome.loadend")
    leaving = get_event(source, "pageHome.unload")
    tick = get_event(source, "tmUpdate.timer")
    gauges = get_event(source, "bUpdateGauge.down")
    assert re.search(r"(?m)^\s*wup=1\s*$", initial)
    assert re.search(r"(?m)^\s*wup=255\s*$", leaving)
    assert "xpic 0,0,480,320,0,300,HomeGaugepic" in final
    assert final.index("vaPrvpHPercen.val=-1") < final.index("click bUpdateGauge,1")
    assert final.index("vaPrvOrpPercen.val=-1") < final.index("click bUpdateGauge,1")
    assert "xpic 20,89,207,150,sys1,0,HomeGaugepic" in gauges
    assert "xpic 253,89,207,150,sys1,150,HomeGaugepic" in gauges
    assert "vaPrvWifiLevel.val=-1" in final
    assert "xpic 423,11,43,38,sys1,690,HomeGaugepic" in gauges
    assert "vis tErrMessage,0" in initial
    assert not re.search(r"(?m)^\s*ref b[01]\s*$", final), "opaque footer buttons redrawn"
    assert "click bUpdateGauge,1" in tick
    print("PASS: Home wake reloads and redraws xpic background + two gauge sprites")
    print("PASS: leaving Home restores wup=255; normal navigation is unchanged")


if __name__ == "__main__":
    main()
