#!/usr/bin/env python3
"""Compile and execute the *production* ConfigMenuModel leaf/browse methods on host.

A mocked ConfigStore advertises physical modules but deliberately cannot
serialize their JSON. A registered leaf must still open on a row tap.
This catches the old hasAttributes/moduleRowCount_ gating regression.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "src/Modules/HMIModule/ConfigMenuModel.cpp").read_text(encoding="utf-8")


def extract(signature: str) -> str:
    pos = src.index(signature)
    begin = src.index("{", pos)
    depth = 0
    for end in range(begin, len(src)):
        if src[end] == "{":
            depth += 1
        elif src[end] == "}":
            depth -= 1
            if depth == 0:
                return src[pos:end + 1]
    raise AssertionError(f"Unclosed production method: {signature}")


production = "\n\n".join(extract(s) for s in (
    "bool ConfigMenuModel::back(",
    "bool ConfigMenuModel::openModule(",
    "bool ConfigMenuModel::enterRow(",
    "bool ConfigMenuModel::editRow(",
    "uint8_t ConfigMenuModel::pageCount(",
    "bool ConfigMenuModel::branchRowAt_(",
    "void ConfigMenuModel::buildHomeView_(",
))

harness = r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <memory>
#include <new>
#include <vector>
#include <string>
#include <algorithm>
struct ConfigStoreService {
    bool (*toJsonModule)(void*, const char*, char*, size_t, bool*) = nullptr;
    size_t (*listModules)(void*, const char**, size_t) = nullptr;
    void* ctx = nullptr;
};
namespace HmiConfigPaths {
inline bool copyPath(const char* from,char* to,size_t n) {
    return from && to && snprintf(to,n,"%s",from)>=0 && strlen(from)<n;
}
inline bool isVirtualBranch(const char* path) {
    return strcmp(path,"network")==0 || strcmp(path,"network/modbus-tcp")==0;
}
inline size_t virtualChildCount(const char* path) {
    if(strcmp(path,"network")==0) return 4;
    if(strcmp(path,"network/modbus-tcp")==0) return 3;
    return 0;
}
inline bool toStore(const char* path,char* out,size_t n) {
    return !isVirtualBranch(path) && copyPath(path,out,n);
}
inline bool toDisplay(const char* path,char* out,size_t n) {
    return copyPath(path,out,n);
}
}
static bool startsWithBranch_(const char* path,const char* branch) {
    size_t n=strlen(branch);
    return strncmp(path,branch,n)==0 && path[n]=='/';
}
static void copyStr_(char* out,size_t n,const char* s) {
    snprintf(out,n,"%s",s?s:"");
}
enum class ConfigMenuMode : uint8_t { Browse, Edit };
enum class ConfigMenuWidget : uint8_t { Text, Switch, Select, Slider };
struct ConfigMenuRowView {
    bool visible=false,valueVisible=false,editable=false,dirty=false;
    bool canEnter=false,canEdit=false;
    ConfigMenuWidget widget=ConfigMenuWidget::Text;
    uint8_t editType=0;
    char key[64]{},label[28]{},value[40]{};
};
struct ConfigMenuView {
    uint8_t pageIndex=0,pageCount=1,rowCountOnPage=0;
    ConfigMenuRowView rows[6]{};
};
struct ConfigMenuModel {
    static constexpr uint8_t RowsPerPage=6,MaxRows=64;
    static constexpr size_t PathCapacity=64,MaxModules=128;
    struct BranchPath {char path[PathCapacity]{};};
    const ConfigStoreService* cfgSvc_=nullptr;
    ConfigMenuMode mode_=ConfigMenuMode::Browse;
    uint8_t pageIndex_=0,editReturnPageIndex_=0;
    char currentModule_[PathCapacity]{},previousModule_[PathCapacity]{};
    bool isHome() const {return currentModule_[0]=='\0';}
    bool back();
    bool openModule(const char* module);
    bool enterRow(uint8_t rowOnPage);
    bool editRow(uint8_t rowOnPage);
    uint8_t pageCount() const;
    uint8_t branchRowCount_(const char* branch) const;
    uint8_t currentRowCount_() const;
    uint8_t collectBranchPaths_(const char* branch,BranchPath* out) const;
    bool branchRowAt_(const char* branch,uint8_t index,char* fullPath,
        size_t fullPathLen,char* label,size_t labelLen,
        bool& hasChildren,bool& hasModule) const;
    bool moduleExists_(const char* path) const;
    bool moduleHasChildren_(const char* path) const;
    bool decorateBranchLabel_(const char* path,const char* child,
        char* label,size_t max) const;
    void buildHomeView_(ConfigMenuView& out) const;
};
static const std::vector<std::string> modules = {
  "network/ethernet", "network/mqtt", "network/time",
  "network/modbus-tcp/502", "network/modbus-tcp/503", "network/modbus-tcp/504"
};
bool ConfigMenuModel::moduleExists_(const char* path) const {
    return std::find(modules.begin(),modules.end(),std::string(path))!=modules.end();
}
bool ConfigMenuModel::moduleHasChildren_(const char* path) const {
    return strcmp(path,"network")==0 || strcmp(path,"network/modbus-tcp")==0;
}
uint8_t ConfigMenuModel::collectBranchPaths_(const char* branch,BranchPath* out) const {
    std::vector<std::string> children;
    if(strcmp(branch,"")==0) children={"network"};
    else if(strcmp(branch,"network")==0)
        children={"network/ethernet","network/modbus-tcp","network/mqtt",
                  "network/time"};
    else if(strcmp(branch,"network/modbus-tcp")==0)
        children={"network/modbus-tcp/502","network/modbus-tcp/503",
                  "network/modbus-tcp/504"};
    for(size_t i=0;i<children.size();++i)
        copyStr_(out[i].path,PathCapacity,children[i].c_str());
    return (uint8_t)children.size();
}
uint8_t ConfigMenuModel::branchRowCount_(const char* branch) const {
    BranchPath paths[MaxRows]{};
    return collectBranchPaths_(branch,paths);
}
uint8_t ConfigMenuModel::currentRowCount_() const {
    return mode_==ConfigMenuMode::Browse ? branchRowCount_(currentModule_):2;
}
bool ConfigMenuModel::decorateBranchLabel_(const char*,const char* child,
                                          char* label,size_t max) const {
    copyStr_(label,max,child);return true;
}
// ACTUAL PRODUCTION METHODS BELOW
int main() {
    struct Counters { unsigned reads=0, listings=0; } counters;
    ConfigStoreService svc{};
    svc.ctx=&counters;
    svc.toJsonModule=[](void* context,const char*,char*,size_t,bool*)->bool {
        ++static_cast<Counters*>(context)->reads;
        return false; // snapshot unavailable, module still exists
    };
    svc.listModules=[](void* context,const char** out,size_t max)->size_t {
        ++static_cast<Counters*>(context)->listings;
        const size_t count=std::min(modules.size(),max);
        for(size_t i=0;i<count;i++) out[i]=modules[i].c_str();
        return count;
    };
    ConfigMenuModel model{};
    model.cfgSvc_=&svc;
    assert(model.enterRow(0)); // root -> network directory
    ConfigMenuView network{};
    model.buildHomeView_(network);
    assert(network.rows[0].visible && network.rows[0].canEdit);
    assert(!network.rows[0].canEnter); // physical ethernet leaf
    assert(!network.rows[0].valueVisible);
    assert(network.rows[1].visible && network.rows[1].canEnter);
    assert(!network.rows[1].canEdit); // virtual modbus-tcp folder
    assert(!model.enterRow(0)); // not a subdirectory
    assert(model.editRow(0)); // still opens ethernet leaf
    assert(model.mode_==ConfigMenuMode::Edit);
    assert(strcmp(model.currentModule_,"network/ethernet")==0);
    assert(model.back()); // returns to network browse mode
    assert(model.mode_==ConfigMenuMode::Browse);
    assert(strcmp(model.currentModule_,"network")==0);
    assert(model.editRow(2)); // MQTT is a real leaf
    assert(strcmp(model.currentModule_,"network/mqtt")==0);
    assert(model.back());
    assert(model.enterRow(1)); // modbus-tcp directory
    ConfigMenuView modbus{};
    model.buildHomeView_(modbus);
    for(unsigned i=0;i<3;i++) {
        assert(modbus.rows[i].visible && modbus.rows[i].canEdit);
        assert(!modbus.rows[i].canEnter);
    }
    assert(model.editRow(0)); // leaf 502 opens
    assert(strcmp(model.currentModule_,"network/modbus-tcp/502")==0);
    assert(model.back());
    assert(model.mode_==ConfigMenuMode::Browse);
    assert(counters.reads==0); // browse/enter must never pre-read JSON
    assert(counters.listings==2); // one listing per Browse page (network and modbus)
    puts("PASS: real C++ ConfigMenuModel opens physical leaves despite unavailable JSON; virtual folder remains Browse");
}
"""
# Replace the marker *after* verifying extraction contains the expected behaviors.
assert "vr.canEdit = hasModule;" in production
assert "if (!hasModule) return false;" in production
harness = harness.replace("// ACTUAL PRODUCTION METHODS BELOW", production)
with tempfile.TemporaryDirectory(prefix="flowio-hmi-leaves-") as folder:
    folder = Path(folder)
    source = folder / "leaf_test.cpp"
    binary = folder / "leaf_test"
    source.write_text(harness, encoding="utf-8")
    subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
