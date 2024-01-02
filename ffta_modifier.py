#! python3
# coding: utf-8

CONF = {
    'roms': {
        'src': {
            'base': {
                'path': r'roms\fftaus.gba',
                'type': 'us',
                'charset': 'charset_us.json',
            },
            'text': {
                'path': r'roms\fftacnfx.gba',
                'type': 'cn',
                'charset': 'charset_cn.json',
                'charset_ocr': True,
            },
        },
        'dst': {
            'rels': {
                'path': r'roms\fftauscn.gba',
            },
            'sndbx': {
                'path': r'roms\fftauscn_sndbx.gba',
            },
        },
    },
    'work': {
        'text': {
            'raw': {
                # comparison
                'comp': 'raw_txt_comp_wk.json',
                # uncovered
                'uncv': 'raw_txt_uncv_wk.json',
            },
            'src': {
                # base rom
                'base': 'src_txt_base_wk.json',
                # text rom
                'text': 'src_txt_text_wk.json',
            },
            'mod': {
                # translate
                'trans': 'trans_txt.json',
            },
            'fix': {
                # fix cn text
                'fcomp': 'trans_fix_txt.json',
            },
        },
    },
    'font': {
        # 精品点阵体9×9 BoutiqueBitmap9x9
        # from https://github.com/scott0107000/BoutiqueBitmap9x9
        'src': 'font/BoutiqueBitmap9x9_1.7.ttf',
        'size': 10,
        'offset': (0, 1),
        'charset': 'charset_uscn_wk.json',
        'charset_nosave': True,
        # only hanzi
        'dybase': 0x122,
    },
    'text': {
        'skip': {
            '@[40]@[42]',
            '@[42]',
            'dummy@[40]@[42]',
            'dummy@[42]',
            'dummy',
            'Dummy',
        },
        'skipf': [],
        'skipf_defer': [],
        'modf': [],
        'align': {
            's_text': [
                ((36,), (35,)),
                ((60,), (60,)),
            ],
            'pages:battle': [
                ((54,), (51,)),
            ],
            'pages:quest/': [
                ((1, 0), (0, 200)),
            ],
            'fx_text': [
                ((8, 60), (8, 58)),
                ((8, 61), (8, 60)),
                ((8, 62), (8, 62)),
                ((25,), (24,)),
            ],
            'words:refer': [
                ((107,), (104,)),
            ],
            'words:rumor': [
                ((62,), (61,)),
                ((63,), (63,)),
            ],
            'words:battle': [
                ((179,), (176,)),
                ((543,), (531,)),
            ],
        },
        'trim': {
            's_text': [{
                (61,),
            }, {
                (61,),
            }],
        },
    },
    'sandbox': {
        'enable': True,
        'only': True,
        'scene': {
            'boot': None,
            'fat': {
                #1: (None, None, 61),
                #6: (None, None, 61),
            },
        },
        'script': {
            'scene': (lambda f: {
                1: {
                    0x8:[
                        #0x53, 0x9, 0x0,
                    ],
                    0x363: [
                        *f['text_full'](1, 0x18, 0x82),
                        *f['text_full'](1, 0x18, 0x82, 0, 10),
                        *f['text_full'](57, 0x18, 0x82, 5, 115),
                        *f['text_full'](230, 0x18, 0x82, 10),
                        *f['text_full'](0, 0x18, 0x82, 11),
                        *f['setflag'](0x301),
                        #*f['setflag'](0x302),
                        #*[j for i in range(300) for j in f['setflag'](0x301+i)],
                        #*f['setflag'](0x43b),
                        *f['fade'](True, 60),
                        *f['done'](5),
                    ],
                    #0x367: [
                    #    0x17, 0x5,
                    #],
                    #0x4d4: [
                        #*f['fade'](True, 60),
                        #*f['load'](6),
                    #],
                    #0x501: [
                    #    *f['wait'](60),
                    #    *f['wait'](60),
                    #    *f['wait'](60),
                    #    *f['wait'](60),
                    #    *f['wait'](60),
                    #    *f['load'](2, 4),
                    #],
                },
                2: {
                    #0x4: f['wait'](255),
                },
                6: {
                    #0x9: [
                    #    0xf, 0x1, 0x18, 0xa4,
                    #],
                },
                9: {
                    #0xba: [
                    #    *f['load'](176, 2),
                    #]
                }
            })({
                'wait': lambda frms: [
                    0x15, frms,
                ],
                'fade': lambda is_out, frms=60: [
                    0x6, 0x31, frms, 0x0,
                ] if is_out else [
                    0x6, 0x13, frms, 0x64,
                ],
                'load': lambda sc: [
                    # load scene
                    0x1c, sc, 0x0,
                ],
                'done': lambda typ=2: [
                    # safe return
                    0x17, typ,
                ],
                'setflag': lambda fidx, val=1: [
                    0x1a, fidx & 0xff, fidx >> 8, val,
                ],
                'text_full': lambda tidx, prt, flg, sub=0, sc=0: (
                    lambda rsub, rtidx: [
                        *([
                            # set sc_idx at 0x2002192 = 0x162 + 0x2002030
                            0x1b, 0x62, 0x1, sc,
                        ] if sc > 0 else []),
                        *([
                            # set sub_idx at 0x2003c2a = 0x1bfa + 0x2002030
                            0x1b, 0xfa, 0x1b, rsub,
                        ] if sub > 0 else []),
                        *([
                            0xf, rtidx, prt, flg,
                        ] if sub > 0 else [
                            0xf, tidx, prt, flg,
                        ]),
                    ]
                )(
                    tidx // 24 + 1 + 10 * sub, tidx % 24
                ),
            }),
            'battle': {
                (3, 1): {
                    0x11: [
                        0x3, 0xfa, 0x1b, 0x25,
                    ],
                },
                (7, 2): {
                    0x9: [
                        0x5, 122, 0x0,
                    ],
                },
            }
        },
        'direct': {
            'rumor_data': {
                (0, 0x7f): {
                    'flag1': 0x301,
                    'val1': 1,
                    'flag2': 0,
                    'val2': 0,
                },
            },
            'quest_data': {
##                0x2: {
##                    'flag1': 0,
##                    'val1': 0,
##                    'flag2': 0,
##                    'val2': 0,
##                    'flag3': 0,
##                    'val3': 0,
##                },
##                #128: {
##                39: {
##                    'type': 16,
##                    'flag1': 0x302,
##                    'val1': 1,
##                    'flag2': 0,
##                    'val2': 0,
##                    'flag3': 0,
##                    'val3': 0,
##                    'nest': 0,
##                },
##                40: {
##                    'flag1': 0x303,
##                    'val1': 1,
##                    'flag2': 0,
##                    'val2': 0,
##                    'flag3': 0,
##                    'val3': 0,
##                    'nest': 0,
##                },
                (377, 397): {
                    'flag1': 0x301,
                    'val1': 1,
                    'flag2': 0x507,
                    'val2': 1,
                    'flag3': 0,
                    'val3': 0,
                    'nest': 0,
                },
                (387, 397): {
                    'flag2': 0x508,
                    'val2': 1,
                },
                381: {
                    '_uk3': 161,
                },
                (384, 386): {
                    '_uk3': 161,
                },
                387: {
                    '_uk3': 161,
                },
                (393, 395): {
                    '_uk2': 0,
                },
##                (393, 395): {
##                    'type': 32,
##                    '_uk1': 0,
##                    '_uk2': 0,
##                    '_uk3': 161,
##                    '_uk4': 4109,
##                    '_uk5': 200,
##                },
            },
        },
    },
}

