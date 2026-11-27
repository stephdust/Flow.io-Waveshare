"""PlatformIO-only entry point for the NX4832K035 Nextion 7.0.0 pipeline.

Registered only by [env:nextion]. Neither custom target depends on an
ESP32/SPIFFS build. Default target 'nextion' compiles HMI/TFT and refreshes
binary/manifest.json; target 'manifest' just refreshes TFT+manifest.
"""
Import("env")

from pathlib import Path
import subprocess
import sys

project_dir = Path(env.subst("$PROJECT_DIR")).resolve()
runner = project_dir / "nextion" / "scripts" / "run_nextion.py"


def _invoke(mode):
    def action(source, target, env):
        print(f"[NEXTION] mode={mode}; ESP32/SPIFFS build disabled")
        subprocess.run(
            [sys.executable, str(runner), mode],
            cwd=str(project_dir),
            check=True,
        )
    return action


env.AddCustomTarget(
    name="nextion",
    dependencies=None,
    actions=_invoke("compile"),
    title="Nextion HMI + TFT",
    description="Compile only NX4832K035 HMI/TFT with pinned nxwright; refresh binary/manifest.json",
)
env.AddCustomTarget(
    name="manifest",
    dependencies=None,
    actions=_invoke("manifest"),
    title="Nextion manifest",
    description="Quickly copy the existing 7.0.0 Nextion TFT and regenerate binary/manifest.json",
)
