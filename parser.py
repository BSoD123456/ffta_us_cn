#! python3
# coding: utf-8

import os, os.path

# ===============
# common
# ===============

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

def rvs_endian(src, size, dst_signed):
    if src < 0:
        src += (1 << (size*8))
    dst = 0
    neg = False
    for i in range(size):
        b = (src & 0xff)
        if dst_signed and i == 0 and b + 0x7f:
            neg = True
            b &= 0x7f
        dst <<= 8
        dst |= b
        src >>= 8
    return dst - (1 << (size*8 - 1)) if neg else dst

INF = float('inf')

class c_mark:

    def __init__(self, raw, offset):
        self._raw = raw
        self._mod = None
        self.offset = offset
        self.parent = None
        self._par_offset = 0

    @property
    def raw(self):
        if self.parent:
            return self.parent.raw
        return self._raw if self._mod is None else self._mod

    @property
    def mod(self):
        if self.parent:
            return self.parent.mod
        if not self._mod is None:
            self._mod = bytearray(self._raw)
        return self._mod

    @property
    def par_offset(self):
        po = self._par_offset
        if self.parent:
            po += self.parent.par_offset
        return po

    def shift(self, offs):
        self._par_offset += offs

    def extendto(self, cnt):
        extlen = self.offset + cnt - len(self.raw)
        if extlen > 0:
            self.mod.extend(bytes(extlen))

    def readval(self, pos, cnt, signed):
        return readval_le(self.raw, self.offset + pos, cnt, signed)

    def writeval(self, val, pos, cnt):
        self.extendto(pos + cnt)
        writeval_le(val, self.mod, self.offset + pos, cnt)

    def fill(self, val, pos, cnt):
        for i in range(pos, pos + cnt):
            self.mod[i] = val

    def findval(self, val, pos, cnt, signed):
        st = pos
        ed = len(self.raw) - cnt + 1 - self.offset
        for i in range(st, ed, cnt):
            s = self.readval(i, cnt, signed)
            if s == val:
                return i
        else:
            return -1

    def forval(self, cb, pos, cnt, signed):
        st = pos
        ed = len(self.raw) - cnt + 1 - self.offset
        ln = (ed - st + 1) // 2
        for i in range(st, ed, cnt):
            s = self.readval(i, cnt, signed)
            if cb(i, s, ln) == False:
                return False
        return True

    def replace(self, buf):
        if not isinstance(buf, bytearray):
            buf = bytearray(buf)
        self._mod = buf

    I8  = lambda self, pos: self.readval(pos, 1, True)
    U8  = lambda self, pos: self.readval(pos, 1, False)
    I16 = lambda self, pos: self.readval(pos, 2, True)
    U16 = lambda self, pos: self.readval(pos, 2, False)
    I32 = lambda self, pos: self.readval(pos, 4, True)
    U32 = lambda self, pos: self.readval(pos, 4, False)
    I64 = lambda self, pos: self.readval(pos, 8, True)
    U64 = lambda self, pos: self.readval(pos, 8, False)

    W8  = lambda self, val, pos: self.writeval(val, pos, 1)
    W16 = lambda self, val, pos: self.writeval(val, pos, 2)
    W32 = lambda self, val, pos: self.writeval(val, pos, 4)
    W64 = lambda self, val, pos: self.writeval(val, pos, 8)

    FI8 = lambda self, val, pos: self.findval(val, pos, 1, True)
    FU8 = lambda self, val, pos: self.findval(val, pos, 1, False)
    FI16 = lambda self, val, pos: self.findval(val, pos, 2, True)
    FU16 = lambda self, val, pos: self.findval(val, pos, 2, False)
    FI32 = lambda self, val, pos: self.findval(val, pos, 4, True)
    FU32 = lambda self, val, pos: self.findval(val, pos, 4, False)
    FI64 = lambda self, val, pos: self.findval(val, pos, 8, True)
    FU64 = lambda self, val, pos: self.findval(val, pos, 8, False)

    FORI8 = lambda self, cb, pos: self.forval(cb, pos, 1, True)
    FORU8 = lambda self, cb, pos: self.forval(cb, pos, 1, False)
    FORI16 = lambda self, cb, pos: self.forval(cb, pos, 2, True)
    FORU16 = lambda self, cb, pos: self.forval(cb, pos, 2, False)
    FORI32 = lambda self, cb, pos: self.forval(cb, pos, 4, True)
    FORU32 = lambda self, cb, pos: self.forval(cb, pos, 4, False)
    FORI64 = lambda self, cb, pos: self.forval(cb, pos, 8, True)
    FORU64 = lambda self, cb, pos: self.forval(cb, pos, 8, False)

    def BYTES(self, pos, cnt):
        st = self.offset + pos
        if cnt is None:
            ed = None
        else:
            ed = st + cnt
            self.extendto(pos + cnt)
        return self.raw[st: ed]

    def STR(self, pos, cnt, codec = 'utf8'):
        return self.BYTES(pos, cnt).split(b'\0')[0].decode(codec)

    def BYTESN(self, pos):
        st = self.offset + pos
        rl = len(self.raw)
        ed = rl
        for i in range(st, rl):
            if self.raw[i] == 0:
                ed = i
                break
        return self.raw[st:ed], ed - st

    def STRN(self, pos, codec = 'utf8'):
        b, n = self.BYTESN(pos)
        return b.decode(codec), n

    def FBYTES(self, dst, pos, stp = 1):
        cnt = len(dst)
        st = self.offset + pos
        ed = len(self.raw) - cnt + 1
        for i in range(st, ed, stp):
            for j in range(cnt):
                if self.raw[i+j] != dst[j]:
                    break
            else:
                return i - self.offset
        else:
            return -1

    def FSTR(self, dst, pos, stp = 1, codec = 'utf8'):
        return self.FBYTES(dst.encode(codec), pos, stp)

    def sub(self, pos, length = 0, cls = None):
        if not cls:
            cls = c_mark
        if length > 0:
            s = cls(None, 0)
            s._mod = bytearray(self.BYTES(pos, length))
            s._par_offset = self.par_offset + pos
        else:
            s = cls(None, self.offset + pos)
            s.parent = self
        return s

    def concat(self, dst, pos = None):
        db = dst.BYTES(0, None)
        if pos is None:
            self.mod.extend(db)
        else:
            sb = self.BYTES(0, pos)
            self.extendto(pos + len(db))
            self.mod[pos:] = db
        return self

