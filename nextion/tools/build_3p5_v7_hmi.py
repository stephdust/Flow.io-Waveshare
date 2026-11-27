#!/usr/bin/env python3
"""Build experimental Nextion NX4832K035_011 HMI v7 from the versioned v6 HMI.

This is not a TFT compiler. The produced HMI must be opened/compiled with Nextion Editor.
"""
from pathlib import Path
import hashlib
import re
import struct
import sys

SOURCE = Path('nextion/releases/6.0.0/Flowio_Enhanced_480x320.HMI')
TARGET = Path('nextion/releases/7.0.0/Flowio_Enhanced_480x320_v7.0.0_TEST.HMI')


def crc(page):
    table = []
    for i in range(256):
        x = i << 24
        for _ in range(8):
            x = ((x << 1) ^ (0x04C11DB7 if x & 0x80000000 else 0)) & 0xffffffff
        table.append(x)
    seed = 0xffffffff
    for part in (page[4:], page[4:8], page[12:16], page[20:21], page[21:22]):
        for v in part:
            seed ^= v
            for _ in range(4):
                seed = ((seed << 8) & 0xffffffff) ^ table[seed >> 24]
    return seed


def pages(b):
    count = struct.unpack_from('<I', b)[0]
    rows = []
    for i in range(count):
        n, start, size, deleted, *_ = struct.unpack_from('<16sIIBBBB', b, 4 + 28 * i)
        rows.append((n.split(b'\0')[0].decode('ascii', 'replace'), start, size, deleted, i))
    assert b[:4 + 28 * count] == b[0x80000:0x80000 + 4 + 28 * count], 'directory mirrors mismatch'
    return count, rows


def replace_page(b, count, entry, page):
    start = len(b)
    b.extend(page)
    for base in (0, 0x80000):
        off = base + 4 + 28 * entry
        struct.pack_into('<II', b, off + 16, start, len(page))
        b[off + 24] = 0
        b[off + 25:off + 28] = (len(page) >> 8).to_bytes(3, 'little')
    assert b[:4 + 28 * count] == b[0x80000:0x80000 + 4 + 28 * count]
    assert crc(page) == struct.unpack_from('<I', page)[0]


def commands(c, kind):
    m = re.search((kind + r'-(\d+)').encode(), c)
    assert m, f'missing event {kind}'
    pos = m.end()
    result = []
    for _ in range(int(m.group(1))):
        length = struct.unpack_from('<I', c, pos)[0]
        pos += 4
        result.append(c[pos:pos + length].decode())
        pos += length
    return result


def patch_event(c, kind, before, after):
    token = f'{kind}-{len(before)}'.encode()
    assert c.count(token) == 1, (kind, c.count(token))
    i = c.index(token)
    e = i + len(token)
    enc = lambda lines: b''.join(struct.pack('<I', len(s.encode())) + s.encode() for s in lines)
    old = enc(before)
    assert c[e:e + len(old)] == old
    new_token = f'{kind}-{len(after)}'.encode()
    assert struct.unpack_from('<I', c, i - 4)[0] == len(token)
    return c[:i - 4] + struct.pack('<I', len(new_token)) + new_token + enc(after) + c[e + len(old):]


def patch_attr(c, key, new):
    pat = rb'([\x11-\x1e])\x00{3}' + key.encode() + b'\0' * (16 - len(key))
    ms = list(re.finditer(pat, c))
    assert len(ms) == 1, (key, len(ms))
    m = ms[0]
    width = m.group(1)[0] & 15
    assert 0 <= new < 1 << (width * 8)
    return c[:m.end()] + new.to_bytes(width, 'little') + c[m.end() + width:]


def main():
    b = bytearray(SOURCE.read_bytes())
    count, entries = pages(b)
    name, start, size, deleted, entry = next(q for q in entries if q[0] == '19.pa' and q[3] == 0)
    p = bytes(b[start:start + size])
    assert p[24:40].split(b'\0')[0] == b'pageHome'
    assert crc(p) == struct.unpack_from('<I', p)[0], 'base pageHome CRC mismatch'
    n = struct.unpack_from('<I', p, 12)[0]
    comps = []
    for i in range(n):
        off, size, unknown = struct.unpack_from('<III', p, 56 + 12 * i)
        assert unknown == 0
        comps.append(p[56 + off:56 + off + size])
    assert b''.join(comps) == p[56 + 12 * n:]
    old = commands(comps[0], 'codesload')
    assert len(old) == 6, 'unrecognized pageHome initialize handler'
    new = old + ['vaPrvpHPercen.val=65535', 'vaPrvOrpPercen.val=65535', 'click bDateTime,1', 'click bUpdateGauge,1']
    comps[0] = patch_event(comps[0], 'codesload', old, new)
    for index, attrs in ((14, {'x': 304, 'y': 5, 'w': 94, 'xcen': 1}),
                         (21, {'x': 304, 'y': 31, 'w': 94, 'xcen': 1, 'txt_maxl': 9})):
        for key, value in attrs.items():
            comps[index] = patch_attr(comps[index], key, value)
    comps[29] = patch_attr(comps[29], 'tim', 60000)
    old = commands(comps[27], 'codesdown')
    assert len(old) == 21 and old[11] == '// Build Date', 'unrecognized date handler'
    new = old[:11] + [
        '// Build Date DD/MM/YY', 'vaTmpDateTime.txt=""',
        'covx rtc2,vaBuildDatTime.txt,2,0', 'vaTmpDateTime.txt+=vaBuildDatTime.txt',
        'vaTmpDateTime.txt+="/"', 'covx rtc1,vaBuildDatTime.txt,2,0',
        'vaTmpDateTime.txt+=vaBuildDatTime.txt', 'vaTmpDateTime.txt+="/"',
        'sys0=rtc0%100', 'covx sys0,vaBuildDatTime.txt,2,0',
        'vaTmpDateTime.txt+=vaBuildDatTime.txt', 'if(vaTmpDateTime.txt!=tDate.txt)',
        '{', '  tDate.txt=vaTmpDateTime.txt', '}',
    ]
    comps[27] = patch_event(comps[27], 'codesdown', old, new)
    page = bytearray(p[:56 + 12 * n])
    offset = 12 * n
    for i, c in enumerate(comps):
        struct.pack_into('<III', page, 56 + i * 12, offset, len(c), 0)
        offset += len(c)
    page.extend(b''.join(comps))
    struct.pack_into('<I', page, 4, len(page))
    struct.pack_into('<I', page, 0, crc(page))
    replace_page(b, count, entry, page)
    name, start, size, deleted, entry = next(q for q in entries if q[0] == '5.pa' and q[3] == 0)
    g = bytearray(b[start:start + size])
    assert g[24:40].split(b'\0')[0] == b'globals' and g.count(b'6.0.0') == 1
    assert crc(g) == struct.unpack_from('<I', g)[0]
    g = g.replace(b'6.0.0', b'7.0.0')
    struct.pack_into('<I', g, 0, crc(g))
    replace_page(b, count, entry, g)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(b)
    assert crc(page) == struct.unpack_from('<I', page)[0]
    print('Generated:', TARGET, 'bytes:', len(b), 'sha256:', hashlib.sha256(b).hexdigest())
    print('WARNING: HMI format/CRC checks only. Nextion Editor must compile it before use.')


if __name__ == '__main__':
    main()