#!/usr/bin/env python3
"""Read-only NX4832K035_011 HMI 7.0.0 nxwright compatibility and round-trip audit."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile
import time

NXWRIGHT_COMMIT = "e9443a409cc9deb866db7486854fa962d382accc"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def execute(argv: list[str], log: Path, timeout: int = 180) -> int:
    begin = time.monotonic()
    try:
        process = subprocess.run(
            argv, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, errors="replace", timeout=timeout, check=False,
        )
        result = process.returncode
        content = process.stdout + "\n" + process.stderr
    except subprocess.TimeoutExpired as problem:
        result = 124
        out = problem.stdout or b""
        content = (out.decode("utf-8", "replace") if isinstance(out, bytes) else out)
        content += "\nTIMEOUT at %d seconds" % timeout
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("$ " + " ".join(argv) + "\n" + content[:250000] +
                   "\nExit: %d; time: %.1f seconds\n" %
                   (result, time.monotonic() - begin), encoding="utf-8")
    print("%s: exit=%d" % (log, result), flush=True)
    return result


def unknown_groups(path: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(item, dict):
            counts[str(item.get("sort", "unknown"))] += 1
        elif isinstance(item, list):
            counts.update(str(d.get("sort", "unknown")) for d in item if isinstance(d, dict))
    return dict(counts)


def inspect(label: str, original: Path, out: Path) -> tuple[dict, bool]:
    folder = out / label
    folder.mkdir(parents=True, exist_ok=True)
    fingerprint = sha256(original)
    steps: dict[str, int | None] = {s: None for s in
                                  ("unknown", "extract", "check", "build", "diff", "report")}
    rebuilt_hash: str | None = None
    with tempfile.TemporaryDirectory(prefix="nxwright-hmi-" + label) as scratch:
        source_dir = Path(scratch) / "source"
        steps["unknown"] = execute(
            ["nxwright", "extract", "--list-unknown", str(original)],
            folder / "unknown.log", 180)
        unknown = unknown_groups(folder / "unknown.log")
        steps["extract"] = execute(
            ["nxwright", "extract", str(original), str(source_dir)],
            folder / "extract.log", 240)
        if steps["extract"] == 0:
            steps["check"] = execute(
                ["nxwright", "check", str(source_dir)], folder / "check.log", 240)
            if steps["check"] == 0:
                rebuilt = Path(scratch) / "rebuilt.HMI"
                steps["build"] = execute(
                    ["nxwright", "build", str(source_dir), str(rebuilt), "--no-lock"],
                    folder / "build.log", 300)
                if steps["build"] == 0 and rebuilt.is_file():
                    rebuilt_hash = sha256(rebuilt)
                    steps["diff"] = execute(
                        ["nxwright", "diff", str(source_dir), str(rebuilt), "--no-lock"],
                        folder / "diff.log", 180)
        # Read-only format analysis, with a description of any changed blocks.
        steps["report"] = execute(
            ["nxwright", "report", str(original), str(folder / "compatibility.md")],
            folder / "report.log", 300)

    if sha256(original) != fingerprint:
        raise RuntimeError("nxwright modified input HMI: " + label)
    record = {
        "source": label, "input_sha256": fingerprint, "input_size": original.stat().st_size,
        "unknown_groups": unknown, "steps": steps, "roundtrip_sha256": rebuilt_hash,
        "byte_identical": (fingerprint == rebuilt_hash) if rebuilt_hash else None,
    }
    (folder / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    compatible = all(steps[s] == 0 for s in ("unknown", "extract", "check", "build"))
    return record, compatible


def result_label(rc: int | None) -> str:
    return "—" if rc is None else ("OK" if rc == 0 else "FAIL (%d)" % rc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for path in (args.baseline, args.current):
        if not path.is_file() or path.suffix.upper() != ".HMI":
            parser.error("NX4832K035 HMI missing: %s" % path)

    results = []
    statuses = []
    for label, hmi in (("saved-working-7.0.0", args.baseline),
                       ("modern-dev-7.0.0", args.current)):
        record, ok = inspect(label, hmi.resolve(), args.output)
        results.append(record)
        statuses.append(ok)

    lines = [
        "# Nextion NX4832K035_011 / nxwright compatibility audit",
        "",
        "**DIAGNOSTIC ONLY:** no TFT compiled or uploaded, no production changes.",
        "The 5-inch/7-inch sources and binaries were not used.",
        "",
        "nxwright version: %s; pinned commit: %s" %
        (importlib.metadata.version("nxwright"), NXWRIGHT_COMMIT),
        "",
        "| HMI source | Unknown scan | Extract | Check | Build | Diff |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        s = r["steps"]
        lines.append("| %s | %s | %s | %s | %s | %s |" %
                     (r["source"], result_label(s["unknown"]),
                      result_label(s["extract"]), result_label(s["check"]),
                      result_label(s["build"]), result_label(s["diff"])))
        lines.append("")
        lines.append("%s: SHA256 %s; unknown groups: %s; rebuilt SHA256: %s; "
                     "byte-identical: %s" %
                     (r["source"], r["input_sha256"], r["unknown_groups"],
                      r["roundtrip_sha256"], r["byte_identical"]))
    lines += [
        "", "A successful rebuild does not prove Nextion Editor or hardware compatibility.",
        "Inspect each compatibility.md, .log and result.json before any change to the build.",
        "", "**Overall:** " + ("both sources passed extraction and reconstruction"
                                 if all(statuses) else "further compatibility work required"),
    ]
    summary = "\n".join(lines) + "\n"
    (args.output / "SUMMARY.md").write_text(summary, encoding="utf-8")
    print(summary, flush=True)
    return 0 if all(statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