def clsdec(hndl, *args, **kargs):
    class _dec:
        def __init__(self, mth):
            self.mth = mth
        def __set_name__(self, cls, mname):
            nmth = hndl(cls, mname, self.mth, *args, **kargs)
            if nmth is None:
                nmth = self.mth
            setattr(cls, mname, nmth)
    return _dec

# ===============
# ffta desc
# ===============

class c_ffta_sect(c_mark):

    ADDR_BASE = 0x8000000

    def _offs2addr(self, offs):
        return offs + self.ADDR_BASE

    def _addr2offs(self, addr):
        return addr - self.ADDR_BASE

    def _aot(self, v, typ):
        if typ[0] == typ[1]:
            return v
        elif typ[0] == 'a':
            assert(typ == 'ao')
            return self._addr2offs(v)
        else:
            assert(typ == 'oa')
            return self._offs2addr(v)

    def rdptr(self, ptr, typ = 'oao'):
        if typ[0] == 'a':
            ptr = self._addr2offs(ptr)
        return self._aot(self.U32(ptr), typ[1:])

def cmdc(code):
    def _hndl(cls, mname, mth):
        #if not hasattr(cls, '_cmd_tab'):
        # in __dict__ is the same as js hasOwnProperty
        # but hasattr check parents
        if not '_cmd_tab' in cls.__dict__:
            cls._cmd_tab = {}
        cls._cmd_tab[code] = mth
    return clsdec(_hndl)

