#! python3
# coding: utf-8

from ffta_sect import (
    c_ffta_sect_tab_ref, c_ffta_sect_tab_ref_addr,
    c_ffta_sect_text_line, c_ffta_sect_text_buf,
    c_ffta_sect_text, c_ffta_sect_text_page,
)

INF = float('inf')

c_symb = object

class c_range_holder:

    def __init__(self):
        self.rngs = []

    def _find_ridx(self, val):
        lst_ridx = -1
        lst_mx = None
        for i, rng in enumerate(self.rngs):
            mn, mx = rng
            if val < mn:
                return False, lst_ridx, i, lst_mx == val, val == mn - 1
            elif mn <= val < mx:
                return True, i, i, True, True
            else:
                lst_ridx = i
                lst_mx = mx
        return False, lst_ridx, len(self.rngs), lst_mx == val, False

    def hold(self, rng):
        rngs = self.rngs
        mn, mx = rng
        rm_ridx_rng = [None, None]
        add_rng = [None, None]
        cv1, prv_ri, nxt_ri, rm_prv, rm_nxt = self._find_ridx(mn)
        if rm_prv:
            rm_ridx_rng[0] = prv_ri
            add_rng[0] = rngs[prv_ri][0]
        else:
            rm_ridx_rng[0] = nxt_ri
            add_rng[0] = mn
        cv2, prv_ri, nxt_ri, rm_prv, rm_nxt = self._find_ridx(mx-1)
        if rm_nxt:
            rm_ridx_rng[1] = nxt_ri
            add_rng[1] = rngs[nxt_ri][1]
        else:
            rm_ridx_rng[1] = prv_ri
            add_rng[1] = mx
        rr_cmn, rr_cmx = rm_ridx_rng
        add_rng = tuple(add_rng)
        if rr_cmn == rr_cmx and cv1 and cv2:
            assert(rngs[rr_cmn] == add_rng)
            return True, True # cover, include
        elif rr_cmn > rr_cmx:
            assert(rr_cmn >= 0 and rr_cmn - rr_cmx == 1 and add_rng[0] == mn and add_rng[1] == mx)
            rngs.insert(rr_cmn, add_rng)
            return False, False # cover, include
        else:
            if rr_cmn < 0:
                rr_cmn = 0
            nrngs = rngs[:rr_cmn]
            nrngs.append(add_rng)
            nrngs.extend(rngs[rr_cmx+1:])
            self.rngs = nrngs
            return True, False # cover, include

class c_ffta_ref_addr_finder:

    def __init__(self, sect, st_ofs, top_ofs, itm_align = 1):
        self.sect = sect
        self.top_ofs = top_ofs
        self.itm_align = itm_align
        self.st_ofs = st_ofs

    def scan(self):
        cur_ofs = self.st_ofs
        sect = self.sect
        while cur_ofs + 4 <= self.top_ofs:
            adr = sect.U32(cur_ofs)
            ofs = sect._addr2offs(adr)
            if 0 <= ofs < self.top_ofs:
                yield ofs, adr, cur_ofs
            cur_ofs += 4
            