def chk_has_japanese(txt, *_):
    for c in txt:
        oc = ord(c)
        if (0x3040 < oc < 0x3094 or
            0x30a0 < oc < 0x30fb):
            return True
    return False
def chk_invalid_words(txt, tname, *_):
    if tname == 'words:rumor':
        return txt.isdigit()
    return False
CONF['text']['skipf'].extend([
    chk_has_japanese,
    chk_invalid_words,
])

def mod_static_refer(bt, tt, tname, bidxp, tidxp, btxts, ttxts):
    REF_TOP = 104
    if not '@[51' in tt:
        return tt
    bwt = btxts['words:refer']
    twt = ttxts['words:refer']
    def _rplc(m):
        refv = int(m.group(1), 16)
        refi = (refv,)
        if refv < REF_TOP:
            sv = bwt[refi]
            #if not sv.startswith('CRN_'):
            return m.group(0)
        assert refi in twt
        return twt[refi]
    return re.sub(r'\@\[51([0-9a-fA-F]{2})\]', _rplc, tt)
CONF['text']['modf'].extend([
    mod_static_refer,
])

import json, re
import os, os.path, shutil

from ffta_sect import load_rom
from ffta_charset import c_ffta_charset_ocr, c_ffta_charset_dynamic
from ffta_font_generator import make_ffta_font_gen
from ffta_parser import make_script_parser

