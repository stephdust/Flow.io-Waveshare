#!/usr/bin/env python3
"""Block known deprecated Pillow API calls in the Nextion Python pipeline.

Runs before every local and CI HMI/TFT build. Uses AST: mentions in comments,
strings and documentation do not create false positives. Warning logs must
still be inspected for newly deprecated Pillow or dependency APIs.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent

# Common Pillow removals (including Pillow 14's planned getdata removal).
LEGACY_METHODS = {
    "getdata": "Use getpixel() or get_flattened_data() as appropriate.",
    "getsize": "Use font.getbbox()/getlength() as appropriate.",
    "textsize": "Use draw.textbbox()/textlength().",
    "multiline_textsize": "Use draw.multiline_textbbox().",
}
LEGACY_IMAGE_ATTRIBUTES = {
    "ANTIALIAS": "Use Image.Resampling.LANCZOS.",
}


def violations(path: Path) -> list[str]:
    syntax = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    for node in ast.walk(syntax):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            if attr.attr in LEGACY_METHODS:
                errors.append(
                    f"{path.name}:{node.lineno}: .{attr.attr}() — "
                    f"{LEGACY_METHODS[attr.attr]}"
                )
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Image"
            and node.attr in LEGACY_IMAGE_ATTRIBUTES
        ):
            errors.append(
                f"{path.name}:{node.lineno}: Image.{node.attr} — "
                f"{LEGACY_IMAGE_ATTRIBUTES[node.attr]}"
            )
    return errors


def main() -> int:
    scripts = sorted(SCRIPTS.glob("*.py"))
    issues = [error for script in scripts for error in violations(script)]
    if issues:
        print("FAIL: deprecated Pillow APIs in Nextion Python scripts:")
        for error in issues:
            print("  " + error)
        print("Fix the source; never silence DeprecationWarning.")
        return 1
    print(
        f"PASS: {len(scripts)} Nextion Python scripts contain no known "
        "deprecated Pillow API calls"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
