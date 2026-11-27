#!/usr/bin/env python3
"""Build modern Flow.io Nextion NX4832K035_011 HMI 7.0.0 from saved validated 7.0.0.

This mutates ONLY pageHome, the HomeGaugepic atlas (logical picture #3) and
five filtration icon picture resources (#20-24). Picture pixels MUST be
encoded column-major (x-major); the original project uses this layout. It preserves all other live
resources, screen touch component IDs, serial protocol and 60 s RTC timer.
Every modified directory entry receives its mirrored Nextion CRC32_T.
Editor open + compilation + live device testing are still required.
"""
from __future__ import annotations
import argparse
import hashlib
import math
from pathlib import Path
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Internal helpers already audited for the 7.0.0 project.

def _tab():
    out=[]
    for i in range(256):
        x=i<<24
        for _ in range(8):
            x=((x<<1) ^ (0x04C11DB7 if x & 0x80000000 else 0)) & 0xFFFFFFFF
        out.append(x)
    return out
TABLE=_tab()

def _mix_byte(seed: int, data: bytes)->int:
    for b in data:
        seed ^= b
        for _ in range(4):
            seed=((seed<<8)&0xFFFFFFFF)^TABLE[seed>>24]
    return seed

def crc_page(page: bytes)->int:
    seed=0xFFFFFFFF
    for part in (page[4:],page[4:8],page[12:16],page[20:21],page[21:22]):
        seed=_mix_byte(seed,part)
    return seed

def dir_crc(data: bytes)->int:
    assert len(data)%4==0
    seed=0xFFFFFFFF
    for i in range(0,len(data),4):
        seed ^= int.from_bytes(data[i:i+4],'little')
        for _ in range(4):
            seed=((seed<<8)&0xFFFFFFFF)^TABLE[seed>>24]
    return seed

def directory(buf: bytes):
    cnt=struct.unpack_from('<I',buf,0)[0]
    assert 20<cnt<1000
    end=4+cnt*28
    assert buf[:end+4]==buf[0x80000:0x80000+end+4], 'directory mirrors differ'
    assert struct.unpack_from('<I',buf,end)[0]==dir_crc(buf[:end]+b'ADEC'), 'directory checksum mismatch'
    assert buf[0x6FFFF8:0x700000]==b'ver21234','HMI magic missing'
    result={}
    for i in range(cnt):
        pos=4+i*28
        name,off,size,delbit,*_ = struct.unpack_from('<16sIIBBBB',buf,pos)
        name=name.split(b'\0')[0].decode('ascii','replace')
        if delbit==0:
            assert name not in result,(name,'duplicate')
            assert off+size<=len(buf),(name,off,size,len(buf))
            result[name]=(pos,off,size)
    return result

def component_slices(p:bytes):
    n=struct.unpack_from('<I',p,12)[0]
    out=[]
    for i in range(n):
        rel,size,pad=struct.unpack_from('<III',p,56+i*12)
        assert pad==0
        out.append((56+rel,size))
    assert sum(x[1] for x in out)==len(p)-56-12*n
    return out

def patch_attr(c:bytearray,name:str,val:int)->None:
    pat=rb'([\x11-\x1e])\x00{3}'+name.encode('ascii')+b'\0'*(16-len(name))
    hits=list(re.finditer(pat,c))
    if len(hits)!=1: raise ValueError(f'attr {name} has {len(hits)} matches')
    m=hits[0];wid=m.group(1)[0]&15
    if not 0<=val<2**(wid*8):raise ValueError((name,val,wid))
    c[m.end():m.end()+wid]=val.to_bytes(wid,'little')

def _commands(c:bytes,kind:str):
    m=re.search((kind+r'-(\d+)').encode(),c)
    if m is None:raise ValueError('missing '+kind)
    cursor=m.end(); lines=[]
    for _ in range(int(m.group(1))):
        n=struct.unpack_from('<I',c,cursor)[0];cursor+=4
        lines.append(c[cursor:cursor+n].decode('utf-8'));cursor+=n
    return m,lines,cursor

def replace_commands(c:bytes,kind:str,lines:list[str])->bytes:
    m,old,end=_commands(c,kind)
    newname=(kind+'-'+str(len(lines))).encode()
    pack=b''.join(struct.pack('<I',len(v.encode('utf-8')))+v.encode('utf-8') for v in lines)
    return c[:m.start()]+newname+pack+c[end:]

