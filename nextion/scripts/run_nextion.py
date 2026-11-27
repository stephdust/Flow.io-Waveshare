#!/usr/bin/env python3
"""Single PlatformIO Nextion pipeline: nxwright HMI/TFT or quick TFT manifest.

Use from the repository root:
  pio run -e nextion                 # ignored .pio/ output; refresh binary/ manifest
  pio run -e nextion -t manifest     # no compile: just TFT copy + manifest

Only NX4832K035_011, 480x320, release 7.0.0 on the development fork.
Does NOT touch tracked HMI, TFT, preview.png or picture-0003.png.
Never compiles ESP32, SPIFFS, 5-inch/7-inch displays, or flashes hardware.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[2]
VERSION = "7.0.0"
MODEL = "NX4832K035_011"
SOURCE = ROOT / "nextion" / "tests" / MODEL / VERSION / "source"
RELEASE = ROOT / "nextion" / "releases" / VERSION
HMI_NAME = f"FlowIO_Nextion_{MODEL}-{VERSION}.HMI"
TFT_NAME = f"FlowIO_Nextion_{MODEL}-{VERSION}.tft"
# Match the HMI name exactly, changing only the extension.
# Each HMI contains several Nextion pages. Today only the pageHome preview
# is rendered, so its page name MUST appear in its PNG filename.
# Future page renderers can use the same naming rule for pageAlarms, etc.
PREVIEW_PAGE = "pageHome"
PREVIEW_NAME = f"{Path(HMI_NAME).stem}-{PREVIEW_PAGE}.png"
NXWRIGHT_COMMIT = "e9443a409cc9deb866db7486854fa962d382accc"
VENV = ROOT / ".pio" / "nextion-nxwright-venv"
# All regular build outputs are ignored by Git. Tracked releases/previews and
# the source picture atlas are modified only by an explicit release promotion.
OUTPUT = ROOT / ".pio" / "nextion-output"
# Keep each screen's preview in an isolated model/version path. This can
# coexist with NX8048P050/NX8048P070 previews when their builds are added.
PREVIEW_OUTPUT = OUTPUT / MODEL / VERSION / PREVIEW_NAME
LEGACY_PREVIEWS = (
    ROOT / "binary" / "nextion-preview.png",
    OUTPUT / "preview.png",
    OUTPUT / MODEL / VERSION / "preview.png",
    OUTPUT / MODEL / VERSION / Path(HMI_NAME).with_suffix(".png").name,
)


def cleanup_legacy_previews() -> None:
    """Remove obsolete preview copies, never the canonical per-model file."""
    for old in LEGACY_PREVIEWS:
        old.unlink(missing_ok=True)


def execute(*argv: str) -> None:
    print("[NEXTION] " + " ".join(str(arg) for arg in argv), flush=True)
    subprocess.run([str(x) for x in argv], cwd=ROOT, check=True)


def check_source() -> None:
    app = SOURCE / "app.toml"
    home = SOURCE / "pages" / "pageHome.nx"
    if not app.is_file() or not home.is_file():
        raise RuntimeError(f"Nextion nxwright sources not found: {SOURCE}")
    text = app.read_text(encoding="utf-8")
    # Never label one page with another page's name.
    import tomllib
    if PREVIEW_PAGE not in tomllib.loads(text).get("pages", []):
        raise RuntimeError(f"Nextion preview page missing in app.toml: {PREVIEW_PAGE}")
    if not re.search(r'(?m)^screen\s*=\s*"NX4832K035"\s*$', text):
        raise RuntimeError("Only NX4832K035 Nextion 480x320 is supported")
    if not re.search(r'(?m)^rotation\s*=\s*90\s*$', text):
        raise RuntimeError("Expected 90-degree orientation for NX4832K035")
    # Keep version fixed until a reviewed upstream PR.
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    if not re.search(r'(?m)^nextion_firmware_version\s*=\s*[^\r\n]*7\.0\.0', ini):
        raise RuntimeError("platformio.ini no longer selects Nextion 7.0.0")


def nxwright_path() -> Path:
    """Install pinned nxwright once into a separate .pio venv; not ESP32's Python.

    The first compilation needs network access for GitHub and Nextion Editor
    firmware (--download); subsequent runs reuse the isolated environment.
    The manifest-only target does not create or inspect this environment.
    """
    exe = VENV / ("Scripts/nxwright.exe" if os.name == "nt" else "bin/nxwright")
    if exe.is_file():
        return exe

    if sys.version_info < (3, 11):
        raise RuntimeError("nxwright needs Python 3.11+; update your PlatformIO Python")
    VENV.parent.mkdir(parents=True, exist_ok=True)
    print("[NEXTION] First use: installing pinned nxwright in .pio/nextion-nxwright-venv", flush=True)
    venv.EnvBuilder(with_pip=True).create(VENV)
    py = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    execute(str(py), "-m", "pip", "install", "--no-cache-dir",
            f"git+https://github.com/nixiewright/nxwright.git@{NXWRIGHT_COMMIT}")
    if not exe.is_file():
        raise RuntimeError("nxwright installation completed but CLI is missing")
    return exe


def publish_file(staged: Path, destination: Path) -> None:
    if not staged.is_file() or staged.stat().st_size < 4096:
        raise RuntimeError(f"Nextion file is missing or unexpectedly small: {staged}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Copy to the same directory first, then replace atomically (also on Windows).
    temporary = destination.with_name(destination.name + ".nextion-tmp")
    try:
        shutil.copyfile(staged, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def refresh_manifest(tft_source: Path | None = None) -> None:
    helper = ROOT / "nextion" / "scripts" / "refresh_nextion_manifest.py"
    arguments = ["--tft-source", str(tft_source)] if tft_source else []
    execute(sys.executable, str(helper), *arguments)
    print("[NEXTION] Done: ignored binary/TFT and binary/manifest.json updated.", flush=True)


def compile_nextion() -> None:
    check_source()
    # Fast host-side checks protect legacy IDs, Home wake redraw,
    # packed turbine atlas and live outdoor-temperature layout.
    for test_name in (
        "test_nextion_wake.py",
        "test_nextion_animation.py",
        "test_nextion_gauges.py",
        "test_nextion_picture_refs.py",
        "test_nextion_page_navigation.py",
        "test_nextion_outdoor_temp.py",
        "test_nextion_footer_touch.py",
    ):
        execute(sys.executable, str(ROOT / "nextion" / "scripts" / test_name))
    # Keep ESP32 RSSI packing and the Home atlas in sync during LOCAL builds,
    # not just in GitHub CI; otherwise a stale Wi-Fi test can break CI later.
    execute(sys.executable, str(ROOT / "scripts/tests/test_nextion_wifi_rssi.py"))
    nx = nxwright_path()
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    renderer = ROOT / "nextion/scripts/render_nx_home.py"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (ROOT / ".pio").mkdir(exist_ok=True)
    # Rendering into SOURCE used to dirty tracked picture-0003.png after every
    # local build; likewise writing to nextion/releases or preview.png made
    # git pull impossible. Copy the complete editable source into .pio first.
    with tempfile.TemporaryDirectory(prefix="nextion-build-", dir=ROOT / ".pio") as folder:
        scratch = Path(folder)
        work_source = scratch / "source"
        shutil.copytree(SOURCE, work_source)
        work_preview = scratch / PREVIEW_NAME
        staged_hmi = scratch / HMI_NAME
        staged_tft = scratch / TFT_NAME
        readback = scratch / "hmi-check"

        execute(str(python), str(renderer), "--source", str(work_source),
                "--preview", str(work_preview))
        # Never ship graphical changes without checking the generated PNG.
        execute(str(python), str(ROOT / "nextion/scripts/test_nextion_preview_layout.py"),
                "--preview", str(work_preview))
        execute(str(python), str(ROOT / "nextion/scripts/test_nextion_turbine_3d.py"),
                "--atlas", str(work_source / "pictures" / "picture-0003.png"))
        execute(str(nx), "check", str(work_source))
        execute(str(nx), "build", str(work_source), str(staged_hmi), "--no-lock")
        # Validate the rebuilt HMI can be extracted, unlike the old .pa/.i patch.
        execute(str(nx), "extract", str(staged_hmi), str(readback))
        execute(str(nx), "check", str(readback))
        execute(str(nx), "compile", str(work_source), str(staged_tft), "--download")
        execute(str(nx), "tft-read", str(staged_tft))

        publish_file(staged_hmi, OUTPUT / HMI_NAME)
        publish_file(staged_tft, OUTPUT / TFT_NAME)
        publish_file(work_preview, PREVIEW_OUTPUT)
        publish_file(work_source / "pictures/picture-0003.png",
                     OUTPUT / "picture-0003.png")
        print(f"[NEXTION] Preview for page {PREVIEW_PAGE}: {PREVIEW_OUTPUT.relative_to(ROOT)}",
              flush=True)
        print("[NEXTION] HMI/TFT built in ignored .pio/nextion-output; "
              "tracked release files and source PNGs untouched.", flush=True)
    refresh_manifest(OUTPUT / TFT_NAME)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("compile", "manifest"))
    args = parser.parse_args()
    # Also clean old preview copies in manifest-only mode: no legacy PNG
    # should remain in binary/ after either PlatformIO Nextion target.
    cleanup_legacy_previews()
    if args.mode == "compile":
        compile_nextion()
    else:
        refresh_manifest()


if __name__ == "__main__":
    main()
