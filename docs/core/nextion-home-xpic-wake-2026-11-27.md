# Nextion Enhanced 480×320 — HomeSimple xpic wake redraw

## Root cause (6.0.0 HMI)

The supplied `Flowio_Enhanced_480x320.HMI` contains a HomeSimple timer
which paints the two 207×150 gauge pictures only when their percentage changes:

```nextion
if(vapHPercent.val!=vaPrvpHPercen.val)
{
  vaPrvpHPercen.val=vapHPercent.val
  // ...
  xpic 20,89,207,150,sys1,0,HomeGaugepic
}
if(vaOrpPercent.val!=vaPrvOrpPercen.val)
{
  vaPrvOrpPercen.val=vaOrpPercent.val
  // ...
  xpic 253,89,207,150,sys1,0,HomeGaugepic
}
```

With `wup=255`, a wake may refresh Nextion components without invalidating
`vaPrvpHPercen` or `vaPrvOrpPercen`. The timer then skips both `xpic`
operations when pH/ORP values remain unchanged.

## ESP-side hotfix

The driver now sends the following commands **only when the known active page
is the primary Home page (ID 0)**:

```nextion
vaPrvpHPercen.val=65535
vaPrvOrpPercen.val=65535
```

Commands are sent after the Nextion `0x87` automatic wake event, and also
after a `sleep=0` wake initiated by Flow.io/PIR (which does **not** emit
`0x87`). Nextion's existing timer then paints its graphical arcs using the
real percentage values already supplied by Flow.io. This does not change pH
or ORP measurements, setpoints, serial protocol, the TFT upgrade flow,
or other Nextion pages.

The existing full Home data publish remains in place after wake.

## Nextion Editor follow-up

When compiling a new HomeSimple HMI version, it is preferable to also reset
these cache variables from the page initialization/wake path, preserving the
redraw logic across standalone Nextion use without ESP assistance.

For the approved visual redesign, import new 480×320 assets in Nextion Editor
and keep the exact live object and event names. The RGB Wi-Fi strength bars
require **new explicit HMI components** and an ESP-to-Nextion RSSI level
binding; currently `globals.vaStates` bit 7 only tells whether Wi-Fi is
connected, **not** how strong its signal is. Do not silently reinterpret that
binary bit as RSSI, and do not issue commands to nonexistent Nextion objects.

A compiled `.tft` image and the source `.HMI` are required for an actual
display-side UI update; a PNG mockup alone is not flashable as an HMI.

## Regression / hardware trial

The host UART test `test/host/nextion_page_events.cpp` covers:
- 0x87 automatic wake on HomeSimple;
- `sleep=0` programmatic/PIR wake without 0x87;
- no writes while sleeping;
- no HomeSimple cache commands on settings or HomeSwtch pages.

Before merging, compile the ESP project, test both wake paths on the
NX4832K035_011, and verify that the two gauge arcs reappear without waiting
for a measurement change.
