#!/usr/bin/env bash
# Compile an extracted nxwright source to a TEST-ONLY Nextion TFT.
# This NEVER installs to a device and NEVER publishes a release.
# Requires nxwright pinned on the caller's environment; uses official Editor 1.68.2 firmware.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash nextion/scripts/compile_nxwright_test.sh <extracted-app-dir> <...TEST-ONLY.tft>" >&2
  exit 2
fi
app_dir="$1"
out_tft="$2"

if [[ ! -f "$app_dir/app.toml" || ! -f "$app_dir/pages/pageHome.nx" ]]; then
  echo "ERROR: expected an extracted NX4832K035 source folder" >&2
  exit 2
fi
if ! grep -Eq '^screen = "NX4832K035"$' "$app_dir/app.toml"; then
  echo "ERROR: only NX4832K035 is allowed; 5-inch/7-inch are out of scope" >&2
  exit 2
fi
if ! grep -Eq '^rotation = 90$' "$app_dir/app.toml"; then
  echo "ERROR: unexpected display rotation; must be 90 degrees" >&2
  exit 2
fi
if [[ "$(basename "$out_tft")" != *TEST-ONLY.tft ]]; then
  echo "ERROR: output must end in TEST-ONLY.tft to prevent production release confusion" >&2
  exit 2
fi
if [[ -f "$out_tft" ]]; then
  echo "ERROR: refusing to overwrite an existing TFT: $out_tft" >&2
  exit 2
fi
case "$out_tft" in
  */nextion/releases/*|nextion/releases/*|*/binary/*|binary/*)
    echo "ERROR: output may not be written into a release or PlatformIO binary directory" >&2
    exit 2;;
esac

nxwright check "$app_dir"
# 6.0.0 archived TFT was made by Editor 1.68.1; nxwright requires 1.68.2.
# --download explicitly opts in to fetching the official matching Editor firmware,
# only on the caller's machine / isolated CI runner.
nxwright compile "$app_dir" "$out_tft" --download
test -s "$out_tft"
nxwright tft-read "$out_tft"
sha256sum "$out_tft"
echo "NX4832K035 TFT compiled and parsed; validation on physical Nextion still required."