def report(*args):
    r = ' '.join(a for a in args if a)
    print(r)
    return r

INF = float('inf')

class c_tab_align_iter:

    def __init__(self, *tabs, align_map = [], trim_page = []):
        self.tabs = tabs
        self.amap = self._hndl_amap(align_map)
        self.trmpg = trim_page

    def _hndl_amap(self, align_map):
        add_lsts = []
        for amap_itm in align_map:
            mxidxp = None
            cidxps = []
            for i, idxp in enumerate(amap_itm):
                while i >= len(add_lsts):
                    add_lsts.append([])
                add_lst = add_lsts[i]
                cidxp = idxp
                for abas, adst in add_lst:
                    cidxp, _ = self._add_idx(cidxp, abas, adst)
                cidxps.append(cidxp)
                if mxidxp is None or self._cmp_idx(cidxp, mxidxp) > 0:
                    mxidxp = cidxp
            for i, cidxp in enumerate(cidxps):
                add_lst = add_lsts[i]
                if self._cmp_idx(cidxp, mxidxp) == 0:
                    continue
                add_lst.append((cidxp, mxidxp))
        return add_lsts

    def _iter_tab(self, idx):
        tab = self.tabs[idx]
        if tab:
            yield from tab.items()

    def reset(self):
        self.stats = []
        for i in range(len(self.tabs)):
            itr = self._iter_tab(i)
            zidx = tuple()
            sinfo = [itr, zidx, (zidx, None)]
            self._next_sinfo(i, sinfo)
            self.stats.append(sinfo)

    @staticmethod
    def _getidxv(idxpath, i):
        if i < len(idxpath):
            return idxpath[i]
        else:
            return 0

    def _cmp_idx(self, idxp1, idxp2):
        for i in range(max(len(idxp1), len(idxp2))):
            v1 = self._getidxv(idxp1, i)
            v2 = self._getidxv(idxp2, i)
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0

    def _trim_idx(self, idxp):
        for i in range(len(idxp) - 1, -1, -1):
            if idxp[i] != 0:
                break
        else:
            return tuple()
        return tuple(idxp[:i+1])

    def _add_idx(self, src, abas, adst):
        if self._cmp_idx(src, abas) < 0:
            return src, False
        r = []
        do_add = True
        for i in range(max(len(src), len(abas), len(adst))):
            vs = self._getidxv(src, i)
            vb = self._getidxv(abas, i)
            vd = self._getidxv(adst, i)
            vr = vs
            if do_add:
                vr += vd - vb
            if vs != vb:
                do_add = False
            r.append(vr)
        return self._trim_idx(r), True

    def _calc_cidx(self, idxp, si):
        if si >= len(self.amap):
            return idxp
        cidxp = idxp
        for abas, adst in self.amap[si]:
            cidxp, is_done = self._add_idx(cidxp, abas, adst)
            if not is_done:
                break
        return cidxp

    def _sublen_idx(self, dst, src):
        sl = 0
        for i in range(max(len(dst), len(src))):
            vd = self._getidxv(dst, i)
            vs = self._getidxv(src, i)
            if vd != vs:
                assert vd > vs
                return sl
            sl += 1

    def _next_sinfo(self, si, sinfo):
        itr, idxp, (vidxp, val) = sinfo
        try:
            nvidxp, nval = next(itr)
        except StopIteration:
            infi = (INF,)
            sinfo[1] = infi
            sinfo[2] = (infi, None)
            return
        sinfo[2] = (nvidxp, nval)
        if si >= len(self.trmpg):
            sinfo[1] = nvidxp
            return
        tpgs = self.trmpg[si]
        cpg = None
        for i in range(len(nvidxp), -1, -1):
            pg = nvidxp[:i]
            if pg in tpgs:
                cpg = pg
                break
        if cpg is None:
            sinfo[1] = nvidxp
            return
        sl = self._sublen_idx(nvidxp, vidxp)
        if sl < len(cpg):
            sinfo[1] = cpg
            return
        ridxp = []
        for i in range(len(nvidxp)):
            v = self._getidxv(idxp, i)
            if i > sl:
                v = 0
            elif i == sl:
                v += 1
            ridxp.append(v)
        sinfo[1] = tuple(ridxp)

    def _next(self):
        mnidxp = None
        cidxps = []
        for si, (itr, idxp, _) in enumerate(self.stats):
            cidxp = self._calc_cidx(idxp, si)
            cidxps.append(cidxp)
            if mnidxp is None or self._cmp_idx(cidxp, mnidxp) < 0:
                mnidxp = cidxp
        if mnidxp and mnidxp[0] == INF:
            return None, True
        rs = []
        for si, (sinfo, cidxp) in enumerate(zip(self.stats, cidxps)):
            itr, idxp, (vidxp, val) = sinfo
            if self._cmp_idx(cidxp, mnidxp) == 0:
                rs.append((vidxp, val))
                self._next_sinfo(si, sinfo)
            else:
                rs.append((vidxp, None))
        return rs, False

    def iter(self):
        self.reset()
        while True:
            rs, is_done = self._next()
            if is_done:
                return
            yield tuple(rs)