class c_ffta_ref_tab_finder:

    ST_DROPALL = c_symb()
    ST_BYPASS = c_symb()
    ST_FOUND = c_symb()
    ST_SCAN_I = c_symb()
    ST_SCAN_O = c_symb()
    ST_CHECK = c_symb()

    def __init__(self, sect, st_ofs, top_ofs, ent_width, itm_align = 1):
        self.sect = sect
        self.top_ofs = top_ofs
        self.wd = ent_width
        if itm_align is None:
            itm_align = ent_width
        self.itm_align = itm_align
        self.ENT_A0 = 0
        self.ENT_AF = (1 << self.wd * 8) - 1
        st_ofs = (st_ofs // self.wd) * self.wd
        self.win = []
        self.win_st = st_ofs
        self.win_ed = st_ofs
        self.win_min = INF
        self.win_max = 0

    def reset(self, st_ofs):
        st_ofs = (st_ofs // self.wd) * self.wd
        self.win_ed = st_ofs
        self._drop_all()

    @property
    def win_len(self):
        l = self.win_ed - self.win_st
        assert(l == len(self.win) * self.wd)
        return l // self.wd

    def _ent2ofs(self, ent):
        return self.win_st + ent

    def _ofs2ent(self, ofs):
        assert(ofs >= self.win_st)
        return ofs - self.win_st

    def _hndl_a0(self):
        return True

    def _hndl_af(self):
        return False

    def _shift_in(self):
        ent = self.sect.readval(self.win_ed, self.wd, False)
        self.win_ed += self.wd
        self.win.append(ent)
        if ent == self.ENT_A0:
            bypass = self._hndl_a0()
        elif ent == self.ENT_AF:
            bypass = self._hndl_af()
        else:
            bypass = None
        if bypass is True:
            return self.ST_BYPASS
        elif bypass is False:
            return self.ST_DROPALL
        else:
            pass
        if self._ent2ofs(ent) % self.itm_align:
            return self.ST_DROPALL
        if ent > self.win_max:
            self.win_max = ent
        if ent < self.win_min:
            self.win_min = ent
        return self.ST_CHECK

    def _shift_out(self):
        self.win_st += self.wd
        if self.win_st == self.win_ed:
            return self.ST_DROPALL
        ent = self.win.pop(0)
        a0 = self.ENT_A0
        af = self.ENT_AF
        if ent == a0 or ent == af:
            return self.ST_CHECK
        upd_min = (ent == self.win_min)
        upd_max = (ent == self.win_max)
        if not (upd_min or upd_max):
            return self.ST_CHECK
        wmin = INF
        wmax = 0
        for ent in self.win:
            if ent == a0:
                continue
            elif ent == af:
                continue
            if upd_min and ent < wmin:
                wmin = ent
            if upd_max and ent > wmax:
                wmax = ent
        if upd_min:
            self.win_min = wmin
        if upd_max:
            self.win_max = wmax
        return self.ST_CHECK

    def _chk_itm_bot(self):
        ed = self.win_ed
        wmin = self._ent2ofs(self.win_min)
        wmax = self._ent2ofs(self.win_max)
        if ed == wmin:
            return self.ST_FOUND
        elif ed > wmin or wmax >= self.top_ofs:
            return self.ST_SCAN_O
        return self.ST_SCAN_I

    def _drop_all(self):
        self.win.clear()
        self.win_st = self.win_ed
        self.win_min = INF
        self.win_max = 0
        return self.ST_SCAN_I

    def _scan(self, brk_out):
        st = self.ST_SCAN_I
        while self.win_ed + self.wd <= self.top_ofs:
            #if self.win_ed % 0x10000 == 0:
            #    print('scan', hex(self.win_ed))
            if st == self.ST_SCAN_I:
                #print('in', hex(self.win_ed))
                st = self._shift_in()
            if st == self.ST_SCAN_O:
                #print('out', hex(self.win_ed))
                if brk_out:
                    break
                st = self._shift_out()
            elif st == self.ST_CHECK:
                #print('chk', hex(self.win_ed))
                st = self._chk_itm_bot()
            elif st == self.ST_BYPASS:
                #print('bp', hex(self.win_ed))
                st = self.ST_SCAN_I
            elif st == self.ST_DROPALL:
                #print('drp', hex(self.win_ed))
                st = self._drop_all()
            elif st == self.ST_FOUND:
                yield self.win_st, self.win_ed, self.win_len, self.win_max
                st = self._shift_out()
        #yield False, self.win_st, self.win_ed, self.win_len, self.win_max

    def scan(self):
        yield from _scan(False)

    def check(self, ofs = None):
        if ofs is None:
            ofs = self.win_ed
        if ofs % self.wd:
            return False, 0, 0
        self.reset(ofs)
        for st, ed, ln, mx in self._scan(True):
            return True, ln, mx
        return False, 0, 0

class c_text_checker:

    def __init__(self, sect, tab_thrs = (0.1, 0.2, 0.2)):
        self.sect = sect
        self.rtf2 = c_ffta_ref_tab_finder(sect, 0, sect._sect_top, 2)
        self.rtf4 = c_ffta_ref_tab_finder(sect, 0, sect._sect_top, 4)
        self._bf_thr, self._pg_thr, self._tb_thr = tab_thrs

    def _chk_thr(self, v1, v2, thr):
        return v2 > 0 and v1 / v2 < thr

    def _chk_line(self, dsect):
        return self._chk_buf(dsect.text)

    def _chk_buf(self, dsect):
        return self._chk_thr(
            dsect.dec_error_cnt, len(dsect.tokens), self._bf_thr)

    def _chk_page(self, dsect):
        err_cnt = 0
        try:
            for tl in dsect:
                if not self._chk_line(tl):
                    err_cnt += 1
        except ValueError as ex:
            if ex.args[0].startswith('invalid text line:'):
                return False
            raise
        return self._chk_thr(err_cnt, dsect.tsize, self._pg_thr)

    def _chk_tab(self, dsect):
        err_cnt = 0
        for tp in dsect:
            if not self._chk_page(tp):
                err_cnt += 1
        return self._chk_thr(err_cnt, dsect.tsize, self._tb_thr)

    def check_tab(self, ofs):
        fnd, ln, mx = self.rtf4.check(ofs)
        if fnd:
            dst = self.sect.subsect(ofs, c_ffta_sect_text)
            return self._chk_tab(dst)
        return False

    def check_page(self, ofs):
        fnd, ln, mx = self.rtf2.check(ofs)
        if fnd:
            dst = self.sect.subsect(ofs, c_ffta_sect_text_page)
            return self._chk_page(dst)
        return False

    def check_line(self, ofs):
        try:
            dst = self.sect.subsect(ofs, c_ffta_sect_text_line)
        except ValueError as ex:
            if ex.args[0].startswith('invalid text line:'):
                return False
            raise
        return self._chk_line(dst)

    def check_buf(self, ofs):
        dst = self.sect.subsect(ofs, c_ffta_sect_text_buf)
        return self._chk_buf(dst)

    def check(self, ofs):
        if self.check_tab(ofs):
            return 'tab'
        elif self.check_page(ofs):
            return 'page'
        elif self.check_line(ofs):
            return 'line'
        elif self.check_buf(ofs):
            return 'buf'
        return None

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom

    def main(bs = 0):
        global fa, f2, f4, tc
        fa = c_ffta_ref_addr_finder(rom, bs, rom._sect_top)
        f2 = c_ffta_ref_tab_finder(rom, bs, rom._sect_top, 2)
        f4 = c_ffta_ref_tab_finder(rom, bs, rom._sect_top, 4)
        tc = c_text_checker(rom)
        wk = set()
        for ofs, ptr, ent in fa.scan():
            if ofs in wk:
                continue
            wk.add(ofs)
            #if ofs == 0x9c1484: breakpoint()
            r = tc.check(ofs)
            if r and not r == 'line' and not r == 'buf':
                print('found', hex(ent), hex(ptr), r)