class c_ffta_sect_cmd(c_ffta_sect):

    _cmd_tab = {}

    def _cmd(self, code):
        if not code in self._cmd_tab:
            return None
        return self._cmd_tab[code].__get__(self, type(self))

    def exec(self, params):
        pass

class c_ffta_sect_scene_cmd(c_ffta_sect_cmd):

    #cmd: text window
    #params: p1(c) p2(c) p3(c)
    #p1: index of text on this page
    #p2: index of portrait
    #p3: flags, 80: left, 82: right
    @cmdc(0x0f)
    def cmd_text(self, params):
        pass

class c_ffta_sect_tab(c_ffta_sect):
    _TAB_DESC = []
    def tbase(self, idx):
        cur = idx
        lst_stp = None
        for td in self._TAB_DESC:
            try:
                stp = td[0]
            except:
                stp = td
            try:
                ofs = td[1]
            except:
                ofs = 0
            if not lst_stp is None:
                #print(f'(lst_stp)[0x{cur:x}] = ', end = '')
                cur = self.readval(cur, lst_stp, False)
                #print(f'0x{cur:x}')
            #print(f'0x{cur:x} * {stp} + {ofs} = ', end = '')
            cur = cur * stp + ofs
            #print(f'0x{cur:x}')
            try:
                lst_stp = td[2]
            except:
                lst_stp = stp
        return cur

def tabitm(ofs):
    def _mod(mth):
        def _wrap(self, idx):
            return mth(self, self.tbase(idx) + ofs)
        return _wrap
    return _mod

class c_ffta_sect_scene_fat(c_ffta_sect_tab):
    
    _TAB_DESC = [4]

    @tabitm(0)
    def get_page_id(self, ofs):
        return self.U8(ofs)

    @tabitm(1)
    def get_line_idx(self, ofs):
        return self.U8(ofs)

    @tabitm(2)
    def get_page_idx(self, ofs):
        return self.U8(ofs)

    def iter_lines(self):
        idx = 1
        while True:
            pid = self.get_page_id(idx)
            li = self.get_line_idx(idx)
            pi = self.get_page_idx(idx)
            if pi == 0:
                break
            yield idx, pid, li, pi
            idx += 1

class c_ffta_sect_scene_text(c_ffta_sect_tab):
    _TAB_DESC = [4, 1]
    @tabitm(0)
    def get_page(self, ofs):
        return self.sub(ofs, cls = c_ffta_sect_scene_text_page)

class c_ffta_sect_scene_text_page(c_ffta_sect_tab):
    _TAB_DESC = [2, 1]
    @tabitm(0)
    def get_line(self, ofs):
        return self.sub(ofs, cls = c_ffta_sect_scene_text_line)

