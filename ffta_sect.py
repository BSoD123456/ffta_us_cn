#! python3
# coding: utf-8

import os, os.path

# ===============
#     common
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

c_symb = object

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

    @property
    def accessable_top(self):
        return len(self.raw) - self.offset

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

# ===============
#   ffta spec
# ===============

class c_ffta_sect(c_mark):

    ADDR_BASE = 0x8000000

    _SECT_ALIGN = 1
    _SECT_TOP_ALIGN = 1

    def parse(self):
        pass

    def parse_size(self, top_ofs, top_align_width):
        assert(self.real_offset % self.sect_align == 0)
        self._sect_top = top_ofs
        self._sect_real_top = None
        self._sect_top_nondeterm = False
        self._sect_top_align = top_align_width

    @property
    def sect_align(self):
        return self._SECT_ALIGN

    @property
    def sect_top_align(self):
        return max(self._sect_top_align, self._SECT_TOP_ALIGN)

    @property
    def sect_top(self):
        return self._sect_top

    @property
    def sect_top_least(self):
        sect_top = self.sect_top
        if sect_top is None:
            return 0
        else:
            return sect_top

    @property
    def sect_top_nondeterm(self):
        return self._sect_top_nondeterm

    def set_nondeterm(self):
        self._sect_top_nondeterm = True

    def set_real_top(self, real_top):
        align = self._sect_top_align
        real_offset = self.real_offset
        if self._sect_top is None:
            real_offset_top = alignup(real_offset + real_top, align)
            self._sect_top = real_offset_top - real_offset
            self._sect_real_top = real_top
            return
        if 0 <= self._sect_top - real_top < align:
            self._sect_real_top = real_top
            return
        if self._sect_top_nondeterm:
            real_offset_top = alignup(real_offset + real_top, align)
            self._sect_top = real_offset_top - real_offset
            self._sect_real_top = real_top
            return
        else:
            raise ValueError('sect error: invalid real top')

    def _offs2addr(self, offs):
        return offs + self.real_offset + self.ADDR_BASE

    def _addr2offs(self, addr):
        return addr - self.ADDR_BASE - self.real_offset

    def aot(self, v, typ):
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
        return self.aot(self.U32(ptr), typ[1:])

    def repack_end(self, rmk):
        align = self.sect_top_align
        ac_top = rmk.accessable_top
        align_top = alignup(ac_top, align)
        add_top = align_top - ac_top
        if add_top > 0:
            rmk.WBYTES(bytes(add_top), ac_top)
        rmk.parse_size(align_top, align)
        rmk.parse()

# ===============
#      tabs
# ===============

class c_ffta_sect_tab(c_ffta_sect):
    _TAB_WIDTH = 1
    _TAB_ALIGN = INF
    @property
    def sect_align(self):
        wd = self._TAB_WIDTH
        if wd % 4 == 0:
            a = 4
        elif wd % 2 == 0:
            a = 2
        else:
            a = 1
        return max(self._SECT_ALIGN, a)
    def parse_size(self, top_ofs, top_align_width):
        super().parse_size(top_ofs, top_align_width)
        if top_ofs is None:
            self.tsize = INF
        else:
            self.tsize = top_ofs // self._TAB_WIDTH
    def tbase(self, idx):
        return idx * self._TAB_WIDTH

def tabitm(ofs = 0, part = None):
    def _mod(mth):
        def _wrap(self, idx, *args, **kargs):
            bs = self.tbase(idx)
            return mth(self, bs + ofs, *args, **kargs)
        return _wrap
    return _mod

def tabkey(key):
    mn = 'get_' + key
    def _mod(cls):
        def _getkey(self, k):
            if k >= self.tsize:
                raise IndexError('overflow')
            if hasattr(self, '_tab_cch'):
                cch = self._tab_cch
            else:
                cch = {}
                self._tab_cch = cch
            if k in cch:
                val = cch[k]
            else:
                val = getattr(self, mn)(k)
                cch[k] = val
            return val
        cls.__getitem__ = _getkey
        return cls
    return _mod

