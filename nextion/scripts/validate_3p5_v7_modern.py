#!/usr/bin/env python3
"""Verify modern 7.0.0 NX4832K035 HMI changes ONLY Home and its image resources.

Compared with the archived, field-tested 7.0.0 HMI.
Independent of Nextion Editor; editor compile / physical update remain required.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path
from build_3p5_v7_modern import component_slices, crc_page, directory

EXPECTED_MUTATED = {'19.pa', '36.i', '4.i', '8.i', '28.i', '29.i', '26.i'}
PICTURES = {'36.i', '4.i', '8.i', '28.i', '29.i', '26.i'}


def region(data: bytes, entry):
    _, start, size = entry
    assert 0 < size and start + size <= len(data)
    return data[start:start + size]


def dimensions(data: bytes, entry):
    item = region(data, entry)
    assert item[:4] == bytes((0x0B, 0x64, 0x01, 0x00))
    return struct.unpack_from('<HH', item, 12)


def check(original: bytes, modern: bytes):
    old = directory(original)
    new = directory(modern)
    assert set(old) == set(new), 'Live resource directory changed names'
    assert old.keys() == new.keys(), 'Live resource order changed'
    changed = set()
    for name in old:
        prev = region(original, old[name])
        cur = region(modern, new[name])
        if prev != cur:
            changed.add(name)
        if name.endswith('.pa'):
            assert crc_page(prev) == struct.unpack_from('<I', prev)[0], f'original page CRC {name}'
            assert crc_page(cur) == struct.unpack_from('<I', cur)[0], f'modern page CRC {name}'
            if name != '19.pa':
                assert prev == cur, f'unexpected modifications to page {name}'
            else:
                assert len(component_slices(prev)) == len(component_slices(cur)), 'Home component count changed'
                assert prev[24:40].split(bytes((0,)))[0] == cur[24:40].split(bytes((0,)))[0] == b'pageHome'
                assert b'xpic 0,0,480,320,0,150,HomeGaugepic' in cur
    assert changed == EXPECTED_MUTATED, f'Unexpected resource changes: {changed ^ EXPECTED_MUTATED}'
    assert dimensions(original, old['36.i']) == (1035, 150)
    assert dimensions(modern, new['36.i']) == (1035, 470)
    for name in PICTURES - {'36.i'}:
        assert dimensions(original, old[name]) == dimensions(modern, new[name]), f'changed icon dimensions {name}'
    assert region(original, old['5.pa']) == region(modern, new['5.pa']), '7.0.0 version stamp changed'
    assert region(original, old['main.HMI']) == region(modern, new['main.HMI']), 'model / manifest changed'
    assert b'7.0.0' in region(modern, new['5.pa'])
    print('PASS: 7.0.0 retained; all page CRCs, mirrored directories, original navigation/manifest intact')
    print('PASS: only NX4832K035 Home (19.pa) and six picture resources modified')
    print('NOTE: Nextion Editor load/compile and screen tests still required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--modern', type=Path, required=True)
    args = parser.parse_args()
    check(args.original.read_bytes(), args.modern.read_bytes())


if __name__ == '__main__':
    main()
