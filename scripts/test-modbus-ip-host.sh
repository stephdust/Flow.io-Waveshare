#!/usr/bin/env bash
# Compile and run the native Modbus IP protocol regression suite without ESP32 hardware.
set -euo pipefail
cd "$(dirname "$0")/.."
CXX="${CXX:-g++}"
OUT_DIR="$(mktemp -d)"
trap 'rm -rf "$OUT_DIR"' EXIT
tests=(
  modbus_ip_foundation
  modbus_ip_profile_resolver
  modbus_ip_profile_persistence
  modbus_ip_register_codec
  modbus_ip_tcp_framer
  modbus_ip_config
  modbus_ip_known_device_profile
  modbus_ip_transaction_bridge
  modbus_ip_ports
)
for test in "${tests[@]}"; do
  echo "[modbus-ip] compiling ${test}"
  "$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic -I src -I include \
    "test/host/${test}.cpp" -o "$OUT_DIR/${test}"
  echo "[modbus-ip] running ${test}"
  "$OUT_DIR/${test}"
done
echo "[modbus-ip] all ${#tests[@]} native tests passed"