@tabkey('ref')
class c_ffta_sect_tab_ref(c_ffta_sect_tab):
    
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect
    
    @tabitm()
    def get_entry(self, ofs):
        return self.readval(ofs, self._TAB_WIDTH, False)

    @property
    def last_idx(self):
        try:
            return self._last_idx
        except:
            pass
        _last_idx = 0
        _last_ofs = 0
        for i in range(self.tsize):
            sofs = self.get_entry(i)
            if sofs >= _last_ofs:
                _last_ofs = sofs
                _last_idx = i
        self._last_idx = _last_idx
        return _last_idx

    def _is_last(self, idx):
        return idx == self.last_idx

    def _ref_top_nondeterm(self, idx):
        return self._sect_top_nondeterm and self._is_last(idx)

    def _init_ref(self, sub, idx, ofs):
        try:
            top_ofs = self._tab_ref_size[idx]
        except:
            top_ofs = None
        if isinstance(sub, c_ffta_sect_tab_ref_sub):
            sub.set_sub_offset(ofs)
        if self._is_last(idx):
            top_align = self.sect_top_align
        else:
            top_align = sub.sect_align
        sub.parse_size(top_ofs, top_align)
        if self._ref_top_nondeterm(idx):
            sub.set_nondeterm()
        sub.parse()

    @property
    def sect_top(self):
        if not self._sect_top is None:
            return self._sect_top
        if not self.tsize:
            return None
        lst_sub = self[self.last_idx]
        lst_top = lst_sub.sect_top
        if lst_top is None:
            return None
        real_top = lst_sub.real_offset - self.real_offset + lst_top
        self.set_real_top(real_top)
        return self._sect_top

    @property
    def sect_top_least(self):
        sect_top = self.sect_top
        if not sect_top is None:
            return sect_top
        if not self.tsize:
            return None
        lst_sub = self[self.last_idx]
        return lst_sub.real_offset - self.real_offset + lst_sub.sect_top_least
    
    def get_ref(self, idx):
        ofs = self.get_entry(idx)
        clss = self._TAB_REF_CLS()
        if isinstance(clss, list):
            first_err = None
            for cls in clss:
                sub = self.sub(ofs, cls = cls)
                try:
                    self._init_ref(sub, idx, ofs)
                    break
                except ValueError as ex:
                    if first_err is None:
                        first_err = ex
            else:
                assert(first_err)
                raise first_err
        else:
            sub = self.sub(ofs, cls = clss)
            self._init_ref(sub, idx, ofs)
        return sub

    @property
    def _tab_acs_top(self):
        return self.accessable_top

    def _guess_size(self, top_ofs, upd_sz):
        assert(upd_sz or self.tsize < INF)
        cur_ent = 0
        ofs_min = INF
        ofs_ord = []
        ofs_sort = set()
        acs_top = self._tab_acs_top
        while cur_ent < self.tsize:
            ofs = self.get_entry(cur_ent)
            if ofs < 0:
                raise ValueError('invalid ref tab: tab entry not in range')
            skip = (ofs == 0)
            if (cur_ent * self._TAB_WIDTH == ofs_min or
                (not top_ofs is None and ofs == top_ofs) or
                # all F entry is invalid and last
                (ofs == (1 << self._TAB_WIDTH * 8) - 1)):
                if upd_sz:
                    self.tsize = cur_ent
                    break
                else:
                    skip = True
            elif (cur_ent * self._TAB_WIDTH > ofs_min or
                ofs >= acs_top or
                (not top_ofs is None and ofs > top_ofs) ):
                raise ValueError('invalid ref tab: tab entry not in range')
            cur_ent += 1
            if 0 < ofs < ofs_min:
                ofs_min = ofs
            ofs_ord.append(ofs)
            if not skip:
                ofs_sort.add(ofs)
        if not ofs_sort:
            raise ValueError('invalid ref tab: empty entries')
        ofs_sort = sorted(ofs_sort)
        rslt = []
        for ofs in ofs_ord:
            if ofs == 0:
                rslt.append(0)
                continue
            i = ofs_sort.index(ofs)
            try:
                nxt_ofs = ofs_sort[i+1]
            except:
                nxt_ofs = top_ofs
            try:
                sz = nxt_ofs - ofs
            except:
                sz = None
            rslt.append(sz)
        return rslt

    def parse_size(self, top_ofs, top_align_width):
        super().parse_size(top_ofs, top_align_width)
        self._tab_ref_size = self._guess_size(top_ofs, True)

    def _iter_item(self, path, skiprep):
        wkofs = {}
        for i, sub in enumerate(self):
            npath = path + [i]
            if skiprep and sub:
                sofs = sub.real_offset
                if sofs in wkofs:
                    yield npath, wkofs[sofs]
                    continue
                wkofs[sofs] = npath
            if isinstance(sub, c_ffta_sect_tab_ref):
                yield from sub._iter_item(npath, skiprep)
            else:
                yield npath, sub

    def iter_item(self, skiprep = False):
        yield from self._iter_item([], skiprep)

