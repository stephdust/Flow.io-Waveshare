// Host-side regression test: g++ -std=c++17 -Isrc
// scripts/tests/test_nextion_segmented_psram.cpp -o /tmp/test-nextion-psram
// && /tmp/test-nextion-psram
#include "Core/OtaPsramPolicy.h"

#include <cassert>
#include <cstdio>

int main()
{
    constexpr size_t KiB = 1024U;
    constexpr size_t MiB = 1024U * KiB;
    constexpr size_t kChunk = 64U * KiB;

    // Realistic TFT size: enough aggregate PSRAM but no multi-MiB block.
    const size_t tft = 3952708U;
    assert(!OtaPsramPolicy::canStageImage(tft, 7U * MiB, 128U * KiB));
    assert(OtaPsramPolicy::canStageSegmentedImage(
        tft, 7U * MiB, 128U * KiB, kChunk));

    // Smaller packed TFT should also pass a fragmented 5.5 MiB free heap.
    assert(OtaPsramPolicy::canStageSegmentedImage(
        3U * MiB, 5632U * KiB, 128U * KiB, kChunk));

    // Do not weaken the existing 2 MiB safety reserve.
    assert(!OtaPsramPolicy::canStageSegmentedImage(
        4U * MiB, 5U * MiB, 4U * MiB, kChunk));
    assert(!OtaPsramPolicy::canStageSegmentedImage(
        1U * MiB, 2U * MiB, 1U * MiB, kChunk));

    // Chunk must still be individually allocatable.
    assert(!OtaPsramPolicy::canStageSegmentedImage(
        tft, 7U * MiB, 32U * KiB, kChunk));

    // Handle sizes below one chunk and invalid zero sizes.
    assert(OtaPsramPolicy::canStageSegmentedImage(
        32U * KiB, 3U * MiB, 32U * KiB, kChunk));
    assert(!OtaPsramPolicy::canStageSegmentedImage(
        0U, 7U * MiB, 7U * MiB, kChunk));
    assert(!OtaPsramPolicy::canStageSegmentedImage(
        tft, 7U * MiB, 7U * MiB, 0U));

    std::puts("PASS: segmented Nextion staging keeps the full-image "
              "preverify and 2 MiB PSRAM reserve");
    return 0;
}
