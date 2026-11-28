#pragma once
/**
 * @brief Compact a Nextion breadcrumb for the legacy 24-byte UDP title.
 *
 * The UDP wire format stays at v7 so deployed FlowConnectDisplay firmwares
 * continue to accept snapshots.  Paths are used only for display here:
 * navigation and edits are resolved entirely in the authoritative Flow.io
 * ConfigMenuModel via event row/contextRef, not by this shortened title.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace HmiUdpConfigTitle {

inline void format(char* out, size_t capacity, const char* breadcrumb)
{
    if (!out || capacity == 0U) return;
    out[0] = '\0';
    if (!breadcrumb) return;

    const char* source = breadcrumb;
    if (strncmp(source, "config > ", 9U) == 0)
        source += 9U;

    char normalized[96]{};
    size_t count = 0U;
    while (*source != '\0' && count + 1U < sizeof(normalized)) {
        if (strncmp(source, " [EDIT]", 7U) == 0 && source[7] == '\0')
            break; // edit status travels in the snapshot mode field.
        if (strncmp(source, " > ", 3U) == 0) {
            normalized[count++] = '/';
            source += 3U;
        } else {
            normalized[count++] = *source++;
        }
    }
    normalized[count] = '\0';

    if (count < capacity) {
        (void)snprintf(out, capacity, "%s", normalized);
        return;
    }

    // Prefer a complete rightmost subtree, rather than a useless "config > net".
    const char* suffix = normalized;
    while (strlen(suffix) + 4U > capacity) {
        const char* slash = strchr(suffix, '/');
        if (!slash) break;
        suffix = slash + 1U;
    }
    if (suffix != normalized && strlen(suffix) + 4U <= capacity) {
        (void)snprintf(out, capacity, ".../%s", suffix);
        return;
    }

    // One exceptionally long node: preserve its identifying end.
    if (capacity > 4U)
        (void)snprintf(out, capacity, "...%s", normalized + count - (capacity - 4U));
    else
        (void)snprintf(out, capacity, "%s", normalized + count - (capacity - 1U));
}

}  // namespace HmiUdpConfigTitle
