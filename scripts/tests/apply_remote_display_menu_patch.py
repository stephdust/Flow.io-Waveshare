#!/usr/bin/env python3
"""Apply the Flow.io shared-ConfigStore-tree compatibility fix to RemoteDisplay.

This script is kept in Flow.io-Waveshare because GitHub currently exposes
stephdust/Flow.io-RemoteDisplay as read-only to the assistant integration.

It patches the LOCAL checkout of RemoteDisplay, never fetches/pushes/commits.
Use --check to verify whether it is needed, --apply to modify the checkout.
The replacements are deliberately exact and fail if upstream has changed.
"""
from pathlib import Path
import argparse

PATCHES = (
    (
        """    // HMI navigation scripts can change these buttons independently of our
    // visibility cache. Always apply both states, including explicit vis ...,0.
    configVisibilityKnownMask_ &= ~((1UL << 3U) | (1UL << 4U));
    (void)setConfigVisibility_(3U, "bPrev", canPrev);
    (void)sendCmdFmt_("tsw bPrev,%u", canPrev ? 1U : 0U);
    (void)setConfigVisibility_(4U, "bNext", canNext);
    (void)sendCmdFmt_("tsw bNext,%u", canNext ? 1U : 0U);""",
        """    // 7.0.0 has captioned 3D buttons: keep each image visible and disable
    // only its touch region. Older 6.0.0 Nextion screens retain old behavior.
    const bool threeDMenu = versionDetected_ &&
                            strcmp(displayVersion_, "7.0.0") == 0;
    configVisibilityKnownMask_ &= ~((1UL << 3U) | (1UL << 4U));
    (void)setConfigVisibility_(3U, "bPrev", threeDMenu || canPrev);
    (void)sendCmdFmt_("tsw bPrev,%u", canPrev ? 1U : 0U);
    (void)setConfigVisibility_(4U, "bNext", threeDMenu || canNext);
    (void)sendCmdFmt_("tsw bNext,%u", canNext ? 1U : 0U);""",
    ),
    (
        """    (void)sendText_("tPath", view.breadcrumb);
    (void)setConfigVisibility_(0U, "bHome", view.canHome);
    (void)sendCmdFmt_("tsw bHome,%u", view.canHome ? 1U : 0U);
    (void)setConfigVisibility_(1U, "bBack", view.canBack);
    (void)sendCmdFmt_("tsw bBack,%u", view.canBack ? 1U : 0U);
    (void)setConfigVisibility_(2U, "bValid", view.canValidate);
    (void)sendCmdFmt_("tsw bValid,%u", view.canValidate ? 1U : 0U);""",
        """    const bool threeDMenu = versionDetected_ &&
                            strcmp(displayVersion_, "7.0.0") == 0;
    if (threeDMenu) (void)sendCmd_("vis tLoading,0");
    (void)sendText_("tPath", view.breadcrumb);
    // Keep captioned 3D icons visible even while unavailable, but never
    // make an unavailable action touchable. No behavior change for TFT 6.0.0.
    (void)setConfigVisibility_(0U, "bHome", threeDMenu || view.canHome);
    (void)sendCmdFmt_("tsw bHome,%u", view.canHome ? 1U : 0U);
    (void)setConfigVisibility_(1U, "bBack", threeDMenu || view.canBack);
    (void)sendCmdFmt_("tsw bBack,%u", view.canBack ? 1U : 0U);
    (void)setConfigVisibility_(2U, "bValid", threeDMenu || view.canValidate);
    (void)sendCmdFmt_("tsw bValid,%u", view.canValidate ? 1U : 0U);""",
    ),
    (
        """            const bool emitted = handlePageId_(payload[0], true, out);
            if (emitted) {
                out.contextRef = contextRef;
                out.pageId = payload[0];
            }
            return emitted;""",
        """            // Returning from the keyboard can send a PAGE frame for the
            // *same* page with a context. It still needs to restore the
            // authoritative ConfigMenuModel state on Flow.io via UDP.
            const bool restoreContext = contextRef != 0U &&
                                        isMenuPageId_(payload[0]);
            const bool emitted = handlePageId_(payload[0], true, out);
            if (restoreContext) {
                out.type = HmiEventType::ConfigEnter;
                out.pageId = payload[0];
            }
            if (out.type == HmiEventType::ConfigEnter)
                out.contextRef = contextRef;
            return emitted || restoreContext;""",
    ),
)

PATH = "src/Modules/HMIModule/Drivers/NextionDriver.cpp"


def patched_text(original: str) -> tuple[str, bool]:
    # The current RemoteDisplay firmware already includes the old 6.0.0 /
    # 7.0.0 fixes and may now add the full-row 7.0.0 renderer. Do not
    # reapply historical text substitutions to this newer implementation.
    if "const bool fullRowMenu = threeDMenu;" in original:
        required = (
            'setConfigVisibility_(0U, "bHome", threeDMenu || view.canHome)',
            'setConfigVisibility_(1U, "bBack", threeDMenu || view.canBack)',
            'setConfigVisibility_(2U, "bValid", threeDMenu || view.canValidate)',
            'setConfigVisibility_(3U, "bPrev", threeDMenu || canPrev)',
            'setConfigVisibility_(4U, "bNext", threeDMenu || canNext)',
            "const bool restoreContext = contextRef != 0U",
            "out.type = HmiEventType::ConfigEnter;",
            'vaCfgEdit.val=%u',
            "leftTouchable = false;",
        )
        missing = [marker for marker in required if marker not in original]
        if missing:
            raise ValueError(f"{PATH}: incomplete updated remote driver: {missing}")
        return original, False

    updated = original
    changed = False
    for old, new in PATCHES:
        if new in updated:
            continue
        if updated.count(old) != 1:
            raise ValueError(f"{PATH}: expected exactly one matching source block")
        updated = updated.replace(old, new)
        changed = True
    return updated, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-root", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    file = args.remote_root / PATH
    if not file.is_file():
        raise SystemExit(f"RemoteDisplay checkout not found: {file}")
    original = file.read_text(encoding="utf-8")
    updated, changed = patched_text(original)
    if args.check:
        if changed:
            print("PATCH REQUIRED: RemoteDisplay has the old 6.0.0 menu/navigation behavior")
        else:
            print("PASS: RemoteDisplay 6.0.0 and 7.0.0 Nextion navigation already patched")
        return
    if changed:
        file.write_text(updated, encoding="utf-8")
    verified, again = patched_text(file.read_text(encoding="utf-8"))
    assert not again and verified == updated, "patch is not idempotent"
    print("PASS: RemoteDisplay UART 7.0.0 3D menu + 6.0.0 fallback + contextual return")


if __name__ == "__main__":
    main()
