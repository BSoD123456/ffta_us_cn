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
        # mark from buf
        self.offset = offset
        self.parent = None
        self._buf_offset = 0
        self._buf_real_offset = 0

    @property
    def raw(self):
        if self.parent:
            return self.parent.raw
        return self._raw if self._mod is None else self._mod

    @property
    def mod(self):
        if self.parent:
            return self.parent.mod
        if self._mod is None:
            self._mod = bytearray(self._raw)
        return self._mod

    # buf from last buf
    @property
    def buf_offset(self):
        if self.parent:
            #assert(self._buf_offset == 0)
            return self.parent.buf_offset
        else:
            return self._buf_offset

    # buf from base
    @property
    def buf_real_offset(self):
        if self.parent:
            #assert(self._buf_real_offset == 0)
            return self.parent.buf_real_offset
        else:
            return self._buf_real_offset

    # mark from base
    @property
    def real_offset(self):
        return self.buf_real_offset + self.offset

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

    def WBYTES(self, dst, pos):
        st = self.offset + pos
        cnt = len(dst)
        ed = st + cnt
        self.extendto(pos + cnt)
        self.mod[st: ed] = dst
        return cnt

    def STR(self, pos, cnt, codec = 'utf8'):
        return self.BYTES(pos, cnt).split(b'\0')[0].decode(codec)

    def WSTR(self, dst, pos, codec = 'utf8'):
        b = dst.encode(codec)
        if b[-1] != 0:
            b += b'\0'
        return self.WBYTES(b, pos)

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

    def sub(self, pos, length = None, cls = None):
        if not cls:
            cls = c_mark
        if length is None:
            s = cls(None, self.offset + pos)
            s.parent = self
        else:
            s = cls(None, 0)
            s._mod = bytearray(self.BYTES(pos, length))
            s._buf_offset = self.offset + pos
            s._buf_real_offset = self.real_offset + pos
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
#   ffta spec
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

# ===============
#      tabs
# ===============

class c_ffta_sect_tab(c_ffta_sect):
    _TAB_DESC = []
    def _tbase(self, *idxs):
        ii = 0
        lst_stp = None
        val_cch = []
        for td in self._TAB_DESC:
            # tab desc:
            # step of (offset, cur_idx, *-1_val, -1_val, *-2_val, -2_val, ...)
            if not isinstance(td, tuple):
                if val_cch:
                    td = (0, 0, td)
                else:
                    td = (0, td)
            cur = 0
            all_stp = 1
            for i, stp in enumerate(td):
                if stp == 0:
                    continue
                bi = i // 2
                is_stp = True
                if i % 2:
                    if bi == 0:
                        cval = idxs[ii]
                        ii += 1
                    else:
                        cval = val_cch[-bi][0]
                else:
                    if bi == 0:
                        cval = 1
                        is_stp = False
                    else:
                        _lv, _lb = val_cch[-bi]
                        if isinstance(stp, tuple):
                            _lb = stp[1]
                            stp = stp[0]
                        cval = self.readval(_lv, _lb, False)
                        #print(f'({_lb})[0x{_lv:x}] == 0x{cval:x}')
                if is_stp:
                    all_stp *= stp
                #print(f'typ({len(val_cch)}:{bi}/{i%2}) cur(0x{cur:x}) + stp({stp}) * cval(0x{cval:x}) = ', end = '')
                cur += stp * cval
                #print(f'cur(0x{cur:x}) all_stp(0x{all_stp:x})')
            val_cch.append((cur, all_stp))
        return cur, ii
    def tbase(self, *idxs):
        return self._tbase(*idxs)[0]

def tabitm(ofs):
    def _mod(mth):
        def _wrap(self, *idxs, **kargs):
            bs, ri = self._tbase(*idxs)
            if ri < len(idxs):
                return mth(self, bs + ofs, *idxs[ri:], **kargs)
            else:
                return mth(self, bs + ofs, **kargs)
        return _wrap
    return _mod

def tabkey(key):
    mn = 'get_' + key
    def _mod(cls):
        def _getkey(self, k):
            if hasattr(self, '_tab_cch'):
                cch = self._tab_cch
            else:
                cch = {}
                self._tab_cch = cch
            if k in cch:
                val = cch[k]
            else:
                if isinstance(k, tuple):
                    val = getattr(self, mn)(*k)
                else:
                    val = getattr(self, mn)(k)
                cch[k] = val
            return val
        cls.__getitem__ = _getkey
        return cls
    return _mod

