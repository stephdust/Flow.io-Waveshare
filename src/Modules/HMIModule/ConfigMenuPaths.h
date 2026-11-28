#pragma once
/**
 * @brief Flow.io ConfigStore Web and Nextion share ONE metadata hierarchy.
 *
 * The generated arrays below come exclusively from the Web's resolved
 * cfg_tree_aliases and cfg_tree_virtual_branches.  DO NOT add manual
 * mapping rules here. Applies to every Nextion panel via ConfigMenuModel.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace HmiConfigPaths {

struct Alias {
    const char* store;
    const char* display;
};

struct VirtualBranch {
    const char* display;
    size_t firstChild;
    size_t childCount;
};

#include "ConfigMenuPaths_Generated.h"

inline bool copyPath(const char* path, char* out, size_t capacity)
{
    if (!path || !out || capacity == 0U) return false;
    const int written = snprintf(out, capacity, "%s", path);
    return written >= 0 && (size_t)written < capacity;
}

inline bool pathHasPrefix(const char* path, const char* prefix)
{
    if (!path || !prefix) return false;
    const size_t length = strlen(prefix);
    return strncmp(path, prefix, length) == 0 &&
           (path[length] == '\0' || path[length] == '/');
}

inline bool replacePrefix(const char* path, const char* from, const char* to,
                          char* out, size_t capacity)
{
    if (!pathHasPrefix(path, from) || !to || !out || capacity == 0U)
        return false;
    const int written = snprintf(out, capacity, "%s%s", to, path + strlen(from));
    return written >= 0 && (size_t)written < capacity;
}

inline const VirtualBranch* findVirtualBranch(const char* path)
{
    if (!path) return nullptr;
    for (const VirtualBranch& entry : kVirtualBranches) {
        if (strcmp(entry.display, path) == 0) return &entry;
    }
    return nullptr;
}

inline bool isVirtualBranch(const char* path)
{
    return findVirtualBranch(path) != nullptr;
}

inline size_t virtualChildCount(const char* path)
{
    const VirtualBranch* branch = findVirtualBranch(path);
    return branch ? branch->childCount : 0U;
}

inline bool virtualChildAt(const char* path, size_t index,
                           char* out, size_t capacity)
{
    const VirtualBranch* branch = findVirtualBranch(path);
    if (!branch || index >= branch->childCount) return false;
    return copyPath(kVirtualChildren[branch->firstChild + index], out, capacity);
}

inline bool toDisplay(const char* store, char* out, size_t capacity)
{
    if (!store || !out || capacity == 0U) return false;
    const Alias* selected = nullptr;
    for (const Alias& alias : kAliases) {
        if (!pathHasPrefix(store, alias.store)) continue;
        if (!selected || strlen(alias.store) > strlen(selected->store))
            selected = &alias;
    }
    return selected
        ? replacePrefix(store, selected->store, selected->display, out, capacity)
        : copyPath(store, out, capacity);
}

inline bool toStore(const char* display, char* out, size_t capacity)
{
    if (!display || !out || capacity == 0U) return false;
    // A folder declared as virtual in the Web UI cannot be edited as a
    // real ConfigStore module; its registered children remain editable.
    if (isVirtualBranch(display)) return false;
    const Alias* selected = nullptr;
    for (const Alias& alias : kAliases) {
        if (!pathHasPrefix(display, alias.display)) continue;
        if (!selected || strlen(alias.display) > strlen(selected->display))
            selected = &alias;
    }
    return selected
        ? replacePrefix(display, selected->display, selected->store, out, capacity)
        : copyPath(display, out, capacity);
}

} // namespace HmiConfigPaths
