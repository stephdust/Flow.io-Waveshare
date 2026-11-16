#!/usr/bin/env python3
"""
Inject build reference macros into the active PlatformIO environment.

Stable product versions stay in platformio.ini (`custom_version` / `FIRMW`),
while this script appends a build reference generated at compile time.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sys

scripts_dir = str(Path.cwd() / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from version_utils import normalize_config_string

Import("env")  # type: ignore[name-defined]


core_version = normalize_config_string(env.GetProjectOption("custom_version", "0.0.0"))
# Stable by default so consecutive incremental builds reuse compiled objects.
# Set FLOW_BUILD_REF explicitly for release builds, or FLOW_BUILD_TIMESTAMP=1
# to restore the former per-build timestamp behavior.
build_ref = os.getenv("FLOW_BUILD_REF", "").strip()
if not build_ref:
    build_ref = (datetime.now().strftime("%Y%m%d.%H%M%S")
                 if os.getenv("FLOW_BUILD_TIMESTAMP", "0") == "1" else "local")
if not all(c.isalnum() or c in "._-" for c in build_ref):
    raise ValueError("FLOW_BUILD_REF may contain only letters, digits, '.', '_' or '-'")
full_version = f"{core_version}+{build_ref}"

env.Append(
    CPPDEFINES=[
        ("FLOW_BUILD_REF", f'\\"{build_ref}\\"'),
        ("FLOW_FIRMWARE_VERSION_FULL", f'\\"{full_version}\\"'),
    ]
)

print(f"[build-version] core={core_version} build_ref={build_ref} full={full_version}")
