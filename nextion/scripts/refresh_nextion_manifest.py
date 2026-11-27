#!/usr/bin/env python3
"""Refresh the Flow.io 7.0.0 Nextion TFT and binary/manifest.json without PlatformIO.

Called internally by: pio run -e nextion -t manifest
This reuses scripts/export_binaries.py's production naming, hash, and manifest
logic with a tiny stub PlatformIO environment; it does not compile ESP32/SPIFFS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
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
    parser.add_argument("--tft-source", type=Path,
                        help="Use this compiled TFT instead of the tracked release asset")
    args = parser.parse_args()
    if args.version != "7.0.0":
        parser.error("this test-only helper is restricted to Nextion 7.0.0")

    root = Path(__file__).resolve().parents[2]
    exporter = root / "scripts" / "export_binaries.py"
    release_dir = root / "nextion" / "releases" / args.version
    binary_dir = root / "binary"
    filename = f"FlowIO_Nextion_NX4832K035_011-{args.version}.tft"
    # A normal local build lives in ignored .pio/, never in tracked release/.
    # The standalone manifest target also works on fresh clones, falling back
    # to the published release when no local TFT has been compiled yet.
    local_tft = root / ".pio" / "nextion-output" / filename
    source = args.tft_source or (local_tft if local_tft.is_file()
                                 else release_dir / filename)
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
    destination = binary_dir / filename
    if source.resolve() == (release_dir / filename).resolve():
        # Legacy manifest-only path for clean checkouts: use published TFT.
        exporter_functions["_export_nextion_release"]()
    else:
        # Never copy generated TFT back into tracked nextion/releases/.
        # Use the same exporter manifest logic after an atomic binary copy.
        temporary = destination.with_name(destination.name + ".nextion-tmp")
        try:
            shutil.copy2(source, temporary)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        exporter_functions["_update_manifest"]()
    manifest = binary_dir / "manifest.json"
    assert destination.read_bytes() == source.read_bytes(), "TFT copy mismatch"
    assert manifest.is_file(), "manifest.json not created"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    candidates = [
        item for item in payload.get("artifacts", {}).get("nextion", [])
        if item.get("path") == filename
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Nextion TFT missing or duplicated in manifest: {filename}")
    artifact = candidates[0]
    size = destination.stat().st_size
    with destination.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    if (artifact.get("size") != size
            or artifact.get("sha256") != sha256
            or artifact.get("version") != args.version
            or artifact.get("display_compatibility") != "NX4832K035_011"
            or artifact.get("target") != "nextion"
            or artifact.get("kind") != "nextion-tft"):
        raise RuntimeError("Nextion manifest entry does not match the published TFT")
    print(f"OK: source={source} (tracked release left untouched)")
    print(f"OK: {destination.relative_to(root)} ({size} bytes)")
    print(f"OK: {manifest.relative_to(root)}; Nextion entry, size and SHA-256 verified")
    # ESP32-S3 has 8 MiB PSRAM, and the Nextion OTA staging policy reserves
    # at least 2 MiB. This bound is optimistic: runtime allocations and
    # fragmentation further reduce the largest contiguous allocation.
    maximum_ota_size = 6 * 1024 * 1024
    if size >= maximum_ota_size:
        print(
            "WARNING: TFT >= 6 MiB; PSRAM-preverified Nextion OTA is "
            "not feasible on the ESP32-S3 with its 2 MiB reserve.",
            file=sys.stderr,
        )
    else:
        print(
            "NOTE: Nextion OTA additionally requires at least TFT size "
            "+ 2 MiB reserve in free PSRAM; staging uses 64 KiB segments."
        )
    print("No ESP32/SPIFFS compile; paired OTA release ZIP remains unchanged.")
    print("If using a separate HTTP server, upload both the TFT and manifest.json there.")


if __name__ == "__main__":
    main()
