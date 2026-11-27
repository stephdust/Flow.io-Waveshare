#!/usr/bin/env python3
"""Static compatibility gate for the Flow.io ESP32 -> Nextion RSSI protocol.

The actual ESP32 firmware is compiled in the separate firmware workflow.
These checks ensure old Nextion bit positions and pump/touch semantics stay intact.
"""
from pathlib import Path
import re
import tomllib

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:(ROOT/p).read_text(encoding="utf-8")
wifi_header=read("src/Core/Services/IWifi.h")
wifi_impl=read("src/Modules/Network/WifiModule/WifiModule.cpp")
wifi_module=read("src/Modules/Network/WifiModule/WifiModule.h")
hmi=read("src/Modules/HMIModule/HMIModule.cpp")
home=read("nextion/tests/NX4832K035_011/7.0.0/source/pages/pageHome.nx")
page=tomllib.loads(read("nextion/tests/NX4832K035_011/7.0.0/source/pages/pageHome.page.toml"))
art=read("nextion/scripts/render_nx_home.py")

def required(token,source):
    assert token in source, "missing contract: "+token

required("int32_t (*getRssi)(void* ctx);",wifi_header)
required("ServiceBinding::bind<&WifiModule::getRssi_>",wifi_module)
required("WiFi.RSSI()",wifi_impl)
required("kHomeWifiRssiLevelShift = 16U",hmi)
required("bits |= ((uint32_t)level << kHomeWifiRssiLevelShift)",hmi)
required("1UL << HMI_HOME_STATE_WIFI_READY",hmi)
required("1UL << HMI_HOME_STATE_MQTT_READY",hmi)
assert "kHomePeriodicRefreshPeriodMs = 10000U" in hmi
assert re.search(r"rssi <= -85.*return 1U;",hmi)
assert re.search(r"rssi <= -76.*return 2U;",hmi)
assert re.search(r"rssi <= -68.*return 3U;",hmi)
assert re.search(r"return 4U;",hmi)
assert "sys0=globals.vaStates.val/65536" in home
assert "sys0=sys0%8" in home
assert "xpic 428,11,43,38,0,sys1,HomeGaugepic" in home
assert "WIFI_ATLAS_Y=970" in art and "WIFI_LEVELS=5" in art
assert "def wifi_frame(bg,level):" in art
assert "vis tWifiState,0" in home

components=page["component"]
assert components[-1]["name"]=="vaPrvWifiLevel", "must append to preserve old Nextion component IDs"
assert components[-1]["val"]==-1
names=[item["name"] for item in components]
for preserved in ("tWifiState","tProp","tmAnim","b0","b1","m0","m1",
                  "tpH","tORP","bUpdateGauge","tErrMessage"):
    assert names.count(preserved)==1,preserved
assert "wup=1" in home and "wup=255" in home
assert "on tmAnim.timer:" in home and "temp1=globals.vaStates.val>>0" in home
# Match user-visible thresholds, preserving 0=offline.
def level(rssi):
    if rssi<=-127:return 0
    if rssi<=-85:return 1
    if rssi<=-76:return 2
    if rssi<=-68:return 3
    return 4
for rssi,expected in [(-127,0),(-100,1),(-85,1),(-84,2),(-76,2),
                      (-75,3),(-68,3),(-67,4),(-40,4)]:
    assert level(rssi)==expected,(rssi,expected)
print("PASS: real WiFi RSSI 0..4, legacy Home bits unchanged, 10s updates")
print("PASS: 5 colored Nextion Wi-Fi sprites; touch IDs / pump timer preserved")