class c_ffta_sect_tab_ref_sub(c_ffta_sect_tab_ref):
    def set_sub_offset(self, ofs):
        self._tab_ref_sub_offset = ofs
    def get_entry(self, idx):
        return super().get_entry(idx) - self._tab_ref_sub_offset

class c_ffta_sect_tab_ref_addr(c_ffta_sect_tab_ref):
    
    _TAB_WIDTH = 4
    
    def set_info(self, host, tlen, hole_idxs = None):
        self._tab_ref_host = host
        self.tsize = tlen
        if hole_idxs is None:
            hole_idxs = []
        self._tab_hole_idxs = hole_idxs
        
    def _ref_top_nondeterm(self, idx):
        return True

    @property
    def _tab_acs_top(self):
        return self._tab_ref_host.accessable_top
    
    def get_entry(self, idx):
        addr = super().get_entry(idx)
        if addr:
            ofs = self._tab_ref_host.aot(addr, 'ao')
        else:
            ofs = 0
        return ofs
    
    def get_ref(self, idx):
        ofs = self.get_entry(idx)
        if ofs:
            ref = self._tab_ref_host.sub(ofs, cls = self._TAB_REF_CLS())
            self._init_ref(ref, idx, ofs)
        else:
            ref = None
        return ref
    
    def parse_size(self, top_ofs, top_align_width):
        super(c_ffta_sect_tab, self).parse_size(top_ofs, top_align_width)
        tbsz = self._guess_size(top_ofs, False)
        for i in self._tab_hole_idxs:
            if i < len(tbsz):
                tbsz[i] = None
        self._tab_ref_size = tbsz
        self.set_nondeterm()

# ===============
#     scene
# ===============

# ===============
#      fat
# ===============

class c_ffta_sect_scene_fat(c_ffta_sect_tab):
    
    _TAB_WIDTH = 4

    @tabitm()
    def get_entry(self, ofs):
        return self.U8(ofs) - 1, self.U8(ofs+1), self.U8(ofs+2)

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

# ===============
#     scene
# ===============

