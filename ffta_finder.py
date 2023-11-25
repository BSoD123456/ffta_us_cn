#! python3
# coding: utf-8

from ffta_sect import (
    c_ffta_sect_tab_ref, c_ffta_sect_tab_ref_addr,
    c_ffta_sect_text_line, c_ffta_sect_text_buf,
    c_ffta_sect_text, c_ffta_sect_text_page,
    c_ffta_sect_fixed_text, c_ffta_sect_words_text,
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

    def _hold(self, rng, upd):
        rngs = self.rngs
        mn, mx = rng
        rm_ridx_rng = [None, None]
        add_rng = [None, None]
        adj_cnt = 0
        cv1, prv_ri, nxt_ri, rm_prv, rm_nxt = self._find_ridx(mn)
        if rm_prv:
            rm_ridx_rng[0] = prv_ri
            add_rng[0] = rngs[prv_ri][0]
            if not cv1:
                adj_cnt += 1
        else:
            rm_ridx_rng[0] = nxt_ri
            add_rng[0] = mn
        cv2, prv_ri, nxt_ri, rm_prv, rm_nxt = self._find_ridx(mx-1)
        if rm_nxt:
            rm_ridx_rng[1] = nxt_ri
            add_rng[1] = rngs[nxt_ri][1]
            if not cv2:
                # adj ridx can not be the same
                # so just use 1 counter
                adj_cnt += 1
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
            if upd:
                rngs.insert(rr_cmn, add_rng)
            return False, False # cover, include
        else:
            if rr_cmn < 0:
                rr_cmn = 0
            inner_cnt = rr_cmx - rr_cmn + 1 - adj_cnt
            assert(inner_cnt >= 0)
            if upd:
                nrngs = rngs[:rr_cmn]
                nrngs.append(add_rng)
                nrngs.extend(rngs[rr_cmx+1:])
                self.rngs = nrngs
            return inner_cnt > 0, False # cover, include

    def hold(self, rng):
        return self._hold(rng, True)

    def peek(self, rng):
        return self._hold(rng, False)

    def peek1(self, ofs):
        return self.peek((ofs, ofs+1))

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

class c_ffta_ref_addr_hold_finder(c_ffta_ref_addr_finder):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.holder = c_range_holder()
        self._pre_scan()

    def _is_ptr(self, ent):
        adr = self.sect.U32(ent)
        ofs = self.sect._addr2offs(adr)
        return 0 <= ofs < self.top_ofs, ofs, adr == 0

    def _pre_scan(self, adrtab_min = 5):
        adrtab_min_sz = adrtab_min * 4
        cur_ofs = self.st_ofs
        rvs_tab = {}
        ptr_tab = {}
        itm_tab = set()
        while cur_ofs + 4 <= self.top_ofs:
            cur_ent = cur_ofs
            while not (cur_ent in ptr_tab or cur_ent in itm_tab):
                is_ptr, nxt_ent, is_null = self._is_ptr(cur_ent)
                if is_ptr:
                    #self.holder.hold((cur_ent, cur_ent + 4)) # too slow
                    ptr_tab[cur_ent] = nxt_ent
                    if not nxt_ent in rvs_tab:
                        rvs_tab[nxt_ent] = []
                    rvs_tab[nxt_ent].append(cur_ent)
                else:
                    if is_null:
                        ptr_tab[cur_ent] = None
                    if cur_ent != cur_ofs:
                        itm_tab.add(cur_ent)
                    break
                cur_ent = nxt_ent
            cur_ofs += 4
        adr_tab = []
        ptr_sort = sorted(k for k in ptr_tab)
        lst_mn = None
        lst_ofs = 0
        # insert another last ptr to handle the real last one
        _af = (1 << 32) - 1
        ptr_sort.append(_af)
        for ofs in ptr_sort:
            if not ofs < _af:
                continue
            ofs_p = ptr_tab[ofs]
            if not ofs_p is None and not ofs_p in itm_tab:
                continue
            is_rng = False
            if ofs == lst_ofs + 4:
                if lst_mn is None:
                    lst_mn = lst_ofs
            elif not lst_mn is None:
                mn = lst_mn
                mx = lst_ofs + 4
                lst_mn = None
                is_rng = True
            lst_ofs = ofs
            if not is_rng:
                continue
            if mx - mn < adrtab_min_sz:
                continue
            lst_dofs = None
            for dofs in range(mn, mx, 4):
                if not dofs in rvs_tab:
                    continue
                if not lst_dofs is None and dofs - lst_dofs >= adrtab_min_sz:
                    adr_tab.append((lst_dofs, dofs))
                lst_dofs = dofs
            if not lst_dofs is None and mx - lst_dofs >= adrtab_min_sz:
                adr_tab.append((lst_dofs, mx))
        self.ptr_tab = ptr_tab
        self.rvs_tab = rvs_tab
        self.itm_tab = itm_tab
        self.adr_tab = adr_tab

    def scan_adrtab(self, adrtab_min = 5):
        self._last_hold = None
        rmati = []
        for ati, (mn, mx) in enumerate(self.adr_tab):
            yield mn, mx
            if mn == self._last_hold:
                rmati.append(ati)
        for ati in reversed(rmati):
            self.adr_tab.pop(ati)
        
    def scan(self):
        self._last_hold = None
        for ofs in sorted(self.itm_tab):
            cv, incld = self.holder.peek1(ofs)
            if cv:
                continue
            yield ofs
            if ofs == self._last_hold:
                self.itm_tab.remove(ofs)

    def hold(self, ofs, top):
        if top is None:
            top = 1
        self.holder.hold((ofs, ofs + top))
        self._last_hold = ofs

class c_ffta_ref_tab_finder:

    ST_DROPALL = c_symb()
    ST_BYPASS = c_symb()
    ST_FOUND = c_symb()
    ST_SCAN_I = c_symb()
    ST_SCAN_O = c_symb()
    ST_CHECK = c_symb()
    ST_CHECK_DROP = c_symb()

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
            return self.ST_CHECK_DROP
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
            elif st == self.ST_CHECK_DROP:
                #print('chkdrp', hex(self.win_ed))
                st = self._chk_itm_bot()
                if st != self.ST_FOUND:
                    st = self.ST_DROPALL
            elif st == self.ST_BYPASS:
                #print('bp', hex(self.win_ed))
                st = self.ST_SCAN_I
            elif st == self.ST_DROPALL:
                #print('drp', hex(self.win_ed))
                if brk_out:
                    break
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

    def __init__(self, sect, thrs = (2, 3, 9, 7)):
        self.sect = sect
        self.rtf2 = c_ffta_ref_tab_finder(sect, 0, sect._sect_top, 2)
        self.rtf4 = c_ffta_ref_tab_finder(sect, 0, sect._sect_top, 4)
        self._thrs = thrs

    def _chk_tab(self, ofs, cls):
        try:
            dst = rom.subsect(ofs, cls)
            for i in dst.iter_item():
                pass
        except:
            return False, None, None, None
        sz = dst.sect_top
        if sz is None:
            assert(dst.tsize < 2)
            return False, dst, dst.tsize, None
        return True, dst, dst.tsize, sz

    def _chk_item(self, ofs, cls):
        try:
            dst = rom.subsect(ofs, cls)
        except:
            return False, None, None, None
        sz = dst.sect_top
        if sz is None:
            return False, dst, None, None
        return True, dst, sz, sz

    def check(self, ofs, typ):
        cls = (
            c_ffta_sect_text, c_ffta_sect_text_page,
            c_ffta_sect_text_line, c_ffta_sect_text_buf)
        for i, dtyp in enumerate((1, 2, 4, 8)):
            if not (typ & dtyp):
                continue
            if dtyp & 0x1:
                fnd, ln, mx = self.rtf4.check(ofs)
            elif dtyp & 0x2:
                fnd, ln, mx = self.rtf2.check(ofs)
            else:
                fnd = True
            if not fnd:
                continue
            if dtyp & 0x3:
                r = self._chk_tab(ofs, cls[i])
            else:
                r = self._chk_item(ofs, cls[i])
            if r[0] and r[2] >= self._thrs[i]:
                return r
        return False, None, None, None

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom

    from ffta_charset import c_ffta_charset_us_dummy as c_charset
    
    chs = c_charset()
    
    def main(bs = 0):
        global fa, tc
        fa = c_ffta_ref_addr_hold_finder(rom, bs, rom._sect_top)
        tc = c_text_checker(rom)
        for cls in [c_ffta_sect_fixed_text, c_ffta_sect_words_text]:
            print(f'scan adrtab for {cls.__name__}')
            for mn, mx in fa.scan_adrtab():
                sz = mx - mn
                ln = sz // 4
                subrngs = []
                try:
                    sct = rom.subsect(mn, cls, rom, ln)
                    for sub in sct:
                        if sub is None:
                            continue
                        subrngs.append((sub.real_offset, sub.sect_top))
                except:
                    continue
                if len(subrngs) < 3:
                    continue
                for rng in subrngs:
                    fa.hold(*rng)
                fa.hold(mn, sz)
                rvs_rpr = ', '.join(hex(i) for i in fa.rvs_tab[mn])
                print(f'found 0x{mn:x}-0x{mx:x}(0x{ln:x}): {cls.__name__} [{rvs_rpr}]')
        for typ in [1, 2, 8, 4]:
            print(f'scan for {typ}')
            for ofs in fa.scan():
                fnd, sct, ln, sz = tc.check(ofs, typ)
                if fnd:
                    fa.hold(ofs, sz)
                    rvs_rpr = ', '.join(hex(i) for i in fa.rvs_tab[ofs])
                    print(f'found 0x{ofs:x}-0x{ofs+sz:x}(0x{ln:x}): {typ} [{rvs_rpr}]')
                    if typ & 0x4:
                        txt = chs.decode(sct.text.tokens)
                    elif typ & 0x8:
                        txt = chs.decode(sct.tokens)
                    else:
                        continue
                    if txt and txt.count('.') / len(txt) < 0.3:
                        print('  txt:', txt)