# ===============
#     scene
# ===============

# ===============
#      fat
# ===============

@tabkey('entry')
class c_ffta_sect_scene_fat(c_ffta_sect_tab):
    
    _TAB_DESC = [4]

    @tabitm(0)
    def get_entry(self, ofs):
        return self.U8(ofs), self.U8(ofs+1), self.U8(ofs+2)

    @tabitm(0)
    def get_script_page(self, ofs):
        return self.U8(ofs)

    @tabitm(1)
    def get_script_idx(self, ofs):
        return self.U8(ofs)

    @tabitm(2)
    def get_text_page(self, ofs):
        return self.U8(ofs)

    def iter_lines(self):
        idx = 1
        while True:
            sp, si, tp = self.get_entry(idx)
            if tp == 0:
                break
            yield sp, si, tp
            idx += 1

# ===============
#     script
# ===============

@tabkey('page')
class c_ffta_sect_scene_script(c_ffta_sect_tab):
    _TAB_DESC = [(-4, 4), 1, (0, 4, 0, 1), (0, 0, 1, 0, 0, 1)]
    @tabitm(0)
    def get_page(self, ofs):
        page = self.sub(ofs, cls = c_ffta_sect_scene_script_page)
        page.parse()
        return page

class c_ffta_sect_scene_script_page(c_ffta_sect):

    def parse(self):
        self._line_ofs = [0]

    def _get_cmd(self, idx):
        ent = self._line_ofs[idx]
        ln = self._line_ofs[idx + 1] - ent
        cmdop = self.U8(ent)
        prms = self.BYTES(ent + 1, ln - 1)
        return cmdop, prms

    def _has_idx(self, idx):
        return idx < len(self._line_ofs) - 1

    def get_cmd(self, idx):
        if self._has_idx(idx):
            return self._get_cmd(idx)
        else:
            return None, None

    def extend_line(self):
        lst_ent = self._line_ofs[-1]
        cmdop = self.U8(lst_ent)
        cmdlen = yield cmdop
        self._line_ofs.append(lst_ent + cmdlen)

    def extend_to(self, idx):
        while not self._has_idx(idx):
            yield from self.extend_line()
        yield None

class c_ffta_sect_scene_script_cmds(c_ffta_sect_tab):
    _TAB_DESC = [6]
    @tabitm(2)
    def get_cmd_addr(self, ofs):
        return self.U32(ofs)
    @tabitm(0)
    def get_cmd_len(self, ofs):
        return self.U16(ofs)

# ===============
#      text
# ===============

@tabkey('page')
class c_ffta_sect_scene_text(c_ffta_sect_tab):
    _TAB_DESC = [4, 1]
    @tabitm(0)
    def get_page(self, ofs):
        return self.sub(ofs, cls = c_ffta_sect_scene_text_page)

@tabkey('line')
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

    def _decompress(self, dst, src_idx, dst_len):
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
        assert(len(dst) == dst_len)

    def parse(self):
        flags = self.U16(0)
        cmpr = not not (flags & 0x2)
        self.compressed = cmpr
        if cmpr:
            dst_len = rvs_endian(self.U32(2), 4, False)
            subsect = self.sub(2, 0, cls = c_ffta_sect_scene_text_buf)
            buf = self._decompress(subsect.mod, 6, dst_len)
        else:
            subsect = self.sub(2, cls = c_ffta_sect_scene_text_buf)
        self.text = subsect
        self.text.parse()

class c_ffta_sect_scene_text_buf(c_ffta_sect):

    def parse(self):
        self._cidx = 0
        self._half = False
        self._decode()
        self.raw_len = self._cidx

    def _gc(self):
        c = self.U8(self._cidx)
        self._cidx += 1
        return c

    def _getc(self):
        c = self._gc()
        if c == 1:
            self._half = True
            return self._getc()
        elif c == 0:
            return 'EOS', 0
        elif self._half:
            return 'CHR_HALF', c - 1
        elif c == 0x40:
            c = self._gc() - 0x21
            if 0 <= c < 0x58:
                return 'CTR_FUNC', c
            else:
                return 'ERR_CFUNC', c
        elif c & 0x80:
            c &= 0x7f
            c <<= 8
            c |= self._gc()
            return 'CHR_FULL', c
        else:
            return 'ERR_UNKNOWN', c

    def _decode(self):
        toks = []
        while True:
            typ, val = self._getc()
            if typ == 'EOS':
                break
            toks.append((typ, val))
        self.tokens = toks

