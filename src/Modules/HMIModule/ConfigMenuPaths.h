#pragma once
/**
 * @brief Bidirectional Nextion ConfigStore display paths.
 * Matches the Web UI's cfg_tree_aliases. The new physical Modbus TCP
 * modules pass through unchanged. Used by all supported Nextion sizes.
 */
#include <ctype.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace HmiConfigPaths {

struct Alias { const char* store; const char* display; };
static constexpr Alias kAliases[] = {
    {"wifi", "network/wifi"},
    {"ethernet", "network/ethernet"},
    {"time", "network/time"},
    {"mqtt", "network/mqtt"},
    {"tft/s3", "hmi/tft"}
};

inline bool copyPath(const char* path, char* out, size_t capacity)
{
    if (!path || !out || capacity == 0U) return false;
    const int n = snprintf(out, capacity, "%s", path);
    return n >= 0 && (size_t)n < capacity;
}

inline bool replacePrefix(const char* path, const char* from, const char* to,
                          char* out, size_t capacity)
{
    const size_t n = strlen(from);
    if (strncmp(path, from, n) != 0 ||
        (path[n] != '\0' && path[n] != '/')) return false;
    const int written = snprintf(out, capacity, "%s%s", to, path + n);
    return written >= 0 && (size_t)written < capacity;
}

inline bool ioRef(const char* suffix, char first)
{
    return suffix && suffix[0] == first &&
           isdigit((unsigned char)suffix[1]) &&
           isdigit((unsigned char)suffix[2]) &&
           (suffix[3] == '\0' || suffix[3] == '/');
}

inline bool toDisplay(const char* store, char* out, size_t capacity)
{
    if (!store || !out || capacity == 0U) return false;
    if (strncmp(store, "io/input/", 9U) == 0) {
        const char* suffix = store + 9U;
        if (ioRef(suffix, 'a')) {
            const int n = snprintf(out, capacity, "io/input/analog/%s", suffix);
            return n >= 0 && (size_t)n < capacity;
        }
        if (ioRef(suffix, 'i')) {
            const int n = snprintf(out, capacity, "io/input/digital/%s", suffix);
            return n >= 0 && (size_t)n < capacity;
        }
    }
    for (const Alias& alias : kAliases) {
        if (replacePrefix(store, alias.store, alias.display, out, capacity))
            return true;
    }
    return copyPath(store, out, capacity);
}

inline bool toStore(const char* display, char* out, size_t capacity)
{
    if (!display || !out || capacity == 0U) return false;
    static constexpr char kAnalog[] = "io/input/analog/";
    static constexpr char kDigital[] = "io/input/digital/";
    if (strncmp(display, kAnalog, sizeof(kAnalog) - 1U) == 0 &&
        ioRef(display + sizeof(kAnalog) - 1U, 'a')) {
        const int n = snprintf(out, capacity, "io/input/%s",
                               display + sizeof(kAnalog) - 1U);
        return n >= 0 && (size_t)n < capacity;
    }
    if (strncmp(display, kDigital, sizeof(kDigital) - 1U) == 0 &&
        ioRef(display + sizeof(kDigital) - 1U, 'i')) {
        const int n = snprintf(out, capacity, "io/input/%s",
                               display + sizeof(kDigital) - 1U);
        return n >= 0 && (size_t)n < capacity;
    }
    for (const Alias& alias : kAliases) {
        if (replacePrefix(display, alias.display, alias.store, out, capacity))
            return true;
    }
    return copyPath(display, out, capacity);
}

} // namespace HmiConfigPaths