class c_ffta_sect_scene_script(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 4
    # delay reference class symbol
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_scene_script_group

class c_ffta_sect_scene_script_group(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 4
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_script_page

# ===============
#     battle
# ===============

class c_ffta_sect_battle_script(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 2
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_battle_script_group

class c_ffta_sect_battle_script_group(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 2
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_script_page

# ===============
#   script page
# ===============

class c_ffta_sect_script_page(c_ffta_sect):

    def parse(self):
        super().parse()
        self._line_ofs = [0]

    def _get_prms(self, cofs, clen):
        r = self.BYTES(cofs + 1, clen - 1)
        return r

    def _get_cmd(self, idx):
        ent = self._line_ofs[idx]
        ln = self._line_ofs[idx + 1] - ent
        cmdop = self.U8(ent)
        prms = self._get_prms(ent, ln)
        return ent, cmdop, prms

    def get_cmd(self, ofs):
        ln_ofs = self._line_ofs
        try:
            idx = ln_ofs.index(ofs)
        except:
            return None, None, None
        if idx >= len(ln_ofs) - 1:
            return None, None, None
        return self._get_cmd(idx)

    def _extend_line(self):
        lst_ent = self._line_ofs[-1]
        cmdop = self.U8(lst_ent)
        cmdlen_ctx = [None]
        def prmsfunc(n):
            cmdlen_ctx[0] = n
            if n is None:
                return None
            return self._get_prms(lst_ent, n)
        yield False, lst_ent, cmdop, prmsfunc
        cmdlen = cmdlen_ctx[0]
        if cmdlen is None:
            return False
        self._line_ofs.append(lst_ent + cmdlen)
        return True

    def iter_lines_to(self, ofs):
        ln_ofs = self._line_ofs
        llen = len(ln_ofs)
        if llen > 1:
            for cur_ln in range(llen - 1):
                cur_ofs = ln_ofs[cur_ln]
                if not ofs is None and cur_ofs > ofs:
                    return
                yield True, *self._get_cmd(cur_ln)
        while ofs is None or ln_ofs[-1] <= ofs:
            _done = yield from self._extend_line()
            if not _done:
                break

# ===============
#    commands
# ===============

class c_ffta_sect_script_cmds(c_ffta_sect_tab):
    _TAB_WIDTH = 6
    @tabitm(2)
    def get_cmd_addr(self, ofs):
        return self.U32(ofs)
    @tabitm(0)
    def get_cmd_len(self, ofs):
        return self.U16(ofs)

# ===============
#      text
# ===============

class c_ffta_sect_text(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 4
    @staticmethod
    def _TAB_REF_CLS():
        return [c_ffta_sect_text_page, c_ffta_sect_text_sub]

class c_ffta_sect_text_sub(c_ffta_sect_tab_ref_sub):
    _TAB_WIDTH = 4
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_text_page

class c_ffta_sect_fixed_text(c_ffta_sect_tab_ref_addr):
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_text_page

class c_ffta_sect_words_text(c_ffta_sect_tab_ref_addr):
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_text_buf

class c_ffta_sect_text_page(c_ffta_sect_tab_ref):
    _TAB_WIDTH = 2
    _SECT_TOP_ALIGN = 4
    @staticmethod
    def _TAB_REF_CLS():
        return c_ffta_sect_text_line

class c_ffta_sect_text_line(c_ffta_sect):
    
    _SECT_ALIGN = 2
    
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
        return src_idx

    def parse(self):
        super().parse()
        flags = self.U16(0)
        cmpr = not not (flags & 0x2)
        cls_buf = (c_ffta_sect_text_buf, c_ffta_sect_text_buf_ya)[flags & 0x1]
        self.compressed = cmpr
        warn_cnt = 0
        if cmpr:
            dst_len = rvs_endian(self.U32(2), 4, False)
            if dst_len == 0:
                raise ValueError('invalid text line: decompress nothing')
            subsect = self.sub(2, 0, cls = cls_buf)
            try:
                src_len = self._decompress(subsect.mod, 6, dst_len)
            except:
                raise ValueError('invalid text line: decompress error')
            subsect.parse_size(dst_len, self.sect_top_align)
        else:
            subsect = self.sub(2, cls = cls_buf)
            if self.sect_top is None:
                _st = None
            else:
                _st = self.sect_top - 2
            subsect.parse_size(_st, self.sect_top_align)
            if self.sect_top_nondeterm:
                subsect.set_nondeterm()
        subsect.parse()
        self.text = subsect
        if not cmpr and subsect:
            src_len = subsect.raw_len + 2
        self.set_real_top(src_len)
        self.raw_len = src_len
        self.warn_cnt = warn_cnt

class c_ffta_sect_text_buf(c_ffta_sect):

    _CTR_TOKBASE = 0x21
    _CTR_TOKLEN = [
        # read 2
        [0x40, 0x41, 0x42, 0x4a, 0x4d, 0x4f, 0x52, 0x54, 0x56, 0x57, 0x58],
        # read 3
        [0x00, 0x1b, 0x1d, 0x46, 0x4b, 0x51, 0x53, 0x32, 0x04],
        # read 4
        [0x45],
    ]
    # read 3 but spec
    _CTR_TOKSPEC = [0x32, 0x04]

    def parse(self):
        super().parse()
        self._cidx = 0
        self._half = False
        self._directly = 0
        self._make_ctr_tab()
        self.dec_error_cnt = 0
        self._decode()

    def _make_ctr_tab(self):
        ctr_tab = {}
        ctr_spec_tab = {}
        for i, ctis in enumerate(self._CTR_TOKLEN):
            for cti in ctis:
                ctr_tab[cti] = i
        for cti in self._CTR_TOKSPEC:
            ctr_spec_tab[cti] = getattr(self, f'_get_ctr_{cti:0>2x}')
        self._ctr_tab = ctr_tab
        self._ctr_spec_tab = ctr_spec_tab

    def _gc(self):
        c = self.U8(self._cidx)
        self._cidx += 1
        return c

    def _bc(self):
        self._cidx -= 1

    def _directly_mode(self, n):
        if self._directly != 0:
            self.dec_error_cnt += 1
        self._directly = n

    # replace ctrl, hero's name do nothing, but others fill dest buff
    # only care src, ignore
    def _get_ctr_04(self):
        return self._gc() | 0x400

    # directly copy 2 strings
    def _get_ctr_32(self):
        self._directly_mode(2)
        return self._gc() | 0x3200

    def _get_tok(self):
        c = self._gc()
        if c == 0:
            if self._directly > 0:
                self._directly -= 1
                return 'CTR_EOS', 0
            else:
                return 'EOS', 0
        if c == 1:
            self._half = True
            return self._get_tok()
        elif self._half:
            return 'CHR_HALF', c - 1
        elif c == 0x40:
            c = self._gc() - self._CTR_TOKBASE
            if c in self._ctr_spec_tab:
                func = self._ctr_spec_tab[c]
                c = func()
                return 'CTR_FUNC', c
            elif c in self._ctr_tab:
                cmlen = self._ctr_tab[c]
                for _ in range(cmlen):
                    c <<= 8
                    c |= self._gc()
                return 'CTR_FUNC', c
            self._bc()
            self.dec_error_cnt += 1
            return 'ERR_CFUNC', c
        elif c & 0x80:
            c &= 0x7f
            c <<= 8
            c |= self._gc()
            return 'CHR_FULL', c
        else:
            self.dec_error_cnt += 1
            return 'ERR_UNKNOWN', c

    def _decode(self):
        toks = []
        top_ofs = self.sect_top
        while top_ofs is None or self._cidx < top_ofs:
            typ, val = self._get_tok()
            if typ == 'EOS':
                break
            toks.append((typ, val))
        if not top_ofs is None:
            if self._cidx > top_ofs:
                self.cidx = top_ofs
            while self._cidx < top_ofs:
                c = self._gc()
                if c != 0:
                    self._bc()
                    break
        self.tokens = toks
        self.raw_len = self._cidx
        if self.dec_error_cnt > 0:# and not self.sect_top_nondeterm:
            raise ValueError('invalid text buf: decode error')
        self.set_real_top(self.raw_len)

    def _encode_tok(self, buf, tok):
        ttyp, tchr = tok
        if ttyp.startswith('CHR_'):
            ch = ((tchr >> 8) & 0x7f)
            cl = (tchr & 0xff)
            buf.append(ch | 0x80)
            buf.append(cl)
        elif ttyp == 'CTR_FUNC':
            tseq = []
            cchr = tchr
            while cchr:
                tseq.append(cchr & 0xff)
                cchr >>= 8
            cmd = tseq.pop()
            assert cmd in self._ctr_tab and self._ctr_tab[cmd] == len(tseq)
            buf.append(0x40)
            buf.append(cmd + self._CTR_TOKBASE)
            for tc in reversed(tseq):
                buf.append(tc)
        elif ttyp == 'CTR_EOS':
            buf.append(0)
        else:
            raise ValueError(f'invalid token type to encode: {ttyp}')

    def _encode(self, toks):
        buf = []
        for tok in toks:
            self._encode_tok(buf, tok)
        buf.append(0)
        return buf

    def repack_with(self, toks):
        buf = self._encode(toks)
        rmk = self.sub(0, 0, cls = c_ffta_sect_text_buf)
        rmk.WBYTES(bytearray(buf), 0)
        self.repack_end(rmk)
        return rmk

class c_ffta_sect_text_buf_ya(c_ffta_sect_text_buf):

    _CTR_TRANS = [
        0x4,  0x46, 0x4b, 0x45,
        0x45, None, 0x53, 0x51,
        0x4d, 0x52, 0x42, 0x57,
        0x54, 0x40, 0x4f, 0x41,
        0x56, 0x4a, None, 0x1b,
        0x1d, 0x58, 0x0
    ]

    _CTR_TOKSPEC = [0x3, 0x4]

    def _get_ctr_03(self):
        return self._gc() | 0x454c00

    def _get_ctr_04(self):
        return self._gc() | 0x455200
    
    def _get_tok(self):
        c = self._gc()
        if c == 0xff:
            return 'EOS', 0
        if c & 0x80:
            c -= 0x80
            if c in self._ctr_spec_tab:
                func = self._ctr_spec_tab[c]
                c = func()
                return 'CTR_FUNC', c
            try:
                c = self._CTR_TRANS[c]
            except:
                c = None
            if c is None:
                self.dec_error_cnt += 1
                return 'ERR_CFUNC', c
            if c in self._ctr_tab:
                cmlen = self._ctr_tab[c]
                for _ in range(cmlen):
                    c <<= 8
                    c |= self._gc()
                return 'CTR_FUNC', c
            self.dec_error_cnt += 1
            return 'ERR_CFUNC', c
        else:
            return 'CHR_HALF', self._gc()

# ===============
#      font
# ===============

class c_ffta_sect_font(c_ffta_sect_tab):

    def set_info(self, info):
        self.char_shape = info['shape']
        self.rvs_byte = info['rvsbyt']
        char_bits = 1
        for v in self.char_shape:
            char_bits *= v
        self._TAB_WIDTH = char_bits // 8

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

    @tabitm()
    def gen_char(self, ofs):
        bs, cl, rl, bl = self.char_shape
        rvs = self.rvs_byte
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

    ARG_SELF = c_symb()

    def setup(self, tabs_info, rom_ed = None):
        self.set_info(tabs_info)
        self.parse_size(rom_ed, 1)
        self.parse()
        return self

    def patch(self, patchs):
        for ofs, val in patchs.items():
            if isinstance(val, str):
                cmd, *cvals = val.split(':')
                if cmd == 'shft':
                    clen = int(cvals[0], 16)
                    cval = int(cvals[1], 16)
                    while cval > 0:
                        for i in range(ofs + clen - 1, ofs - 1, -1):
                            self.W8(self.U8(i), i+1)
                        self.W8(0, ofs)
                        cval -= 1
                    while cval < 0:
                        for i in range(ofs, ofs + clen):
                            self.W8(self.U8(i+1), i)
                        cval += 1
                else:
                    raise NotImplementedError
            else:
                self.W8(val, ofs)
        return self

    def set_info(self, tabs_info):
        self._add_tabs(tabs_info)

    def _subsect(self, offs, c_sect, pargs, nondet = False):
        sect = self.sub(offs, cls = c_sect)
        if pargs:
            sect.set_info(*pargs)
        sect.parse_size(None, 1)
        if nondet:
            sect.set_nondeterm()
        sect.parse()
        return sect

    def subsect(self, offs, c_sect, *pargs, **kargs):
        return self._subsect(offs, c_sect, pargs, **kargs)

    def _subsect_ptr(self, offs_ptr, c_sect, pargs):
        offs_base = self.rdptr(offs_ptr, 'oao')
        return self._subsect(offs_base, c_sect, pargs)

    def _add_tabs(self, tabs_info):
        tabs = {}
        for tab_name, tab_info in tabs_info.items():
            tab_ptr, tab_cls = tab_info[:2]
            if len(tab_info) > 2:
                pargs = (self if a == self.ARG_SELF else a for a in tab_info[2:])
            else:
                pargs = None
            subsect = self._subsect_ptr(tab_ptr, tab_cls, pargs)
            tab_gidx = tab_name.split(':')
            if len(tab_gidx) > 1:
                if tab_gidx[0] in tabs:
                    t_grp = tabs[tab_gidx[0]]
                else:
                    t_grp = {}
                    tabs[tab_gidx[0]] = t_grp
                t_grp[tab_gidx[1]] = subsect
            else:
                tabs[tab_name] = subsect
        self.tabs = tabs

# ===============
#      main
# ===============

def _words_sect_info(info):
    return {
        'words:'+k: (ofs, c_ffta_sect_words_text,
            c_ffta_sect_rom.ARG_SELF, sz,
        )
        for k, (ofs, sz) in info.items()}

def _trim_raw_len(raw, st):
    for i in range(min(st, len(raw) - 1), -1, -1):
        b = raw[i]
        if b != 0xff:
            break
    return alignup(i, 0x10)

def load_rom_us(fn):
    with open(fn, 'rb') as fd:
        raw = fd.read()
        return c_ffta_sect_rom(raw, 0).setup({
            's_fat': (0x009a20, c_ffta_sect_scene_fat),
            's_scrpt': (0x1223c0, c_ffta_sect_scene_script),
            's_cmds': (0x122b10, c_ffta_sect_script_cmds),
            's_text': (0x009a88, c_ffta_sect_text),
            'b_scrpt': (0x00a148, c_ffta_sect_battle_script),
            'b_cmds': (0x00a19c, c_ffta_sect_script_cmds),
            'b_text': (0x237f4, c_ffta_sect_text_page),
            #'ico_text': (0x13c84, c_ffta_sect_text_page),
            'font': (0x013474, c_ffta_sect_font, {
                'shape': (4, 8, 16, 2),
                'rvsbyt': False,
            }),
            'fx_text': (0x018050, c_ffta_sect_fixed_text,
                c_ffta_sect_rom.ARG_SELF, 27,
            ),
            **_words_sect_info({
                'ico': (0x198d0, 0xa),
                'uitm': (0x538b8, 0x4),
                'content': (0x18da4, 0x2f2),
                'name1': (0x9a08, 0x6b),
                'battle': (0x9028, 0x301),
                'rumor': (0x5fd9c, 0x5c),
                'quest': (0x191f0, 0x20f),
                'clan': (0x9a10, 0x80),
                'system': (0x39f54, 0x54),
                'name2': (0xc9ed0, 0x2d5),
                'title': (0x192bc, 0x34),
            }),
        }, _trim_raw_len(raw, 0xf00000))

def load_rom_jp(fn):
    with open(fn, 'rb') as fd:
        raw = fd.read()
        return c_ffta_sect_rom(raw, 0).setup({
            's_fat': (0x009a70, c_ffta_sect_scene_fat),
            's_scrpt': (0x1178a8, c_ffta_sect_scene_script),
            's_cmds': (0x117f10, c_ffta_sect_script_cmds),
            's_text': (0x009ad8, c_ffta_sect_text),
            'b_scrpt': (0x00a0dc, c_ffta_sect_battle_script),
            'b_cmds': (0x00a130, c_ffta_sect_script_cmds),
            'b_text': (0x23698, c_ffta_sect_text_page),
            #'ico_text': (0x13bfc, c_ffta_sect_text_page),
            'font': (0x0133f4, c_ffta_sect_font, {
                'shape': (4, 8, 16, 2),
                'rvsbyt': False,
            }),
            'fx_text': (0x017f6c, c_ffta_sect_fixed_text,
                c_ffta_sect_rom.ARG_SELF, 26,
            ),
            **_words_sect_info({
                'uitm': (0x5113c, 0x4),
                'utitle': (0x558f8, 0x5),
                'content': (0x18cb4, 0x2f2),
                'name1': (0x9a58, 0x68),
                'battle': (0x9070, 0x2f5),
                'rumor': (0x5c954, 0x5c),
                'quest': (0x19100, 0x20f),
                'clan': (0x9a60, 0x80),
                'system': (0x3a560, 0x49),
                'name2': (0xc10c0, 0x80),
                'title': (0x191cc, 0x34),
            }),
        }, _trim_raw_len(raw, 0xf00000))

def load_rom_cn(fn):
    rom = load_rom_jp(fn)
    rom.patch({
        # wrong ctrl-tok
        0x48cd3f: 0x25,
        # missing 0
        0x9761eb: 'shft:50:1',
        # surplus 0
        0x987bdf: 'shft:8:-2',
    })
    return rom

load_rom = {
    'us': load_rom_us,
    'jp': load_rom_jp,
    'cn': load_rom_cn,
}

def main():
    global rom_us, rom_cn, rom_jp
    rom_us = load_rom_us('fftaus.gba')
    rom_cn = load_rom_cn('fftacnb.gba')
    rom_jp = load_rom_jp('fftajp.gba')

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    main()

    from ffta_charset import c_ffta_charset_ocr
    chs_us = chs_jp = c_ffta_charset_ocr('charset_us.json', None)
    chs_us.load()
    chs_cn = c_ffta_charset_ocr('charset_cn.json', rom_cn)
    chs_cn.load()
    
    fat = rom_us.tabs['s_fat']
    scr = rom_us.tabs['s_scrpt']
    cmd = rom_us.tabs['s_cmds']
    txt = rom_us.tabs['s_text']
    bat = rom_us.tabs['b_scrpt']
    bcm = rom_us.tabs['b_cmds']
    def enum_text():
        for page in range(2):
            for line in range(5):
                tl = txt[page][line]
                tl.parse()
                print(f'page: 0x{page:x} line: 0x{line:x} cmpr: {tl.compressed}')
                hd(tl.text.BYTES(0, 0x20))
    def enum_script(fat_idx, mofs = 0x3f):
        si = fat.get_entry(fat_idx)[:2]
        spage = scr[si[0], si[1]]
        for rdy, cofs, cop, cprms in spage.iter_lines_to(mofs):
            if not rdy:
                clen = cmd.get_cmd_len(cop)
                cprms = cprms(clen)
            cmd_addr = cmd.get_cmd_addr(cop)
            print(f'{str(rdy):>5s} 0x{cofs:x}: 0x{cop:x}(0x{cmd_addr:x}) {len(cprms)} cprms:')
            hd(cprms)
    def enum_b_script(p_idx, mofs = 0x3f):
        spage = bat[p_idx, 1]
        for rdy, cofs, cop, cprms in spage.iter_lines_to(mofs):
            if not rdy:
                clen = bcm.get_cmd_len(cop)
                cprms = cprms(clen)
            cmd_addr = bcm.get_cmd_addr(cop)
            print(f'{str(rdy):>5s} 0x{cofs:x}: 0x{cop:x}(0x{cmd_addr:x}) {len(cprms)} cprms:')
            hd(cprms)
            
