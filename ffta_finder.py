#! python3
# coding: utf-8

from ffta_sect import c_ffta_sect_tab_ref, c_ffta_sect_tab_ref_addr

INF = float('inf')

c_symb = object

class c_ffta_ref_tab_finder:

    ST_DROPALL = c_symb()
    ST_BYPASS = c_symb()
    ST_FOUND = c_symb()
    ST_SCAN = c_symb()
    ST_CHECK = c_symb()

    def __init__(self, sect, st_ofs, top_ofs, ent_width, itm_align = None):
        self.sect = sect
        self.top_ofs = top_ofs
        self.wd = ent_width
        if itm_align is None:
            itm_align = ent_width
        self.itm_align = itm_align
        self.ENT_A0 = 0
        self.ENT_AF = (1 << self.wd) - 1
        self.win = []
        self.win_st = st_ofs
        self.win_ed = st_ofs
        self.win_min = INF
        self.win_max = 0

    @property
    def win_len(self):
        l = self.win_ed - self.win_st
        assert(l == len(self.win) * self.wd)
        return l

    def _ent2ofs(ent):
        return self.win_st + ent

    def _ofs2ent(ofs):
        assert(ofs > self.win_st)
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

    def _shift_out(self, ov):
        assert(ov < self.win_len and ov % self.wd == 0)
        self.win = self.win[ov:]
        self.win_st += ov
        a0 = self.ENT_A0
        af = self.ENT_AF
        wmin = INF
        wmax = 0
        for ent in self.win:
            if ent == a0:
                continue
            elif ent == af:
                continue
            if ent < wmin:
                wmin = ent
            if ent > wmax:
                wmax = ent
        self.win_min = wmin
        self.win_max = wmax
        return self.ST_CHECK

    def _chk_itm_bot(self):
        ed_ent = self._ofs2ent(self.win_ed)
        min_ofs = self._ent2ofs(self.win_min)
        if ed_ent == min_ofs:
            return self.ST_FOUND
        elif ed_ent > min_ofs:
            ov = ed_ent - min_ofs
            if ov < self.win_len and ov % self.wd == 0:
                return self._shift_out(ov)
            else:
                #TODO drop all
                return self.ST_DROPALL
        return self.ST_SCAN

    def _drop_all(self):
        self.win = []
        self.win_st = self.win_ed
        self.win_min = INF
        self.win_max = 0
        return self.ST_SCAN

    def scan(self):
        st = self.ST_SCAN
        while self.win_ed + self.wd <= self.top_ofs:
            if st == self.ST_SCAN:
                st = self._shift_in()
            elif st == self.ST_CHECK:
                st = self._chk_itm_bot()
            elif st == self.ST_BYPASS:
                st = self.ST_SCAN
            elif st == self.ST_DROPALL:
                st = self._drop_all()
            elif st == self.ST_FOUND:
                return True, self.win_st, self.win_ed
        return False, self.win_st, self.win_ed

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom
