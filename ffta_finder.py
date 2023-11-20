#! python3
# coding: utf-8

from ffta_sect import c_ffta_sect_tab_ref, c_ffta_sect_tab_ref_addr

INF = float('inf')

c_symb = object

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
            cur_ofs += 4
            if 0 <= ofs < self.top_ofs:
                yield ofs, adr, cur_ofs
            

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
        return l

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
        ed_ent = self._ofs2ent(self.win_ed)
        wmin = self.win_min
        if ed_ent == wmin:
            return self.ST_FOUND
        elif ed_ent > wmin:
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

    def check(self, ofs):
        if ofs % self.wd:
            return False, 0, 0
        self.reset(ofs)
        for st, ed, ln, mx in self._scan(True):
            return True, ln, mx
        return False, 0, 0

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom

    def main(bs = 0):
        global fa, f2
        fa = c_ffta_ref_addr_finder(rom, bs, rom._sect_top)
        f2 = c_ffta_ref_tab_finder(rom, bs, rom._sect_top, 2)
        wk = set()
        for ofs, ptr, ent in fa.scan():
            if ofs in wk:
                continue
            wk.add(ofs)
            fnd, ln, mx = f2.check(ofs)
            if fnd:
                print('found', hex(ln), hex(ptr), hex(ofs), hex(mx))
