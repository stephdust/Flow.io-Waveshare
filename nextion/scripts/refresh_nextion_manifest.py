#!/usr/bin/env python3
"""Refresh the Flow.io 7.0.0 Nextion TFT and binary/manifest.json without PlatformIO.

Called internally by: pio run -e nextion -t manifest
This reuses scripts/export_binaries.py's production naming, hash, and manifest
logic with a tiny stub PlatformIO environment; it does not compile ESP32/SPIFFS.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import runpy
import sys


class _ManifestOnlyEnv(dict):
    def __init__(self, project: Path, version: str) -> None:
        super().__init__(CPPDEFINES=[("TFT_FIRMW", f'"{version}"')])
        self.project = project

    def subst(self, value: str) -> str:
        # Never announce the real Waveshare build environment: otherwise the
        # exporter registers an ESP32 SPIFFS build hook during import.
        return {
            "$PROJECT_DIR": str(self.project),
            "$PIOENV": "nextion-manifest-only",
        }.get(value, value)

    def AddPostAction(self, *args, **kwargs) -> None:
        # PlatformIO post-build registration is deliberately disabled.
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="7.0.0",
                        help="Nextion version (default: 7.0.0)")
    args = parser.parse_args()
    if args.version != "7.0.0":
        parser.error("this test-only helper is restricted to Nextion 7.0.0")

    root = Path(__file__).resolve().parents[2]
    exporter = root / "scripts" / "export_binaries.py"
    release_dir = root / "nextion" / "releases" / args.version
    binary_dir = root / "binary"
    filename = f"FlowIO_Nextion_NX4832K035_011-{args.version}.tft"
    source = release_dir / filename
    if not source.is_file() or source.stat().st_size < 4096:
        parser.error(f"missing or suspiciously small TFT: {source}")
    # Fresh clones may not have binary/ yet (it is gitignored).
    # Exporting a Nextion-only manifest must not require an ESP32 build.
    binary_dir.mkdir(parents=True, exist_ok=True)
    # Avoid accidental exports of 5-inch / 7-inch files from this helper.
    other_tfts = [p.name for p in release_dir.glob("*.tft") if p.name != filename]
    if other_tfts:
        parser.error("unexpected TFT in 7.0.0 release: " + ", ".join(other_tfts))
    if not exporter.is_file():
        parser.error(f"missing export script: {exporter}")

    # The exporter imports scripts/version_utils.py from the project directory.
    sys.path.insert(0, str(root / "scripts"))
    env = _ManifestOnlyEnv(root, args.version)
    exporter_functions = runpy.run_path(
        str(exporter),
        init_globals={"Import": lambda _name: None, "env": env},
    )
    exporter_functions["_export_nextion_release"]()
    destination = binary_dir / filename
    manifest = binary_dir / "manifest.json"
    assert destination.read_bytes() == source.read_bytes(), "TFT copy mismatch"
    assert manifest.is_file(), "manifest.json not created"
    print(f"OK: {destination.relative_to(root)} ({destination.stat().st_size} bytes)")
    print(f"OK: {manifest.relative_to(root)} updated with TFT SHA-256")
    print("No ESP32/SPIFFS compile; paired OTA release ZIP remains unchanged.")
    print("If using a separate HTTP server, upload both the TFT and manifest.json there.")


if __name__ == "__main__":
    main()