class c_ffta_sect_scene_text_line(c_ffta_sect):
    
    def _gc(self, si):
        c = self.U8(si)
        return c, si + 1

    def _bypass(self, si, di, d, l):
        for i in range(l):
            d.append(self.U8(si + i))
        return si + l, di + l

    @staticmethod
    def _flip(di, d, l, f):
        for i in range(l):
            #d.append(readval_le(d, di - f + i - 1, 1, False))
            d.append(d[di - f + i - 1])
        return di + l

    @staticmethod
    def _bset(di, d, l, v):
        for i in range(l):
            d.append(v)
        return di + l

    def _decompress(self, src_idx, dst_len):
        dst = bytearray()
        dst_idx = 0
        while dst_idx < dst_len:
            cmd, src_idx = self._gc(src_idx)
            #print hex(cmd)
            if cmd & 0x80:
                cmd1, src_idx = self._gc(src_idx)
                ln = ((cmd >> 3) & 0xf) + 3
                fl = (((cmd & 0x7) << 8) | cmd1)
                dst_idx = self._flip(dst_idx, dst, ln, fl)
            elif cmd & 0x40:
                ln = (cmd & 0x3f) + 1
                src_idx, dst_idx = self._bypass(src_idx, dst_idx, dst, ln)
            elif cmd & 0x20:
                ln = (cmd & 0x1f) + 2
                dst_idx = self._bset(dst_idx, dst, ln, 0x00)
            elif cmd & 0x10:
                cmd1, src_idx = self._gc(src_idx)
                cmd2, src_idx = self._gc(src_idx)
                ln = (((cmd1 & 0xc0) >> 2) | (cmd & 0xf)) + 4
                fl = (((cmd1 & 0x3f) << 8) | cmd2)
                dst_idx = self._flip(dst_idx, dst, ln, fl)
            elif cmd == 0x2:
                cmd1, src_idx = self._gc(src_idx)
                ln = cmd1 + 3
                dst_idx = self._bset(dst_idx, dst, ln, 0x00)
            elif cmd == 0x1:
                cmd1, src_idx = self._gc(src_idx)
                ln = cmd1 + 3
                dst_idx = self._bset(dst_idx, dst, ln, 0xff)
            elif cmd == 0x0:
                cmd1, src_idx = self._gc(src_idx)
                cmd2, src_idx = self._gc(src_idx)
                cmd3, src_idx = self._gc(src_idx)
                ln = cmd1 + 5
                fl = ((cmd2 << 8) | cmd3)
                dst_idx = self._flip(dst_idx, dst, ln, fl)
            else:
                pass
        return dst

    def parse(self):
        flags = self.U16(0)
        cmpr = not not (flags & 0x2)
        self.compressed = cmpr
        self.text = self.sub(2, cls = c_ffta_sect_scene_text_buf)
        if cmpr:
            dst_len = rvs_endian(self.U32(2), 4, False)
            buf = self._decompress(6, dst_len)
            assert(len(buf) == dst_len)
            self.text.replace(buf)

class c_ffta_sect_scene_text_buf(c_ffta_sect):
    pass

class c_ffta_sect_rom(c_ffta_sect):

    def parse(self, tabs_info):
        self._add_tabs(tabs_info)
        return self

    def _subsect(self, offs_ptr, c_sect):
        offs_base = self.rdptr(offs_ptr, 'oao')
        sect = self.sub(offs_base, cls = c_sect)
        return sect

    def _add_tabs(self, tabs_info):
        tabs = {}
        for tab_name, (tab_ptr, tab_cls) in tabs_info.items():
            tabs[tab_name] = self._subsect(tab_ptr, tab_cls)
        self.tabs = tabs

    def tst_txtdump(self, pg, ln, cnt):
        ent = self.tabs['s_fat'].get_entry(pg)
        tp = self.tabs['s_text'].get_page(ent)
        ofs = tp.tbase(ln)
        return self.tabs['s_text'].BYTES(ofs, cnt)

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    
    def main():
        global rom_us, rom_cn, rom_jp
        with open('fftaus.gba', 'rb') as fd:
            rom_us = c_ffta_sect_rom(fd.read(), 0).parse({
                's_fat': (0x009a20, c_ffta_sect_scene_fat),
                's_text': (0x009a88, c_ffta_sect_scene_text),
            })
        with open('fftacns.gba', 'rb') as fd:
            rom_cn = c_ffta_sect_rom(fd.read(), 0).parse({
                's_fat': (0x009a70, c_ffta_sect_scene_fat),
                's_text': (0x009ad8, c_ffta_sect_scene_text),
            })
        with open('fftajp.gba', 'rb') as fd:
            rom_jp = c_ffta_sect_rom(fd.read(), 0).parse({
                's_fat': (0x009a70, c_ffta_sect_scene_fat),
                's_text': (0x009ad8, c_ffta_sect_scene_text),
            })
    main()
    fat = rom_us.tabs['s_fat']
    txt = rom_us.tabs['s_text']
    def enum_text():
        for page in range(20):
            for line in range(5):
                txt.get_page(page).get_line(line).parse()
