#!/usr/bin/env python3
"""Safely patch NX4832K035 Nextion HMI 7.0.0 *in place*.

This does not add/append or resize any HMI resources. Directory, component sizes,
file length and content addresses are unchanged. Page CRCs are recalculated.
Nextion Editor must still open and compile the result before deployment.
"""
from pathlib import Path
import struct
import re
import hashlib

SOURCE = Path('nextion/releases/6.0.0/FlowIO_Nextion_NX4832K035_011-6.0.0.HMI')
TARGET = Path('nextion/releases/7.0.0/FlowIO_Nextion_NX4832K035_011-7.0.0.HMI')


def crc(page):
    t = []
    for i in range(256):
        x = i << 24
        for _ in range(8):
            x = ((x << 1) ^ (0x04C11DB7 if x & 0x80000000 else 0)) & 0xFFFFFFFF
        t.append(x)
    seed = 0xFFFFFFFF
    for part in (page[4:], page[4:8], page[12:16], page[20:21], page[21:22]):
        for v in part:
            seed ^= v
            for _ in range(4):
                seed = ((seed << 8) & 0xFFFFFFFF) ^ t[seed >> 24]
    return seed



def directory_checksum(directory_bytes):
    """CRC32_T over the directory followed by the ADEC sentinel (eseverson/nextion-hmi)."""
    data = directory_bytes + b'ADEC'
    assert len(data) % 4 == 0
    table = []
    for i in range(256):
        x = i << 24
        for _ in range(8):
            x = ((x << 1) ^ (0x04C11DB7 if x & 0x80000000 else 0)) & 0xFFFFFFFF
        table.append(x)
    seed = 0xFFFFFFFF
    for pos in range(0, len(data), 4):
        seed ^= int.from_bytes(data[pos:pos + 4], 'little')
        for _ in range(4):
            seed = ((seed << 8) & 0xFFFFFFFF) ^ table[seed >> 24]
    return seed


def entries(buf):
    count = struct.unpack_from('<I', buf)[0]
    assert 20 < count < 400
    mirror_len = 4 + 28 * count
    # The four-byte directory checksum follows the directory in both mirrors.
    assert buf[:mirror_len + 4] == buf[0x80000:0x80000 + mirror_len + 4], 'directory mirrors differ'
    assert buf[0x6FFFF8:0x700000] == b'ver21234', 'HMI magic missing'
    stored = struct.unpack_from('<I', buf, mirror_len)[0]
    expected = directory_checksum(buf[:mirror_len])
    assert stored == expected, f'directory CRC mismatch: stored={stored:08x}, expected={expected:08x}'
    data = {}
    for i in range(count):
        name, at, size, deleted, *_ = struct.unpack_from('<16sIIBBBB', buf, 4 + 28*i)
        name = name.split(b'\0')[0].decode('ascii','replace')
        if deleted == 0:
            assert at + size <= len(buf), (name, at, size)
            if name in data:
                raise ValueError(f'duplicate live {name}')
            data[name] = (at, size)
    return data


def components(page):
    num = struct.unpack_from('<I', page, 12)[0]
    out = []
    for i in range(num):
        off, size, extra = struct.unpack_from('<III', page, 56 + 12*i)
        assert extra == 0
        out.append((56 + off, size))
    assert sum(sz for _, sz in out) == len(page) - 56 - 12*num
    return out


def commands(c, kind):
    m = re.search((kind + r'-(\d+)').encode(), c)
    assert m, f'missing {kind}'
    pos = m.end()
    result = []
    for _ in range(int(m.group(1))):
        n = struct.unpack_from('<I', c, pos)[0]
        pos += 4
        result.append(c[pos:pos+n].decode('utf-8'))
        pos += n
    return m, result, pos


def patch_attr(c, name, value):
    pat = rb'([\x11-\x1e])\x00{3}' + name.encode() + b'\0' * (16 - len(name))
    matches = list(re.finditer(pat,c))
    assert len(matches) == 1, (name,len(matches))
    m = matches[0]
    width = m.group(1)[0] & 15
    old = int.from_bytes(c[m.end():m.end()+width], 'little')
    assert 0 <= value < (1 << (width * 8)), (name, value, width)
    c[m.end():m.end()+width] = value.to_bytes(width,'little')
    return old


