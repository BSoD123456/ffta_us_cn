#! python3
# coding: utf-8

try:
    from cnocr import CnOcr
except:
    print('''
please install Pillow with
pip3 install cnocr
or
pip install cnocr
or
py -3 -m pip install cnocr
or
python -m pip install cnocr
''')
    raise

def report(*args):
    r = ' '.join(a for a in args if a)
    print(r)
    return r

class c_hole_idx:

    def __new__(cls, st):
        if isinstance(st, cls):
            return st
        return super().__new__(cls)

    def __init__(self, st):
        if st is self:
            return
        self.base = st
        self.holes = []

    def src(self, idx):
        for h in self.holes:
            if idx >= h:
                idx += 1
        return self.base + idx

    def dig(self, idx):
        hs = self.holes
        i = 0
        d = idx
        for i, h in enumerate(hs):
            if d < h:
                break
            d += 1
            assert d != h
        else:
            i += 1
        n = c_hole_idx(self.base)
        n.holes = hs[:i] + [d] + hs[i:]
        return n

    def cut(self, idx, ret1 = True, ret2 = True):
        hs = self.holes
        i = 0
        d = idx
        for i, h in enumerate(hs):
            if d < h:
                break
            d += 1
            assert d != h
        else:
            i += 1
        if ret1:
            n1 = c_hole_idx(self.base)
            n1.holes = hs[:i]
        if ret2:
            n2 = c_hole_idx(self.base + d)
            n2.holes = [h - d for h in hs[i:]]
        if ret1 and ret2:
            return n1, n2
        elif ret1:
            return n1
        elif ret2:
            return n2

class c_map_blk:

    MAX_SHIFT = 3

    def __init__(self, s1, i1, s2, i2, cmt):
        self.ss = (s1, s2)
        s1i = {c:i for i, c in enumerate(s1)}
        s2i = {c:i for i, c in enumerate(s2)}
        self.ssi = (s1i, s2i)
        self.hidx = [c_hole_idx(i1), c_hole_idx(i2)]
        self.len = [len(s1), len(s2)]
        self.shft = self.len[1] - self.len[0]
        self.cmt = cmt

    @property
    def valid(self):
        return all(self.len)

    @property
    def determine(self):
        return self.shft == 0

    def _rvs_info(self, rvs):
        if rvs:
            return 1, 0, -self.shft
        else:
            return 0, 1, self.shft

    def shft_rng(self, offs = 0):
        return (
            min(0, self.shft + offs, self.shft - offs),
            max(0, self.shft + offs, self.shft - offs),
        )

    @staticmethod
    def _get_slc(s, i, shft):
        if shft < 0:
            i1 = max(0, i + shft)
            i2 = min(len(s), i)
        else:
            i1 = max(0, i)
            i2 = min(len(s), i + shft)
        return s[i1:i2]

    def get_src(self, rvs):
        sidx, saidx, shft = self._rvs_info(rvs)
        return self.ss[sidx]

    def get_len(self, rvs):
        sidx, saidx, shft = self._rvs_info(rvs)
        return self.len[sidx]

    def get_map(self, dc, rvs):
        sidx, saidx, shft = self._rvs_info(rvs)
        si = self.ssi[sidx]
        if c in si:
            return self._get_slc(self.ss[saidx], si[c], shft)
        return None

    def split_by(self, c1, c2):
        s1i, s2i = self.ssi
        s1, s2 = self.ss
        hi1, hi2 = self.hidx
        cmt = self.cmt
        if not (c1 in s1i or c2 in s2i):
            return self,
        elif not c1 in s1i:
            ci2 = s2i[c2]
            return c_map_blk(
                s1, hi1,
                s2[:ci2] + s2[ci2 + 1:], hi2.dig(ci2), cmt),
        elif not c2 in s2i:
            ci1 = s1i[c1]
            return c_map_blk(
                s1[:ci1] + s1[ci1 + 1:], hi1.dig(ci1),
                s2, hi2, cmt),
        ci1 = s1i[c1]
        ci2 = s2i[c2]
        srng1, srng2 = self.shft_rng(self.MAX_SHIFT)
        if not srng1 <= ci2 - ci1 < srng2:
            report('warning', f'shifted too much {ci2 - ci1}~{srng1}/{srng2}')
            return c_map_blk(
                s1[:ci1] + s1[ci1 + 1:], hi1.dig(ci1),
                s2[:ci2] + s2[ci2 + 1:], hi2.dig(ci2), cmt),
        b1 = c_map_blk(
            s1[:ci1], hi1.cut(ci1, ret2=False),
            s2[:ci2], hi2.cut(ci2, ret2=False), cmt)
        b2 = c_map_blk(
            s1[ci1 + 1:], hi1.cut(ci1 + 1, ret1=False),
            s2[ci2 + 1:], hi2.cut(ci2 + 1, ret1=False), cmt)
        return b1, b2

    @staticmethod
    def _trim(blk):
        det_info = []
        if not blk.valid:
            return None, det_info
        elif not blk.determine:
            return blk, det_info
        hi1, hi2 = blk.hidx
        cmt = blk.cmt
        for i, (c1, c2) in enumerate(zip(blk.ss[0], blk.ss[1])):
            det_info.append(
                (c1, hi1.src(i), c2, hi2.src(2), cmt)
            )
        return None, det_info

    def split_bat(self, pairs):
        rbs = []
        det_info = []
        cblk = self
        for c1, c2 in pairs:
            sblks = self.split_by(c1, c2)
            if len(sblks) == 1:
                cblk, = sblks
            elif len(sblks) == 2:
                rblk, nblk = sblks
                rblk, dinfo = self._trim(rblk)
                if rblk:
                    rbs.append(rblk)
                elif dinfo:
                    det_info.extend(dinfo)
                cblk = nblk
            else:
                assert False
        cblk, dinfo = self._trim(cblk)
        if cblk:
            rbs.append(cblk)
        elif dinfo:
            det_info.extend(dinfo)
        return rbs, det_info

