#! python3
# coding: utf-8

# ===============
# tips:

# ===
# us:
# rom end: a39920

# func 812237c: (seadch ref by ghidra)
# load [81223c0] = 89a5d54 <- scen dat base
# call 8009a14 -> load [8009a20] = 8a19970 <- scen fat base

# ===
# cnjp:
# rom end: 9bb3d0

# (compare with us)
# [81178a8] = 89571b0 <- scen dat base
# [8009a70] = 899ab98 <- scen fat base

# ===============

import os, os.path

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

alignup   = lambda v, a: ((v - 1) // a + 1) * a
aligndown = lambda v, a: (v // a) * a

def readval_le(raw, offset, size, signed):
    neg = False
    v = 0
    endpos = offset + size - 1
    for i in range(endpos, offset - 1, -1):
        b = raw[i]
        if signed and i == endpos and b > 0x7f:
            neg = True
            b &= 0x7f
        #else:
        #    b &= 0xff
        v <<= 8
        v += b
    return v - (1 << (size*8 - 1)) if neg else v

def writeval_le(val, dst, offset, size):
    if val < 0:
        val += (1 << (size*8))
    for i in range(offset, offset + size):
        dst[i] = (val & 0xff)
        val >>= 8

INF = float('inf')

I8  = lambda raw, pos: readval_le(raw, pos, 1, True)
U8  = lambda raw, pos: readval_le(raw, pos, 1, False)
I16 = lambda raw, pos: readval_le(raw, pos, 2, True)
U16 = lambda raw, pos: readval_le(raw, pos, 2, False)
I32 = lambda raw, pos: readval_le(raw, pos, 4, True)
U32 = lambda raw, pos: readval_le(raw, pos, 4, False)
I64 = lambda raw, pos: readval_le(raw, pos, 8, True)
U64 = lambda raw, pos: readval_le(raw, pos, 8, False)
W8  = lambda raw, val, pos: writeval_le(val, raw, pos, 1)
W16 = lambda raw, val, pos: writeval_le(val, raw, pos, 2)
W32 = lambda raw, val, pos: writeval_le(val, raw, pos, 4)
W64 = lambda raw, val, pos: writeval_le(val, raw, pos, 8)

# ===============

rom_base = 0x8000000

s1ed = 0xa39920
s2ed = 0x9bb3d0

# point of DAT FAT TXT F_TBL, by ghidra search
# TXT base in thumb code 9a36. It's scene text index getter
s1pas = [
    0x1223c0, 0x009a20, 0x009a88, 0x122b10,
]

# by compare
s2pas = [
    0x1178a8, 0x009a70, 0x009ad8, 0x117f10,
]

def _print_points(raw, pas):
    for i, pa in enumerate(pas):
        a = U32(raw, pa) - rom_base
        print(f'{i+1} [0x{pa:x}] = 0x{a:x}')

def tst_print_addrs():
    with open('fftaus.gba', 'rb') as sfd1:
        with open('fftacns.gba', 'rb') as sfd2:
            print('us:')
            _print_points(sfd1.read(), s1pas)
            print('jpcn:')
            _print_points(sfd2.read(), s2pas)

def _rplc_addr(dd, sd, aps, ofs):
    for da, sa in aps:
        sv = U32(sd, sa)
        print(f'src [{sa:x}] = {sv:x}')
        print(f'=> [{da:x}] := {sv:x} + {ofs:x}')
        W32(dd, sv + ofs, da)

def tst_concat():
    
    s2ptop = s2pas[-1]
    
    with open('fftaus.gba', 'rb') as sfd1:
        with open('fftajp.gba', 'rb') as sfd2:
            with open('fftaus_mod.gba', 'wb') as dfd:
                b1 = bytearray(sfd1.read(s1ed))
                b2 = sfd2.read()
                s2top = U32(b2, s2ptop) - rom_base
                print(f's2top({s2top:x})')
                b2ofs = s1ed - s2top + rom_base
                _rplc_addr(b1, b2, zip(
                    s1pas[2:3],
                    s2pas[2:3],
                ), b2ofs)
                
                sfd2.seek(s2top)
                b2c = sfd2.read(s2ed - s2top)
                dfd.write(b1)
                dfd.write(b2c)

def tst_replace():

    us_chtb_bs = 0x433330
    us_chtb_ln = 0xc67 * 0x80

    jp_chtb_bs = 0x425030
    jp_chtb_ln = 0xc66 * 0x80
    
    with open('fftaus.gba', 'rb') as sfd1:
        with open('fftacns.gba', 'rb') as sfd2:
            with open('fftaus_mod.gba', 'wb') as dfd:
                b1 = bytearray(sfd1.read(s1ed))
                s1txt = U32(b1, s1pas[2]) - rom_base
                s1end = U32(b1, s1pas[1]) - rom_base
                s1len = s1end - s1txt
                b2 = sfd2.read()
                s2txt = U32(b2, s2pas[2]) - rom_base
                s2end = U32(b2, s2pas[1]) - rom_base
                s2len = s2end - s2txt
                rlen = min(s1len, s2len)
                print(*(hex(i) for i in [s1txt, s1end, s1len, s2txt, s2end, s2len, rlen]))
                b1[s1txt:s1txt + rlen] = b2[s2txt:s2txt + rlen]

                chtb_ln = min(us_chtb_ln, jp_chtb_ln)
                b1[us_chtb_bs:us_chtb_bs+chtb_ln] = b2[jp_chtb_bs:jp_chtb_bs+chtb_ln]
                
                dfd.write(b1)

if __name__ == '__main__':
    import pdb
    tst_print_addrs()