def main():
    b = bytearray(SOURCE.read_bytes())
    original_len = len(b)
    before_dir = bytes(b[:4 + 28 * struct.unpack_from('<I',b)[0]])
    dirs = entries(b)
    assert '19.pa' in dirs and '5.pa' in dirs
    start, size = dirs['19.pa']
    page = bytearray(b[start:start+size]); assert page[24:40].split(b'\0')[0] == b'pageHome'
    assert crc(page) == struct.unpack_from('<I',page)[0], 'base Home CRC mismatch'
    offsets = components(page)

    for index, values in ((14, {'x':304,'y':5,'w':94,'xcen':1}),
                          (21, {'x':304,'y':31,'w':94,'xcen':1,'txt_maxl':9})):
        off, sz = offsets[index]
        c = bytearray(page[off:off+sz])
        for k,v in values.items():patch_attr(c,k,v)
        page[off:off+sz] = c

    off, sz = offsets[29]
    c = bytearray(page[off:off+sz])
    assert patch_attr(c, 'tim', 60000) == 5000
    page[off:off+sz] = c

    # Replacement uses the original 21 command entries and EXACT original size.
    # The new date is written from RTC as DD/MM/YY without changing any record sizes.
    off, sz = offsets[27]
    c = bytearray(page[off:off+sz])
    marker, old, end = commands(c,'codesdown')
    assert len(old)==21 and old[11]=='// Build Date', 'unknown Home date event'
    date = [
        '// Build Date DD/MM/YY',
        'covx rtc2,tDate.txt,2,0',
        'tDate.txt+="/"',
        'covx rtc1,vaBuildDatTime.txt,2,0',
        'tDate.txt+=vaBuildDatTime.txt',
        'tDate.txt+="/"',
        'sys0=rtc0%100',
        'covx sys0,vaBuildDatTime.txt,2,0',
        'tDate.txt+=vaBuildDatTime.txt',
        '// Date from RTC',
    ]
    new = old[:11] + date
    assert len(new)==len(old)==21
    oldtotal = sum(map(lambda s:len(s.encode()),old))
    newtotal = sum(map(lambda s:len(s.encode()),new))
    # Variable-length text lines may be rewritten provided the event keeps same size.
    # Pad the trailing comment only, never executable code.
    assert newtotal <= oldtotal, f'new lines too long by {newtotal-oldtotal} bytes'
    new[-1] += ' '*(oldtotal-newtotal)
    def pack_lines(lines):
        return b''.join(struct.pack('<I',len(s.encode()))+s.encode() for s in lines)
    p0, p1 = pack_lines(old), pack_lines(new)
    assert len(p0)==len(p1)
    assert c[marker.end():end] == p0
    c[marker.end():end] = p1
    assert len(c)==sz and commands(c,'codesdown')[1]==new
    page[off:off+sz] = c
    assert len(page)==size
    struct.pack_into('<I',page,0,crc(page))
    assert crc(page)==struct.unpack_from('<I',page)[0]
    b[start:start+size] = page

    # Same-length version stamp patch, preserving its page's CRC and directory.
    start, size = dirs['5.pa']
    page = bytearray(b[start:start+size])
    assert page[24:40].split(b'\0')[0]==b'globals'
    assert crc(page)==struct.unpack_from('<I',page)[0]
    assert page.count(b'6.0.0')==1
    page = page.replace(b'6.0.0',b'7.0.0')
    assert len(page)==size
    struct.pack_into('<I',page,0,crc(page))
    b[start:start+size] = page

    assert len(b)==original_len
    assert bytes(b[:len(before_dir)]) == before_dir
    assert entries(b)==dirs
    for name in ('5.pa','19.pa'):
        st,sz=dirs[name]; p=b[st:st+sz]
        assert crc(p)==struct.unpack_from('<I',p)[0], name
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_bytes(b)
    print('OUTPUT',TARGET,'size',len(b),'sha256',hashlib.sha256(b).hexdigest())
    print('CRC valid; all directory offsets, mirrors, page sizes, and file length unchanged')
    print('WARNING: still requires Nextion Editor open/compile check before use')

if __name__=='__main__':main()