class c_map_guesser:

    MAX_LA_WARN = 3
    MAX_LA_SKIP = 6

    def __init__(self):
        self.det = {}
        self.det_r = {}
        self.nondet = {}
        self.cnflct = {}
        self.mapblk = []

    def innate(self, knowledge):
        for c1, c2 in knowledge.items():
            if c1 in self.det:
                report('warning', f'dumped innate char {c1}')
            self.det[c1] = c2
            if c2 in self.det_r:
                report('warning', f'dumped innate char {c2}')
            self.det_r[c2] = c1

    def _norm_text(self, s, norm, trim):
        r = []
        for c in s:
            if c in trim:
                continue
            if c in norm:
                c = norm[c]
            r.append(c)
        return r

    def _log_conflict(self, c1, i1, c2, i2, cmt):
        report('info', f'conflict {c1} - {c2} {i1}/{i2} at {cmt}')
        if c1 in self.cnflct:
            cc_info = self.cnflct[c1]
        else:
            cc_info = {}
            self.cnflct[c1] = cc_info
        if not c2 in cc_info:
            cc_info[c2] = []
        cc_info[c2].append((cmt, i1, i2))

    def _ensure_match(self, c1, i1, c2, i2, cmt, chk_cnflct):
        #print('ensure', c1, i1, c2, i2, cmt)
        if chk_cnflct:
            if c1 in self.det:
                if c2 == self.det[c1]:
                    return
                self._log_conflict(c1, i1, c2, i2, cmt)
                return
            if c2 in self.det_r:
                assert c1 != self.det_r[c2]
                self._log_conflict(c1, i1, c2, i2, cmt)
                return
        assert not c1 in self.det
        self.det[c1] = c2
        assert not c2 in self.det_r
        self.det_r[c2] = c1
        sblks = self.mapblk
        if sblks:
            self.mapblk = []
            detp = [(c1, c2)]
            for sblk in sblks:
                self._feed_blk_trim(sblk, detp)

    def _ensure_match_nondet(self, c1, i1, c2, i2, cmt):
        #print('ensure nondet', c1, i1, c2, i2, cmt)
        if not c1 in self.nondet:
            return
        c1r_info = self.nondet[c1]
        del self.nondet[c1]
        for cc2, (ccmt, ci1, ci2) in c1r_info.items():
            if cc2 == c2:
                continue
            self._log_conflict(c1, ci1, cc2, ci2, ccmt)
            _ac1_del = []
            _ac1_ensure = []
            for ac1, ac1r_info in self.nondet.items():
                if cc2 in ac1r_info:
                    ccmt, ci1, ci2 = ac1r_info[cc2]
                    self._log_conflict(ac1, ci1, cc2, ci2, ccmt)
                    del ac1r_info[cc2]
                if len(ac1r_info) == 1:
                    for ac1r, (ccmt, ci1, ci2) in ac1r_info.items():
                        _ac1_ensure.append((ac1, ci1, ac1r, ci2, ccmt))
                    ac1r_info = None
                if not ac1r_info:
                    _ac1_del.append(ac1)
            for ac1 in _ac1_del:
                del self.nondet[ac1]
            for args in _ac1_ensure:
                self._ensure_match(*args, True)

    def _guess_match(self, c1, i1, c2, i2, cmt):
        #print('guess', c1, i1, c2, i2, cmt)
        if c1 in self.det:
            if c2 == self.det[c1]:
                return
            self._log_conflict(c1, i1, c2, i2, cmt)
            return
        if c2 in self.det_r:
            assert c1 != self.det_r[c2]
            self._log_conflict(c1, i1, c2, i2, cmt)
            return
        if not c1 in self.nondet:
            self.nondet[c1] = {}
        c1r_info = self.nondet[c1]
        if c2 in c1r_info:
            self._ensure_match(c1, i1, c2, i2, cmt, False)
            self._ensure_match_nondet(c1, i1, c2, i2, cmt)
        else:
            c1r_info[c2] = (cmt, i1, i2)

    def _feed_blk(self, s1, i1, s2, i2, cmt):
        ns1 = []
        ns2 = []
        ni1 = c_hole_idx(i1)
        nih1 = 0
        ni2 = c_hole_idx(i2)
        nih2 = 0
        det_pairs = []
        det_r = set()
        for i, c1 in enumerate(s1):
            if c1 in self.det:
                c1r = self.det[c1]
                if c1r in s2:
                    det_pairs.append((c1, c1r))
                    det_r.add(c1r)
                else:
                    ni1 = ni1.dig(i - nih1)
                    nih1 += 1
                    continue
            ns1.append(c1)
        for i, c2 in enumerate(s2):
            if c2 in self.det_r:
                if not c2 in det_r:
                    assert not self.det_r[c2] in ns1
                    ni2 = ni2.dig(i - nih2)
                    nih2 += 1
                    continue
            ns2.append(c2)
        sblk = c_map_blk(ns1, ni1, ns2, ni2, cmt)
        self._feed_blk_trim(sblk, det_pairs)

    def _feed_blk_trim(self, blk, det_pairs):
        rblks, rdet = blk.split_bat(det_pairs)
        if rblks:
            self.mapblk.extend(rblks)
        for dinfo in rdet:
            self._guess_match(*dinfo)

    def _guess_match_blk(self, s1, ed1, s2, ed2, cmt):
        l1 = len(s1)
        l2 = len(s2)
        i1 = ed1 - l1 - 1
        i2 = ed2 - l2 - 1
        self._feed_blk(s1, i1, s2, i2, cmt)

    def feed(self, s1, s2, cmt, norm_r = {}, trim_r = []):
        trim1 = set()
        trim2 = set()
        for t in trim_r:
            if t in self.det_r:
                trim1.add(self.det_r[t])
            trim2.add(t)
        s1 = self._norm_text(s1, {}, trim1)
        s2 = self._norm_text(s2, norm_r, trim2)
        #print('feed', cmt, f'({len(s2)})', ''.join(s2))
        #print(f'({len(s1)})', ' '.join(hex(c)[2:] for c in s1))
        l1 = len(s1)
        l2 = len(s2)
        i1 = 0
        i2 = 0
        sk1 = []
        sk2 = []
        lst_matched = True
        while i1 < l1 and i2 < l2:
            if lst_matched:
                if sk1 and sk2:
                    #print(f'guess skip {len(sk1)}/{len(sk2)}', sk1, ''.join(sk2))
                    self._guess_match_blk(sk1, i1, sk2, i2, cmt)
                sk1 = []
                sk2 = []
            c1 = s1[i1]
            c2 = s2[i2]
            if c1 in self.det:
                # known c1
                c1r = self.det[c1]
                if c1r == c2:
                    # matched, bypass
                    i1 += 1
                    i2 += 1
                    #print('matched', c1, i1, c2, i2)
                    lst_matched = True
                    continue
                # find matched char in s2 next
                _i2dlt = 0
                _sk2 = [c2]
                for _i2 in range(i2 + 1, min(l2, i2 + self.MAX_LA_SKIP)):
                    _c2 = s2[_i2]
                    if _c2 == c1r:
                        _i2dlt = _i2 - i2
                        break
                    _sk2.append(_c2)
                if _i2dlt > 0:
                    for _i1 in range(i1 + 1, min(l1, i1 + _i2dlt * 2 - len(sk1) + len(sk2))):
                        _c1 = s1[_i1]
                        if _c1 == c1:
                            # dumplicate match, skip self
                            report('warning',
                                f's1 look ahead across a dumplicate char {i1}~{_i1}/{i1+_i2dlt}')
                            break
                    else:
                        if _i2dlt >= self.MAX_LA_WARN:
                            report('warning',
                                f's2 lookahead too much {i2}+{_i2dlt}/{self.MAX_LA_WARN}~{self.MAX_LA_SKIP} at {cmt}')
                        i1 += 1
                        i2 += _i2dlt + 1
                        #print('sk2+1', ''.join(_sk2))
                        sk2.extend(_sk2)
                        lst_matched = True
                        continue
                # no matched char found, skip c1
                #print('sk1+2')
                sk1.append(c1)
                i1 += 1
                lst_matched = False
                continue
            # unknown c1
            if c2 in self.det_r:
                # known c2
                c2r = self.det_r[c2]
                assert c2r != c1
                # find matched char in s1 next
                _i1dlt = 0
                _sk1 = [c1]
                for _i1 in range(i1 + 1, min(l1, i1 + self.MAX_LA_SKIP)):
                    _c1 = s1[_i1]
                    if _c1 == c2r:
                        _i1dlt = _i1 - i1
                        break
                    _sk1.append(_c1)
                if _i1dlt > 0:
                    for _i2 in range(i2 + 1, min(l2, i2 + _i1dlt * 2 - len(sk2) + len(sk1))):
                        _c2 = s2[_i2]
                        if _c2 == c2:
                            # dumplicate match, skip self
                            report('warning',
                                f's2 look ahead across a dumplicate char {i2}~{_i2}/{i2+_i1dlt}')
                            break
                    else:
                        if _i1dlt >= self.MAX_LA_WARN:
                            report('warning',
                                f's2 lookahead too much {i1}+{_i1dlt}/{self.MAX_LA_WARN}~{self.MAX_LA_SKIP}')
                        i2 += 1
                        i1 += _i1dlt + 1
                        #print('sk1+1')
                        sk1.extend(_sk1)
                        lst_matched = True
                        continue
                # no matched char found, skip c2
                #print('sk2+2', c2)
                sk2.append(c2)
                i2 += 1
                lst_matched = False
                continue
            # both c1 c2 unknown
            sk1.append(c1)
            sk2.append(c2)
            lst_matched = False
            i1 += 1
            i2 += 1
        if i1 < l1:
            sk1.extend(s1[i1:])
            i1 = l1
        if i2 < l2:
            sk2.extend(s2[i2:])
            i2 = l2
        if sk1 and sk2:
            self._guess_match_blk(sk1, i1, sk2, i2, cmt)