class c_ffta_modifier:

    def __init__(self, conf):
        self.conf = conf

    def load(self):
        self.srom = {}
        self.chst = {}
        for nm, rconf in self.conf['roms']['src'].items():
            rom, chst = self.load_rom(rconf)
            self.srom[nm] = rom
            self.chst[nm] = chst
        self.fntgen, self.chst['font'] = self.load_font()
        self.txts = self.load_texts()

    def export(self):
        rmk = None
        sben = self.conf.get('sandbox', {}).get('enable', False)
        sbon = self.conf.get('sandbox', {}).get('only', False)
        if not sben or not sbon:
            rmk = self.export_rom(self.conf['roms']['dst']['rels'])
        if sben:
            sbrmk = self.export_rom(self.conf['roms']['dst']['sndbx'], as_sndbx = True)
            if rmk is None:
                rmk = sbrmk
        return rmk

    def export_rom(self, rom_conf, *args, **kargs):
        rmk = self.repack(*args, **kargs)
        if not rmk:
            report('warning', f'something wrong while repacking')
            return
        self.save_rom(rom_conf['path'], rmk)
        return rmk

    def load_rom(self, rom_conf):
        lfunc = load_rom[rom_conf['type']]
        rom = lfunc(rom_conf['path'])
        if 'charset' in rom_conf:
            if 'charset_ocr' in rom_conf and rom_conf['charset_ocr']:
                chstrom = rom
            else:
                chstrom = None
            chst = c_ffta_charset_ocr(rom_conf['charset'], chstrom)
            chst.load()
        else:
            chst = None
        return rom, chst

    def load_font(self):
        conf = self.conf['font']
        chst = c_ffta_charset_dynamic(
            conf['charset'], conf.get('charset_nosave', False))
        chst.load(self.chst['base'], conf['dybase'])
        fnt_gen = make_ffta_font_gen(conf['src'], conf['size'], conf['offset'])
        return fnt_gen, chst

    def load_texts(self):
        conf = self.conf['work']['text']
        dirty = False
        txts = {}
        if self._load_texts_json(conf['raw'], txts):
            ts = md.parse_texts(
                conf['raw']['comp'],
                conf['raw']['uncv'],
                conf['src']['base'],
                conf['src']['text'],
            )
            if conf['raw']['comp']:
                txts['comp'] = ts.pop(0)
            if conf['raw']['uncv']:
                txts['uncv'] = ts.pop(0)
            self._save_texts_json(conf['raw'], txts)
            reidx = lambda txts: {
                k:{'/'.join(str(i) for i in k):v for k, v in tab.items()}
                for k, tab in txts.items()}
            stxts = {}
            if conf['src']['base']:
                stxts['base'] = reidx(ts.pop(0))
            if conf['src']['text']:
                stxts['text'] = reidx(ts.pop(0))
            if stxts:
                self._save_texts_json(conf['src'], stxts)
            dirty = True
        if self._load_texts_json(conf['mod'], txts):
            txts['trans'] = txts['uncv']
            self._save_texts_json(conf['mod'], txts)
            dirty = False
        if dirty:
            txts['trans'] = self._merge_trans(txts['trans'], txts['uncv'])
            self._save_texts_json(conf['mod'], txts, bak = True)
        dirty = False
        if self._load_texts_json(conf['fix'], txts):
            txts['fcomp'] = {}
            dirty = True
        if self._refresh_fix_texts(txts):
            dirty = True
        if dirty:
            self._save_texts_json(conf['fix'], txts, bak = True)
        return txts

    def _load_texts_json(self, conf, txts):
        dirty = False
        for tname, tpath in conf.items():
            txt = self.load_json(tpath)
            if txt is None:
                dirty = True
                break
            txts[tname] = txt
        return dirty

    def _save_texts_json(self, conf, txts, bak = False):
        for tname, tpath in conf.items():
            if bak:
                self.bak_file(tpath)
            self.save_json(tpath, txts[tname])

    def bak_file(self, fn):
        if not os.path.isfile(fn):
            return
        f1, f2 = os.path.splitext(fn)
        shutil.copy2(fn, f1 + '.bak' + f2)

    def load_json(self, fn):
        try:
            with open(fn, 'r', encoding = 'utf-8') as fd:
                return json.load(fd)
        except:
            return None

    def save_json(self, fn, obj):
        with open(fn, 'w', encoding = 'utf-8') as fd:
            json.dump(obj, fd,
                ensure_ascii=False, indent=4, sort_keys=False)

    def save_rom(self, fn, rmk):
        with open(fn, 'wb') as fd:
            fd.write(rmk.raw)

    def _refresh_fix_texts(self, txts):
        fxtabs = txts['fcomp']
        otabs = txts['comp']
        rtabs = txts['trans']
        dirty = False
        for tname, tab in fxtabs.items():
            del_idxr = []
            for idxr, fpair in tab.items():
                if idxr in rtabs.get(tname, {}):
                    report('warning', f'duplicated fix path: {tname} {idxr}, deleted')
                    del_idxr.append(idxr)
                    continue
                opair = otabs.get(tname, {}).get(idxr, None)
                if not opair:
                    report('warning', f'invalid fix path: {tname} {idxr}, deleted')
                    del_idxr.append(idxr)
                    continue
                osrc, odst = opair
                if (not osrc or osrc.startswith('#') or
                    not odst or odst.startswith('#') ):
                    report('warning', f'unchanged fix path: {tname} {idxr}, deleted')
                    del_idxr.append(idxr)
                    continue
                if isinstance(fpair, list) and len(fpair) == 2:
                    fsrc, fdst = fpair
                    if fsrc != osrc:
                        report('warning', f'unmatched fix path: {tname} {idxr}, refreshed: {fsrc} -> {osrc}')
                        fpair[0] = osrc
                        dirty = True
                    if fdst == odst:
                        report('warning', f'unfixed fix path: {tname} {idxr}, deleted')
                        del_idxr.append(idxr)
                        continue
                else:
                    tab[idxr] = [osrc, '#' + odst]
                    dirty = True
            for idxr in del_idxr:
                del tab[idxr]
                dirty = True
        return dirty

    @staticmethod
    def _iter_txttab(rom):
        for tname, tab in rom.tabs.items():
            if tname.endswith('text'):
                yield tname, tab
            elif tname in ['words', 'pages']:
                for stname, stab in tab.items():
                    yield ':'.join((tname, stname)), stab

    @staticmethod
    def _iter_txttab_items_with_merge(merged, tabs):
        assert merged or len(tabs) == 1
        for i, tab in enumerate(tabs):
            for path, line in tab.iter_item(skiprep = True):
                if merged:
                    path = (i, *path)
                yield path, line

    def _iter_txttab_with_merge(self, rom):
        mtabs = []
        lst_merged = False
        lst_mtname = None
        for tname, tab in self._iter_txttab(rom):
            mtnames = tname.split('/')
            mtname = mtnames[0]
            if len(mtnames) > 1:
                mtname = mtname + '/'
                mi = int(mtnames[1])
                merged = True
            else:
                mi = 0
                merged = False
            if lst_mtname and mtname != lst_mtname:
                yield lst_mtname, self._iter_txttab_items_with_merge(lst_merged, mtabs)
                mtabs = []
            lst_merged = merged
            lst_mtname = mtname
            while mi >= len(mtabs):
                mtabs.append(None)
            mtabs[mi] = tab
        if mtabs:
            yield lst_mtname, self._iter_txttab_items_with_merge(lst_merged, mtabs)

    def _parse_text(self, romkey):
        rom = self.srom[romkey]
        chst = self.chst[romkey]
        txt_skip = self.conf['text']['skip']
        txt_skip_fs = self.conf['text']['skipf']
        txt_skip_fs_defer = self.conf['text']['skipf_defer']
        txts = {}
        defer_idxps = []
        for tname, tabitr in self._iter_txttab_with_merge(rom):
            ttxts = {}
            for path, line in tabitr:
                if line is None:
                    continue
                #pkey = '/'.join(str(i) for i in path)
                pkey = tuple(path)
                if isinstance(line, list):
                    rep_rpr = '/'.join(str(i) for i in line)
                    ttxts[pkey] = f'#repeat from {rep_rpr}'
                    continue
                try:
                    line = line.text
                except:
                    pass
                dec = chst.decode(line.tokens)
                if dec in txt_skip:
                    continue
                for sf in txt_skip_fs:
                    if sf(dec, tname, path, romkey):
                        #report('warning', f'skip text {tname}:{pkey}: {dec}')
                        dec = '#' + dec
                        break
                for sf in txt_skip_fs_defer:
                    if sf(dec, tname, path, romkey, defered = False):
                        defer_idxps.append((sf, tname, pkey, path))
                ttxts[pkey] = dec
            txts[tname] = ttxts
        for sf, tname, pkey, path in defer_idxps:
            dec = txts[tname][pkey]
            if sf(dec, tname, path, romkey, txts = txts, defered = True):
                #report('warning', f'defer skip text {tname}:{pkey}: {dec}')
                txts[tname][pkey] = '#' + dec
        return txts

    def _merge_keys(self, t1, t2):
        t1 = list(t1.keys())
        t2 = list(t2.keys())
        r = []
        i1 = 0
        i2 = 0
        while True:
            if i1 >= len(t1):
                r.extend(t2[i2:])
                break
            if i2 >= len(t2):
                r.extend(t1[i1:])
                break
            k1 = t1[i1]
            k2 = t2[i2]
            if k1 == k2:
                r.append(k1)
                i1 += 1
                i2 += 1
                continue
            if not k1 in t2:
                r.append(k1)
                i1 += 1
            if not k2 in t1:
                r.append(k2)
                i2 += 1
        return r

    def _merge_texts(self, tbas, ttxt, minfo):
        trslt = {}
        utrslt = {}
        txt_mod_fs = self.conf['text']['modf']
        amaps = self.conf['text']['align']
        trmpgs = self.conf['text']['trim']
        tnames = self._merge_keys(tbas, ttxt)
        for tname in tnames:
            btab = tbas.get(tname, None)
            ttab = ttxt.get(tname, None)
            rtab = {}
            rutab = {}
            if btab is None:
                trslt['#' + tname] = rtab
            else:
                trslt[tname] = rtab
            amap = amaps.get(tname, [])
            trmpg = trmpgs.get(tname, [])
            ta = c_tab_align_iter(btab, ttab,
                align_map = amap, trim_page = trmpg)
            for (bidxp, bval), (tidxp, tval) in ta.iter():
                if bval is None:
                    pkey = '#' + '/'.join(str(i) for i in tidxp)
                else:
                    pkey = '/'.join(str(i) for i in bidxp)
                has_bval = (bval and not bval.startswith('#'))
                has_tval = (tval and not tval.startswith('#'))
                if has_bval and has_tval:
                    for sf in txt_mod_fs:
                        tval = sf(bval, tval, tname, bidxp, tidxp, tbas, ttxt)
                rtab[pkey] = [i if i else '' for i in [bval, tval]]
                if not has_tval and has_bval:
                    rutab[pkey] = [bval, tval if tval else '']
            if rutab:
                utrslt[tname] = rutab
        return trslt, utrslt

    def parse_texts(self, atxt = True, utxt = False, btxt = False, ttxt = False):
        bt = self._parse_text('base')
        tt = self._parse_text('text')
        t, ut = self._merge_texts(bt, tt, None)
        return [tx for v, tx in zip([atxt , utxt , btxt , ttxt], [t, ut, bt, tt]) if v]

    def _merge_trans(self, otrans, nraw, renames = None):
        ntrans = {}
        for tname, nraw_tab in nraw.items():
            if renames and tname in renames:
                otrans_tab = otrans.get(renames[tname], {})
            else:
                otrans_tab = otrans.get(tname, {})
            ntrans_tab = {}
            for idxr, (raw_txt, trans_txt) in nraw_tab.items():
                if not idxr in otrans_tab:
                    ntrans_tab[idxr] = (raw_txt, trans_txt)
                    continue
                oraw_txt, otrans_txt = otrans_tab[idxr]
                if not oraw_txt == raw_txt:
                    raise ValueError(f'trans {tname}:{idxr} not match: {oraw_txt} / {raw_txt}')
                elif (otrans_txt and not otrans_txt.startswith('#')
                        and trans_txt and not trans_txt.startswith('#')):
                    if otrans_txt != trans_txt:
                        report('warning', f'trans {tname}:{idxr} duplicated: {otrans_txt} / {trans_txt}')
                    ntrans_tab[idxr] = (raw_txt, otrans_txt)
                elif trans_txt and not trans_txt.startswith('#'):
                    ntrans_tab[idxr] = (raw_txt, trans_txt)
                else:
                    ntrans_tab[idxr] = (raw_txt, otrans_txt)
            if ntrans_tab:
                ntrans[tname] = ntrans_tab
        return ntrans

    def _rplc_txt_tab(self, mtxt):
        chst = self.chst['font']
        rtabs = {}
        for tname, tab in mtxt.items():
            if tname.startswith('#'):
                continue
            report('info', f'encode tab: {tname}')
            if tname.endswith('/'):
                rtab = []
                merged_tab = True
            else:
                rtab = {}
                merged_tab = False
            for idxr, (src, dst) in tab.items():
                if not dst or idxr.startswith('#'):
                    continue
                #report('info', f'encode line {idxr}')
                dst = chst.encode(dst)
                if not dst:
                    continue
                idxp = tuple(int(i) for i in idxr.split('/'))
                if merged_tab:
                    mi = idxp[0]
                    while mi >= len(rtab):
                        rtab.append({})
                    rtab[mi][idxp[1:]] = dst
                else:
                    rtab[idxp] = dst
            if merged_tab:
                for i, mrtab in enumerate(rtab):
                    if not mrtab:
                        continue
                    mtname = tname + str(i)
                    rtabs[mtname] = mrtab
            elif rtab:
                rtabs[tname] = rtab
        return rtabs

    def _merge_txt_tab(self, tbs):
        rtabs = {}
        for tb in tbs:
            for tname, vtab in tb.items():
                if not vtab:
                    continue
                if tname in rtabs:
                    rtab = rtabs[tname]
                else:
                    rtab = {}
                    rtabs[tname] = rtab
                rtab.update(vtab)
        return rtabs

    def _rplc_fnt_tab(self):
        fg = self.fntgen
        chst = self.chst['font']
        base_code = chst.base_char
        r = []
        for code, ch in chst.iter_dychrs():
            r.append(fg.get_char(ch))
        return r, chst.base_char

    def _rplc_sfat_tab(self, as_sndbx):
        if not as_sndbx:
            return None
        conf = self.conf.get('sandbox', {}).get('scene', {})
        boot_idx = conf.get('boot', None)
        if boot_idx:
            r = {1: boot_idx}
        else:
            r = {}
        for fi, fv in conf.get('fat', {}).items():
            r[fi] = fv
        if not r:
            return None
        return r

    def _rplc_scrpt_tab(self, as_sndbx):
        if not as_sndbx:
            return None, None
        srom = self.srom['base']
        conf = self.conf.get('sandbox', {}).get('script', {})
        rtabs = {}
        for typ, tab in conf.items():
            if not tab:
                continue
            rtab = {}
            psr = make_script_parser(srom, typ)
            psr.refresh_sect_top()
            for idxp, cmds in tab.items():
                if isinstance(idxp, int):
                    idxp = (idxp,)
                prog = psr.get_program(*idxp)
                didxp = prog.page_idxs
                rtab[didxp] = (cmds, prog)
            if rtab:
                rtabs[typ] = rtab
        return rtabs.get('scene', None), rtabs.get('battle', None)

    def _rplc_oth_tabs(self, rtabs, as_sndbx):
        if not as_sndbx:
            return None
        conf = self.conf.get('sandbox', {}).get('direct', {})
        for tname, tab in conf.items():
            if tname in rtabs:
                raise ValueError('should not write tab {tname} directly')
            rtabs[tname] = tab

    def repack(self, as_sndbx = False):
        tbs = []
        for tn in ['comp', 'fcomp', 'trans']:
            report('info', f'encode txt: {tn}')
            rt = self._rplc_txt_tab(self.txts[tn])
            if rt:
                tbs.append(rt)
        artabs = self._merge_txt_tab(tbs)
        if not artabs:
            return None
        artabs['font'] = self._rplc_fnt_tab()
        artabs['s_fat'] = self._rplc_sfat_tab(as_sndbx)
        artabs['s_scrpt'], artabs['b_scrpt'] = self._rplc_scrpt_tab(as_sndbx)
        self._rplc_oth_tabs(artabs, as_sndbx)
        rmk, dirty = self.srom['base'].repack_with(artabs)
        if not dirty:
            return None
        return rmk

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    def main():
        global md, rmk
        md = c_ffta_modifier(CONF)
        md.load()
##        txts = md._parse_text('text')
##        md.save_json('out_cn_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
##        txts = md._parse_text('base')
##        md.save_json('out_us_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
##        txts, utxts = md.parse_texts(True, True)
##        md.save_json('out_wk.json', txts)
##        md.save_json('out_ut_wk.json', utxts)
##        rmk = md.repack_rom_with_text(txts)
##        md.save_rom('ffta_tst_uscn.gba', rmk)
        rmk = md.export()
    main()
