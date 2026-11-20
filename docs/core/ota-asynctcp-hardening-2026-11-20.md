# OTA / AsyncTCP hardening — 2026-11-20

Base: `christophebelmont/Flow.io-Waveshare`, branch `dev`, commit `c94670220cce243943c2bf858e13a2f5b00600c3`.

## Changes

1. **Direct HTTP SPIFFS update disabled.** The old `/fwupdate/spiffs` flow used to erase and overwrite the mounted active SPIFFS partition, potentially leaving the running Web UI unusable after a partial transfer. It now returns an explicit error. For a paired release use the existing local transactional A/B endpoints: `/api/upgrade/manifest`, `/api/upgrade/filesystem`, `/api/upgrade/firmware`, then `/api/upgrade/commit`. This is a deliberate compatibility change; update the Web UI or deployment process to use the A/B release workflow before relying on SPIFFS upgrades.

2. **HTTP / AsyncTCP concurrency reduced during updates.** Authenticated OTA and status endpoints remain available, while other newly arriving HTTP requests receive 503 `OtaBusy` when the firmware-update service reports busy. The Web task suspends SSE event flushing, expensive snapshots and UART log distribution while an update or local release is in progress. Existing TCP/WebSocket connections are not forcibly terminated.

3. **Filesystem clone made cooperative.** Erasure of the inactive SPIFFS slot is broken into aligned 64 KiB operations with a task yield, and copying the filesystem yields periodically. Existing partition validation and failure reporting are retained.

4. **Stack diagnostics.** OTA phase logs include the observed free stack for the `async_tcp` task and flag less than 1024 bytes. A 1536-byte stack-reserve guard is applied to the OTA worker before initiating a remote firmware update.

## Hardware validation required

- Compile the Waveshare target and check `platformio.ini` / partition table against the actual 16 MB flash module.
- Upgrade firmware over HTTP with Wi-Fi or Ethernet while observing serial logs `[OTA]` and both internal-heap and AsyncTCP free-stack metrics.
- Run a local paired A/B upgrade; confirm that failed/incomplete uploads cannot activate the inactive slot.
- Confirm `/fwupdate/spiffs` now rejects with a descriptive error; use the paired A/B workflow for filesystem updates.
- Repeat while the Web UI has several connected clients, with RS485 traffic and MQTT active; confirm no watchdog reset, heap exhaustion or lost control loop deadlines.
- Verify cold and warm reboots and that a power interruption does not make the current active release unbootable.

This change has **not** been compiled or physically tested on an ESP32-S3 by the assistant. It mitigates plausible instability mechanisms but does not establish the original root cause.