# ===============
#      font
# ===============

class c_ffta_sect_font(c_ffta_sect_tab):

    def parse(self, info):
        self.char_shape = info['shape']
        self.half_blks = info['half']
        self.rvs_byte = info['rvsbyt']
        char_bits = 1
        for v in self.char_shape:
            char_bits *= v
        self._TAB_DESC = [char_bits // 8]

    def _get_bits(self, ofs, bidx, blen, rvs, cch):
        bb = 8
        bpos = bidx // bb
        bst = bidx % bb
        bed = bst + blen
        assert(bed <= bb)
        if bpos in cch:
            byt = cch[bpos]
        else:
            byt = self.U8(ofs + bpos)
            cch[bpos] = byt
        if rvs:
            bshft = bed
        else:
            bshft = bst
        return (byt >> bshft) & ((1 << blen) - 1)

    @tabitm(0)
    def gen_char(self, ofs, half = False):
        bs, cl, rl, bl = self.char_shape
        rvs = self.rvs_byte
        if half:
            bl = self.half_blks
        cch = {}
        for r in range(rl):
            def _rowgen():
                for b in range(bl):
                    for c in range(cl):
                        pos = ((b * rl + r) * cl + c) * bs
                        val = self._get_bits(ofs, pos, bs, rvs, cch)
                        yield val
            yield _rowgen()

# ===============
#      rom
# ===============

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
        for tab_name, tab_info in tabs_info.items():
            tab_ptr, tab_cls = tab_info[:2]
            subsect = self._subsect(tab_ptr, tab_cls)
            if len(tab_info) > 2:
                subsect.parse(tab_info[2])
            tabs[tab_name] = subsect
        self.tabs = tabs

# ===============
#      main
# ===============

def main():
    global rom_us, rom_cn, rom_jp
    with open('fftaus.gba', 'rb') as fd:
        rom_us = c_ffta_sect_rom(fd.read(), 0).parse({
            's_fat': (0x009a20, c_ffta_sect_scene_fat),
            's_scrpt': (0x1223c0, c_ffta_sect_scene_script),
            's_cmds': (0x122b10, c_ffta_sect_scene_script_cmds),
            's_text': (0x009a88, c_ffta_sect_scene_text),
            'font': (0x013474, c_ffta_sect_font, {
                'shape': (4, 8, 16, 2),
                'rvsbyt': False,
                'half': 1,
            }),
        })
    with open('fftacns.gba', 'rb') as fd:
        rom_cn = c_ffta_sect_rom(fd.read(), 0).parse({
            's_fat': (0x009a70, c_ffta_sect_scene_fat),
            's_text': (0x009ad8, c_ffta_sect_scene_text),
            'font': (0x0133f4, c_ffta_sect_font, {
                'shape': (4, 8, 16, 2),
                'rvsbyt': False,
                'half': 1,
            }),
        })
    with open('fftajp.gba', 'rb') as fd:
        rom_jp = c_ffta_sect_rom(fd.read(), 0).parse({
            's_fat': (0x009a70, c_ffta_sect_scene_fat),
            's_text': (0x009ad8, c_ffta_sect_scene_text),
            'font': (0x0133f4, c_ffta_sect_font, {
                'shape': (4, 8, 16, 2),
                'rvsbyt': False,
                'half': 1,
            }),
        })

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    
    main()
    fat = rom_us.tabs['s_fat']
    scr = rom_us.tabs['s_scrpt']
    cmd = rom_us.tabs['s_cmds']
    txt = rom_us.tabs['s_text']
    def enum_text():
        for page in range(2):
            for line in range(5):
                tl = txt[page][line]
                tl.parse()
                print(f'page: 0x{page:x} line: 0x{line:x} cmpr: {tl.compressed}')
                hd(tl.text.BYTES(0, 0x20))
    def enum_script(fat_idx, ln = 0x10):
        si = fat.get_entry(fat_idx)[:2]
        spage = scr[si[0], si[1]]
        ctx = spage.extend_to(ln - 1)
        cmdop = next(ctx)
        while not cmdop is None:
            cmdop = ctx.send(cmd.get_cmd_len(cmdop))
        for i in range(ln):
            cmdop, prms = spage.get_cmd(i)
            cmd_addr = cmd.get_cmd_addr(cmdop)
            print(f'0x{cmdop:x}(0x{cmd_addr:x}) {len(prms)} prms:')
            hd(prms)
            