def rebuild_page(p:bytes,edits:dict[int,bytes])->bytes:
    old_slices=component_slices(p)
    pieces=[edits.get(i,p[off:off+size]) for i,(off,size) in enumerate(old_slices)]
    out=bytearray(p[:56+12*len(pieces)])
    off=len(pieces)*12
    for i,comp in enumerate(pieces):
        struct.pack_into('<III',out,56+i*12,off,len(comp),0)
        off+=len(comp)
    out.extend(b''.join(pieces))
    struct.pack_into('<I',out,4,len(out))
    struct.pack_into('<I',out,0,crc_page(out))
    assert component_slices(out)
    assert crc_page(out)==struct.unpack_from('<I',out)[0]
    return bytes(out)

def rgb565(rgb):
    r,g,b=rgb[:3]
    return ((int(r)>>3)<<11)|((int(g)>>2)<<5)|(int(b)>>3)

def render_atlas(logo:Path, out_png:Path):
    S=3
    W,H=480,320
    bg=Image.new('RGB',(W*S,H*S))
    pix=bg.load()
    # Navy gradient with very subtle center cyan glow.
    for y in range(H*S):
        yy=y/S
        for x in range(W*S):
            xx=x/S
            glow=max(0,1-((xx-240)/290)**2-((yy-128)/270)**2)
            col=(int(3+7*glow),int(18+19*glow+3*yy/H),int(36+28*glow+5*yy/H))
            pix[x,y]=col
    d=ImageDraw.Draw(bg)
    def box(x0,y0,x1,y1,radius,fill=None,outline=None,width=1):
        d.rounded_rectangle((x0*S,y0*S,x1*S,y1*S),radius=radius*S,fill=fill,outline=outline,width=width*S)
    # Header/footer outlines / dividers.
    box(2,2,478,58,12,fill=(4,27,51),outline=(5,204,238),width=1)
    box(3,263,477,317,15,fill=(4,28,53),outline=(3,196,235),width=1)
    for x in [148,299,413]:
        d.line((x*S,13*S,x*S,47*S),fill=(5,164,215),width=S)
    for x in [90,188,289,380]:
        d.line((x*S,273*S,x*S,307*S),fill=(7,164,214),width=S)
    # Exact official Flow.io three-wave emblem: blue-wave pixels extracted from
    # the provided image or repository web-logo PNG, not a generated imitation.
    raw=Image.open(logo).convert('RGBA')
    rgb=np.array(raw)
    sel=(rgb[:,:,2]>rgb[:,:,0]+13)&(rgb[:,:,1]>rgb[:,:,0]+3)&(rgb[:,:,3]>20)
    if not np.any(sel):raise ValueError('logo has no identifiable aqua wave pixels')
    ys,xs=np.where(sel)
    wave=raw.crop((max(0,int(xs.min())-2),max(0,int(ys.min())-2),min(raw.width,int(xs.max())+3),min(raw.height,int(ys.max())+3)))
    a=np.array(wave.convert('RGBA'))
    wave_mask=((a[:,:,2].astype(int)>a[:,:,0].astype(int)+13)&(a[:,:,1].astype(int)>a[:,:,0].astype(int)+3)).astype(np.uint8)*255
    a[:,:,3]=wave_mask
    wave=Image.fromarray(a,'RGBA'); wave.thumbnail((49*S,36*S),Image.Resampling.LANCZOS)
    bg.paste(wave,(8*S,13*S),wave)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    inter='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    def label(s,xy,size,color=(241,252,255),bold=True,anchor=None):
        d.text((int(xy[0]*S),int(xy[1]*S)),s,font=ImageFont.truetype(font if bold else inter,size*S),fill=color,anchor=anchor,stroke_width=0)
    label('flow.io',(60,19),21,(245,251,255))
    # Make dot and 'io' turquoise while preserving lowercase typography.
    box(132,22,145,27,2,fill=(4,27,51)) if False else None
    # Pool ladder with blue water waves + red thermometer.
    d.rounded_rectangle((156*S,8*S,165*S,43*S),radius=5*S,outline=(240,249,255),width=2*S)
    d.ellipse((154*S,34*S,167*S,47*S),fill=(242,41,48),outline=(240,249,255),width=2*S)
    d.line((160*S,20*S,160*S,42*S),fill=(250,57,51),width=4*S)
    for z in range(3):
        y=36+z*4
        d.arc((170*S,(y-2)*S,186*S,(y+4)*S),170,350,fill=(14,212,237),width=2*S)
    d.line((174*S,18*S,174*S,32*S),fill=(239,248,255),width=2*S)
    d.line((181*S,18*S,181*S,32*S),fill=(239,248,255),width=2*S)
    d.arc((173*S,14*S,182*S,21*S),180,360,fill=(239,248,255),width=2*S)
    # Two positive nominal targets in plain green, no pill outlines.
    label('7.5',(123,71),15,(105,250,51),anchor='mm')
    label('700',(356,71),15,(105,250,51),anchor='mm')
    for cx in [123,356]:
        d.polygon([(cx*S,86*S),((cx-5)*S,78*S),((cx+5)*S,78*S)],fill=(246,252,255))
    # Gauge-area background is flat to avoid square patches under dynamic text.
    inner=(4,18,37)
    d.rectangle((20*S,89*S,227*S,239*S),fill=inner)
    d.rectangle((253*S,89*S,460*S,239*S),fill=inner)
    # Static labels and min/max scales remain on page, outside xpic sprite area.
    label('pH',(123,247),13,(244,249,253),anchor='mm')
    label('ORP',(356,247),13,(244,249,253),anchor='mm')
    # Bottom icons keep the original touch areas (b0, b1, hotspots).
    for xx in (23,36):
        for yy in (277,291):
            d.rounded_rectangle((xx*S,yy*S,(xx+9)*S,(yy+9)*S),radius=2*S,outline=(238,248,255),width=2*S)
    # Water drop and wave
    d.polygon([(117*S,274*S),(106*S,293*S),(108*S,299*S),(117*S,304*S),(125*S,300*S),(128*S,294*S)],fill=(12,191,250))
    d.arc((102*S,301*S,132*S,316*S),185,355,fill=(15,211,240),width=3*S)
    # Refresh icon
    d.arc((324*S,275*S,353*S,302*S),45,307,fill=(3,217,238),width=4*S)
    d.polygon([(353*S,291*S),(359*S,294*S),(354*S,300*S)],fill=(3,217,238))
    # Alert triangle
    d.polygon([(451*S,275*S),(439*S,302*S),(467*S,302*S)],outline=(244,249,255))
    d.line((453*S,283*S,453*S,294*S),fill=(244,249,255),width=3*S)
    d.ellipse((452*S,297*S,455*S,300*S),fill=(244,249,255))
    # Leave Wi-Fi space vacant; native tWifiState remains live/dynamic.
    # The signal color is set by the existing state handler, not forged graphics.
    # Polished gauge frames: five levels, shared for pH + ORP, using original
    # xpic 207-pixel-column indexing and exact Nextion RGB565 sprite pixels.
    sw,sh=207,150
    stripe=Image.new('RGB',(1035*S,sh*S),inner)
    for level in range(5):
        frame=Image.new('RGB',(sw*S,sh*S),inner)
        f=ImageDraw.Draw(frame)
        rect=(8*S,29*S,199*S,221*S)
        colors=[(254,39,86),(254,137,19),(255,212,32),(98,252,55),(2,212,237)]
        for k in range(5):
            lo=181+k*36+1.5;hi=181+(k+1)*36-1.5
            f.arc(rect,lo,hi,fill=colors[k],width=13*S)
        # Colored active position ring section, no colored value capsule.
        lo=181+level*36+3;hi=181+(level+1)*36-3
        f.arc((5*S,26*S,202*S,224*S),lo,hi,fill=(246,251,255),width=S)
        for t in range(15):
            angle=(180+t*180/14)*math.pi/180
            cx=103+92*math.cos(angle);cy=125+92*math.sin(angle)
            ex=103+83*math.cos(angle);ey=125+83*math.sin(angle)
            # Above ellipse y-range constrained to 150 high; avoid below frame.
            if 1<cy<146 and 1<ey<146:
                f.line((int(cx*S),int(cy*S),int(ex*S),int(ey*S)),fill=(240,250,255),width=max(1,S//2))
        stripe.paste(frame,(level*sw*S,0))
    # Screenshots for manual visual QA.
    bg_small=bg.resize((W,H),Image.Resampling.LANCZOS)
    stripe_small=stripe.resize((1035,150),Image.Resampling.LANCZOS)
    out_png.parent.mkdir(parents=True,exist_ok=True)
    demo=bg_small.copy()
    for x in [20,253]: demo.paste(stripe_small.crop((2*207,0,3*207,150)),(x,89))
    dv=ImageDraw.Draw(demo)
    dv.text((121,168),'7.50',font=ImageFont.truetype(font,24),fill='white',anchor='mm')
    dv.text((357,168),'706',font=ImageFont.truetype(font,25),fill='white',anchor='mm')
    dv.text((194,17),'22.7°C',font=ImageFont.truetype(font,20),fill='white')
    dv.text((306,11),'10:47',font=ImageFont.truetype(font,19),fill='white')
    dv.text((306,35),'27/11/26',font=ImageFont.truetype(font,13),fill='white')
    demo.save(out_png)
    # Atlas has 150 sprite rows, then 320 screen background rows.
    atlas=Image.new('RGB',(1035,470),inner)
    atlas.paste(stripe_small,(0,0)); atlas.paste(bg_small,(0,150))
    return atlas

def replace_pic(buf:bytearray,dir_table:dict,name:str,im:Image.Image,append:bool):
    entry,off,size=dir_table[name]
    old=bytes(buf[off:off+size]);assert old[0:4]==b'\x0b\x64\x01\x00' and len(old)>=24
    im=im.convert('RGB')
    a=np.array(im,dtype=np.uint16)
    rgb=((a[:,:,0]>>3)<<11)|((a[:,:,1]>>2)<<5)|(a[:,:,2]>>3)
    # CRITICAL: Nextion .i payloads are x-major (column-major), not normal
    # row-major RGB565. The old encoder wrote rows and produced white/corrupt
    # rectangles and broken sprites on a real NX4832K035 display.
    payload=rgb.astype('<u2').tobytes(order='F')
    decoded=np.frombuffer(payload,dtype='<u2').reshape((im.width,im.height)).T
    assert np.array_equal(decoded,rgb), f'Nextion image layout mismatch: {name}'
    # A row-major encoder must never be accepted for a non-uniform image.
    if im.width>1 and im.height>1 and not np.all(rgb==rgb.flat[0]):
        assert payload != rgb.astype('<u2').tobytes(order='C'), name
    header=bytearray(old[:24]);struct.pack_into('<H',header,12,im.width);struct.pack_into('<H',header,14,im.height);struct.pack_into('<I',header,16,len(payload))
    new=bytes(header)+payload
    if append:
        at=len(buf);buf.extend(new)
        struct.pack_into('<II',buf,entry+16,at,len(new))
    else:
        assert len(new)==size,(name,len(new),size)
        buf[off:off+size]=new
    return len(new)

def write_dir(buf:bytearray):
    cnt=struct.unpack_from('<I',buf,0)[0];end=4+cnt*28
    checksum=dir_crc(bytes(buf[:end])+b'ADEC')
    struct.pack_into('<I',buf,end,checksum)
    buf[0x80000:0x80000+end+4]=buf[:end+4]

def replace_event_lines(c:bytes,kind:str,source:str,target:str)->bytes:
    _,lines,_=_commands(c,kind)
    if not any(source in x for x in lines):raise ValueError('missing event line '+source)
    altered=[x.replace(source,target) for x in lines]
    return replace_commands(c,kind,altered)

def build(source:Path,out:Path,logo:Path,preview:Path):
    buf=bytearray(source.read_bytes());original_len=len(buf)
    d=directory(buf)
    for name in ['36.i','4.i','8.i','28.i','29.i','26.i','19.pa','5.pa','main.HMI']:
        assert name in d,name
    # Ensure image #3 is the intended gauge sprite, not a similarly named resource.
    o,n=d['main.HMI'][1:];manifest=buf[o:o+n]
    assert manifest[96+3*16+8:96+4*16].split(b'\0')[0]==b'36.i'
    a=d['36.i'][1];assert struct.unpack_from('<HH',buf,a+12)==(1035,150)
    atlas=render_atlas(logo,preview)
    replace_pic(buf,d,'36.i',atlas,append=True)
    # New dynamic filtration icons retain logical indices 20..24 with 70x70.
    icons=['4.i','8.i','28.i','29.i','26.i']
    for idx,name in enumerate(icons):
        size=70; S=3;im=Image.new('RGB',(size*S,size*S),(4,18,37));dw=ImageDraw.Draw(im)
        clr=[(153,168,181),(65,221,132),(248,208,42),(254,132,27),(244,62,81)][idx]
        dw.arc((5*S,5*S,65*S,65*S),30,300,fill=clr,width=5*S)
        # Four bright aqua blades, retaining the original status variability.
        for k in range(4):
            a=k*math.pi/2
            x=35+19*math.cos(a);y=35+19*math.sin(a)
            dw.ellipse((int((x-8)*S),int((y-5)*S),int((x+7)*S),int((y+5)*S)),fill=(220,247,255))
        dw.ellipse((31*S,31*S,39*S,39*S),fill=(32,133,187))
        replace_pic(buf,d,name,im.resize((70,70),Image.Resampling.LANCZOS),append=False)
    # Edit the Home page in a new append-only blob, preserving existing other pages.
    entry,off,size=d['19.pa'];page=bytes(buf[off:off+size]);assert page[24:40].split(b'\0')[0]==b'pageHome'
    assert crc_page(page)==struct.unpack_from('<I',page,0)[0]
    parts=component_slices(page);edits={}
    # New header illustration is drawn in Postinitialize before all live controls.
    c0=bytearray(page[parts[0][0]:parts[0][0]+parts[0][1]])
    patch_attr(c0,'bco',rgb565((4,18,37)))
    c0=bytes(c0)
    _,old,_=_commands(c0,'codesloadend')
    assert 'click bUpdateGauge,1' in old
    new=[
        '// Draw full-screen modern backdrop from unused rows of HomeGaugepic',
        'xpic 0,0,480,320,0,150,HomeGaugepic',
        'vaPrvpHPercen.val=-1',
        'vaPrvOrpPercen.val=-1',
        'vaPrvPSINid.val=-1',
        '// Restore live objects and user interactions after backdrop blit',
        'ref tWaterTemp','ref tTime','ref tDate','ref tWifiState',
        'ref tFConnectState','ref tPHTitle','ref tOrpTitle',
        'ref tpH','ref tORP','ref tProp',
        'ref tpHInject','ref tChlInject','ref tSWGRunning',
        'ref tErrMessage','ref b0','ref b1',
        'click bUpdateGauge,1','click bInjectUpdt,1','click bDateTime,1',
    ]
    edits[0]=replace_commands(c0,'codesloadend',new)
    # All transparent-looking text rectangles are styled in the same navy.
    navy=rgb565((4,18,37))
    for idx in [2,3,4,5,6,7,14,15,16,18,21,25,26,33,36]:
        pos,n=parts[idx];c=bytearray(page[pos:pos+n]);patch_attr(c,'bco',navy)
        edits[idx]=bytes(c)
    # Dynamic gauge refresh: keep all five severity buckets and force redraw on wake.
    pos,n=parts[9];c=bytes(page[pos:pos+n]);_,lines,_=_commands(c,'codesdown')
    gauge_lines=[]
    for line in lines:
        for symbol in ['Red_Color','Orange_Color','Green_Color']:
            if line.strip() in ('tpH.bco='+symbol,'tORP.bco='+symbol):line=line.replace(symbol,str(navy))
        if line.strip()=='tWifiState.pco=1178':line='  tWifiState.pco='+str(rgb565((44,239,142)))
        if line.strip()=='tWifiState.pco=65535':line='  tWifiState.pco='+str(rgb565((6,224,234)))
        gauge_lines.append(line)
    edits[9]=replace_commands(c,'codesdown',gauge_lines)
    # Center labels unchanged, so captions pH and ORP remain live and legible.
    newpage=rebuild_page(page,edits)
    at=len(buf);buf.extend(newpage);struct.pack_into('<II',buf,entry+16,at,len(newpage))
    # Stay on 7.0.0: the original version stamp and globals page are untouched.
    entry,off,size=d['5.pa']
    original_globals=bytes(buf[off:off+size])
    assert original_globals.count(b'7.0.0')==1
    assert crc_page(original_globals)==struct.unpack_from('<I',original_globals)[0]
    write_dir(buf)
    dirs=directory(buf)
    assert dirs['36.i'][2]==24+1035*470*2
    assert dirs['19.pa'][2]==len(newpage)
    for name in ['5.pa','19.pa']:
        _,off,size=dirs[name];p=buf[off:off+size]
        assert crc_page(p)==struct.unpack_from('<I',p,0)[0]
    assert buf[dirs['5.pa'][1]:dirs['5.pa'][1]+dirs['5.pa'][2]]==original_globals
    assert b'7.0.0' in original_globals
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(buf)
    print('HMI',out,'bytes',len(buf),'sha256',hashlib.sha256(buf).hexdigest())
    print('PREVIEW',preview,'bytes',preview.stat().st_size)
    print('RESOURCES: 36.i new atlas / images 20-24 / pageHome; globals unchanged; VERSION 7.0.0')
    print('VALIDATED: mirror, directory CRC, page CRCs, magic, bounds, live layout')
    print('NEXTION EDITOR OPEN/COMPILE and real-display acceptance still REQUIRED')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--logo',type=Path,required=True)
    p.add_argument('--preview',type=Path,required=True)
    a=p.parse_args();build(a.source,a.out,a.logo,a.preview)

if __name__=='__main__':main()

