#!/usr/bin/env python3
"""
Inject a reproducible build reference without invalidating PlatformIO's object
cache on every invocation.

The previous wall-clock timestamp changed global CPPDEFINES on every pio run,
forcing a full recompilation even when no source file had changed.
The build number is now the Git first-parent commit count, with the short
commit hash as an unambiguous suffix. It advances on commits, not on pio runs.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

scripts_dir = str(Path.cwd() / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from version_utils import normalize_config_string

Import("env")  # type: ignore[name-defined]


def git_output(*args: str) -> str:
    project_dir = Path(env.subst("$PROJECT_DIR"))
    result = subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout.strip()


core_version = normalize_config_string(env.GetProjectOption("custom_version", "0.0.0"))

try:
    build_number = git_output("rev-list", "--count", "--first-parent", "HEAD")
    commit_short = git_output("rev-parse", "--short=8", "HEAD")
    build_ref = f"{build_number}.g{commit_short}"
except (OSError, subprocess.SubprocessError) as exc:
    # A source archive without .git still builds with a deterministic version.
    build_ref = "0.source"
    print(f"[build-version] Git metadata unavailable ({exc}); using {build_ref}")

full_version = f"{core_version}+{build_ref}"
env.Append(
    CPPDEFINES=[
        ("FLOW_BUILD_REF", f'\\"{build_ref}\\"'),
        ("FLOW_FIRMWARE_VERSION_FULL", f'\\"{full_version}\\"'),
    ]
)

print(f"[build-version] core={core_version} build_ref={build_ref} full={full_version}")
