#pragma once
/**
 * @file OtaPsramPolicy.h
 * @brief Memory-only admission policy for experimental remote A/B OTA.
 *
 * No ESP32 dependencies: the policy is host-testable. Only a complete image
 * may be staged, and at least 2 MiB of PSRAM remain available for system
 * services. A contiguous block large enough for the image is mandatory.
 */
#include <stddef.h>

namespace OtaPsramPolicy {

constexpr size_t kReserveBytes = 2U * 1024U * 1024U;

inline bool canStageImage(size_t imageSize, size_t freeBytes,
                          size_t largestFreeBlock)
{
    if (imageSize == 0U || freeBytes <= kReserveBytes) return false;
    return imageSize <= freeBytes - kReserveBytes &&
           imageSize <= largestFreeBlock;
}


/** A fragmented image may still be safely pre-verified in bounded PSRAM chunks.
 *
 * The 2 MiB reserve and full-image pre-stage requirement are unchanged. Only
 * the contiguous-block requirement is reduced to one chunk at a time; each
 * individual allocation is still checked by the caller before any HTTP GET.
 */
inline bool canStageSegmentedImage(size_t imageSize, size_t freeBytes,
                                   size_t largestFreeBlock, size_t chunkBytes)
{
    if (chunkBytes == 0U || imageSize == 0U ||
        freeBytes <= kReserveBytes ||
        imageSize > freeBytes - kReserveBytes) return false;
    const size_t requiredBlock = imageSize < chunkBytes ? imageSize : chunkBytes;
    return largestFreeBlock >= requiredBlock;
}

} // namespace OtaPsramPolicy