class c_ffta_ocr_parser:

    def __init__(self, txts, font):
        self.txts = txts
        self.font = font
        self.chrs = []
        self.chrs_idx = 0
        self.toks_done = False
        self.do_shift = False

    def parse(self, noambi = False):
        self.ocr = CnOcr(det_model_name='naive_det')
        self.gsr = c_map_guesser()
        if noambi:
            ocr_ambiguous = {}
            ocr_normalize = {}
        else:
            from ffta_ocr_ambi import ocr_ambiguous, ocr_normalize
        self.gsr.innate({
            # unused, only for charset
            **self._chartab(0, [
                (0xa4a1, 0xa4ef), (0xa4f2, 0xa4f3),
                (0xa5a1, 0xa5ef), (0xa5f2, 0xa5f4),
            ], 'gbk'),
            # symbols
            **self._chartab(0xa3, ['、', '。', 'ー'], 'gbk'),
            **self._chartab(0xa6, [('0', '9')], 'gbk'),
            **self._chartab(0xb0, [('A', 'Z')], 'gbk'),
            **self._chartab(0xca, [('a', 'z')], 'gbk'),
            **self._chartab(0xe4, [
                *'.「」『』…',
                *'?!,·:_々/~',
                *'‘’“”(){}[]',
                *'+-±×=<>∞♂♀%&*※—|',
                *'↑↓←→',
                *'○△□■^;◎',
            ], 'gbk'),
            **self._chartab(0x118, [('０', '９')], 'gbk'),
            # 0x122
            # Ambiguous
            **ocr_ambiguous,
        })
        self.gsr_norm = {
            '，': ',',
            '？': '?',
            '！': '!',
            '０': '0',
            '１': '1',
            '２': '2',
            '３': '3',
            '４': '4',
            '５': '5',
            '６': '6',
            '７': '7',
            '８': '8',
            '９': '9',
        }
        self.gsr_trim = [' ']
        self.txt_trim_rng = [(0, 0xa4), (0xe4, 0xea), (0xed, 0x118)]
        self.chst_norm = ocr_normalize
        self.chst_first_ocr = 0x122
        if noambi:
            self.chst_size = self.chst_first_ocr
        else:
            self.chst_size = self.font.sect.tsize

    @staticmethod
    def _chartab(base, seq, enc):
        r = {}
        def dec(c):
            if isinstance(c, str):
                return int(c.encode(enc).hex(), 16)
            else:
                return c
        def rec(c):
            s = hex(c)[2:]
            if len(s) % 2:
                s = '0' + s
            r[len(r) + base] = bytes.fromhex(s).decode(enc)
        for v in seq:
            if isinstance(v, tuple):
                for c in range(dec(v[0]), dec(v[1]) + 1):
                    rec(c)
            else:
                rec(dec(v))
        return r

    def draw_chars(self, chars, pad = 3, smallchar = False):
        blks = [
            # supplement height to 10px, make OCR work.
            # OCR do not work on image whose height is less than 10px
            self.font.draw_point(2, ln = 10 if smallchar else 1),
            self.font.draw_chars(chars, pad = pad, noshadow = False)
        ]
        return self.font.make_img(self.font.draw_horiz(*blks, pad = 20 if smallchar else 1))

    def ocr_chars(self, chars, ret_img = False, smallchar = False):
        im = self.draw_chars(chars, smallchar = smallchar)
        rinfo = self.ocr.ocr(im)
        rchars = ''.join(i['text'] for i in rinfo)
        if ret_img:
            return rchars, im
        else:
            return rchars

    def _next_toks(self):
        if self.toks_done:
            return None
        try:
            return next(self.txts)
        except StopIteration:
            self.toks_done = True
            return None

    # token handle for ffta token
    def _hndl_tok(self, tok):
        ttyp, tchr = tok
        if not ttyp.startswith('CHR_'):
            return None
        trimed = False
        for trim_st, trim_ed in self.txt_trim_rng:
            if trim_st <= tchr < trim_ed:
                trimed = True
                break
        if trimed:
            return None
        else:
            return tchr

    def _next_chrs(self):
        if self.chrs_idx < 0:
            return None
        if self.chrs_idx < len(self.chrs):
            t = self.chrs[self.chrs_idx]
            self.chrs_idx += 1
            return t
        toks = self._next_toks()
        if toks is None:
            self.chrs_idx = -1
            return None
        line = []
        for tok in toks:
            c = self._hndl_tok(tok)
            if c is None:
                continue
            line.append(c)
        self.chrs.append(line)
        self.chrs_idx = len(self.chrs)
        return line

    def pick_next(self, tlen_min, txt = None):
        if txt is None:
            txt = []
        tlen = 0
        while tlen < tlen_min:
            line = self._next_chrs()
            if line is None:
                return txt
            txt.extend(line)
            tlen += len(line)
        return txt

    def draw_next(self, tlen_min):
        stxt = self.pick_next(tlen_min)
        return self.draw_chars(stxt)

    def feed_next(self, tlen_min, detail = False):
        tidx = self.chrs_idx
        stxt = self.pick_next(tlen_min)
        ntidx = self.chrs_idx
        if detail:
            rtxt, im = self.ocr_chars(stxt, True)
        else:
            rtxt = self.ocr_chars(stxt)
        self.gsr.feed(stxt, rtxt, (tidx, ntidx), self.gsr_norm, self.gsr_trim)
        if detail:
            return rtxt, im

    def feed_all(self, tlen_min = 200, do_shift = False):
        self.do_shift = do_shift
        while self.chrs_idx >= 0:
            report('info', f'feed {self.chrs_idx}')
            self.feed_next(tlen_min)
        if do_shift:
            report('info', f'feed shift chars')
            self.feed_shift()

    def refeed_all(self, tlen_min = 200):
        self.chrs_idx = 0
        self.feed_all(tlen_min, do_shift = self.do_shift)

    def feed_shift(self, win = 4, sep = 'A'):
        sep_c = self.gsr.det_r[sep]
        for c in range(self.chst_first_ocr, self.chst_size - win + 1):
            if c % 0x80 == 0:
                report('info', f'feed char 0x{c:x}')
            ch = list(range(c, c + win))
            och = self.ocr_chars(ch, smallchar = True)
            ch = [sep_c, *ch, sep_c]
            och = sep + och + sep
            self.gsr.feed(ch, och, (c, c+win), self.gsr_norm, self.gsr_trim)

    def get_conflict(self):
        r = {}
        for c1, rinfo in self.gsr.cnflct.items():
            if c1 in  self.gsr.det:
                s = [self.gsr.det[c1], *rinfo.keys()]
                r[c1] = ''.join(s)
            else:
                for c2 in rinfo:
                    #assert c2 in self.gsr.det_r
                    if not c2 in r:
                        if not c2 in self.gsr.det_r:
                            continue
                        r[c2] = [self.gsr.det_r[c2]]
                    r[c2].append(c1)
        return r

    def draw_conflict(self):
        blks = []
        for c, v in self.get_conflict().items():
            if isinstance(c, int):
                blks.append(self.font.draw_horiz(
                    self.font.draw_chars([c]),
                    self.font.draw_comment(f'(0x{c:x}):{v}'),
                ))
                report(None, f"0x{c:x}: '{v}',")
            else:
                blks.append(self.font.draw_horiz(
                    self.font.draw_comment(f'{c}:({",".join(hex(i) for i in v)})'),
                    self.font.draw_chars(v),
                ))
                for i in v:
                    report(None, f"0x{i:x}: '{c}',")
        if not blks:
            return None
        return self.font.make_img(self.font.draw_vert(*blks))

    def draw_nondet(self):
        blks = []
        (_, nd, ndm), _ = self.export_charset()
        nd = nd.copy()
        nd.update(ndm)
        for c, v in nd.items():
            if isinstance(v, list):
                v = ''.join(v)
            blks.append(self.font.draw_horiz(
                self.font.draw_chars([c]),
                self.font.draw_comment(f'(0x{c:x}):{v}'),
            ))
            report(None, f"0x{c:x}: '{v}',")
        if not blks:
            return None
        return self.font.make_img(self.font.draw_vert(*blks))

    def draw_det(self):
        blks = []
        (dt, _, _), _ = self.export_charset()
        for c, v in dt.items():
            blks.append(self.font.draw_horiz(
                self.font.draw_chars([c]),
                self.font.draw_comment(f'(0x{c:x}):{v}'),
            ))
            report(None, f"0x{c:x}: '{v}',")
        if not blks:
            return None
        return self.font.make_img(self.font.draw_vert(*blks))

    def draw_found_chrs(self, char):
        blks = []
        for i, ch in enumerate(self.chrs):
            if char in ch:
                blks.append(self.font.draw_horiz(
                    self.font.draw_comment(f'{i}:'),
                    self.font.draw_chars(ch),
                ))
        return self.font.make_img(self.font.draw_vert(*blks))

    def _uncovered_chrs_txts(self, detail = False):
        cs = {}
        cs_ex, _ = self.export_charset()
        cs.update(cs_ex[1])
        cs.update(cs_ex[0])
        rs = []
        rc = set()
        for i, ch in enumerate(self.chrs):
            fnd = False
            for c in ch:
                if not c in cs:
                    fnd = True
                    rc.add(c)
            if detail and fnd:
                rs.append(i)
        if detail:
            return sorted(rc), rs
        else:
            return sorted(rc)

    def _uncovered_chrs_all(self):
        cs = {}
        cs_ex, _ = self.export_charset()
        cs.update(cs_ex[1])
        cs.update(cs_ex[0])
        rc = []
        for c in range(self.chst_size):
            if not c in cs:
                rc.append(c)
        return rc

    def uncovered_chrs(self):
        if self.do_shift:
            return self._uncovered_chrs_all()
        else:
            return self._uncovered_chrs_txts()

    def draw_uncovered(self):
        ch = self.uncovered_chrs()
        blks = []
        for c in ch:
            blks.append(self.font.draw_horiz(
                self.font.draw_chars([c]),
                self.font.draw_comment(f'(0x{c:x})'),
            ))
            report(None, f"0x{c:x}: '',")
        if not blks:
            return None
        return self.font.make_img(self.font.draw_vert(*blks))

    def export_charset(self):
        cdet = self.gsr.det.copy()
        cdet_r = self.gsr.det_r.copy()
        nondet = self.gsr.nondet
        nondet_r = {}
        nondet_mul_c1 = set()
        nondet_r_mul_c2 = set()
        for c1, c1r_info in nondet.items():
            mul = (len(c1r_info) > 1)
            if mul:
                nondet_mul_c1.add(c1)
            for c2 in c1r_info:
                if mul:
                    nondet_r_mul_c2.add(c2)
                if not c2 in nondet_r:
                    nondet_r[c2] = set()
                nondet_r[c2].add(c1)
        for c2, c2r_info in nondet_r.items():
            if not len(c2r_info) > 1:
                continue
            nondet_r_mul_c2.add(c2)
            for c1 in c2r_info:
                nondet_mul_c1.add(c1)
        cndet = {}
        cndet_r = {}
        cndet_mul = {}
        cndet_r_mul = {}
        for c1, c1r_info in nondet.items():
            if c1 in nondet_mul_c1:
                if not c1 in cndet_mul:
                    cndet_mul[c1] = []
                cnm1 = cndet_mul[c1]
                for c2 in c1r_info:
                    if not c2 in cnm1:
                        cnm1.append(c2)
            else:
                for c2 in c1r_info:
                    assert not c1 in cndet
                    cndet[c1] = c2
        for c2, c2r_info in nondet_r.items():
            if c2 in nondet_r_mul_c2:
                if not c2 in cndet_r_mul:
                    cndet_r_mul[c2] = []
                cnm2 = cndet_r_mul[c2]
                for c1 in c2r_info:
                    if not c1 in cnm2:
                        cnm2.append(c1)
            else:
                for c1 in c2r_info:
                    assert not c2 in cndet_r
                    cndet_r[c2] = c1
        return (cdet, cndet, cndet_mul), (cdet_r, cndet_r, cndet_r_mul)

    def final_charset(self):
        cs, csr = self.export_charset()
        assert len(cs[2]) == len(csr[2]) == 0
        assert len(self.get_conflict()) == 0
        assert len(self.uncovered_chrs()) == 0
        dcs = {}
        dcsr = {}
        for i in range(2):
            dcs.update(cs[i])
            dcsr.update(csr[i])
        fcs = {}
        for ch, s in dcs.items():
            if s in self.gsr_norm:
                s = self.gsr_norm[s]
            if s in self.chst_norm:
                s = self.chst_norm[s]
            fcs[ch] = s
        for s1, s2 in ({**self.gsr_norm, **self.chst_norm}).items():
            dcsr[s1] = dcsr[s2]
        return fcs, dcsr

def iter_toks(rom):
    def iter_sect(sect):
        for path, line in sect.iter_item(skiprep = True):
            if line is None or isinstance(line, list):
                continue
            try:
                line = line.text
            except:
                pass
            yield line.tokens
    report('info', 'iter s_text')
    yield from iter_sect(rom.tabs['s_text'])
    for nm, tab in rom.tabs['pages'].items():
        report('info', f'iter pages:{nm}')
        yield from iter_sect(tab)
    report('info', 'iter fx_text')
    yield from iter_sect(rom.tabs['fx_text'])
    for nm, tab in rom.tabs['words'].items():
        report('info', f'iter words:{nm}')
        yield from iter_sect(tab)

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_cn

    from ffta_font import c_ffta_font_drawer

    def main(rom):
        dr = c_ffta_font_drawer(rom.tabs['font'])
        ocr = c_ffta_ocr_parser(iter_toks(rom), dr)
        ocr.parse()
        return ocr
    ocr = main(rom_cn)
