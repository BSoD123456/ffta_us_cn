#! python3
# coding: utf-8

CONF = {
    'roms': {
        'src': {
            'base': {
                'path': 'fftaus.gba',
                'type': 'us',
                'charset': 'charset_us.json',
            },
            'text': {
                'path': 'fftacnb.gba',
                'type': 'cn',
                'charset': 'charset_cn.json',
                'charset_ocr': True,
            },
            'font': {
                'path': 'fftacns.gba',
                'type': 'cn',
            },
        },
        'dst': {
            'path': 'fftauscn.gba',
            'type': 'us',
        },
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
        'var': {
            'prefix': ['CRN_'],
        },
        'align': {
            's_text': [
                ((36,), (35,)),
                ((60,), (60,)),
            ],
            'b_text': [
                ((54,), (51,)),
            ],
            'fx_text': [
                ((8, 60), (8, 58)),
                ((8, 61), (8, 60)),
                ((8, 62), (8, 62)),
                ((25,), (24,)),
            ],
        },
        'trim': {
            's_text': [{
                (61,),
            }, {
                (61,),
            }],
        }
    }
}

def chk_has_japanese(txt):
    for c in txt:
        oc = ord(c)
        if (0x3040 < oc < 0x3094 or
            0x30a0 < oc < 0x30fb):
            return True
    return False
CONF['text']['skipf'].append(chk_has_japanese)

import json, re

from ffta_sect import load_rom
from ffta_charset import c_ffta_charset_ocr

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

    @staticmethod
    def _iter_txttab(rom):
        for tname, tab in rom.tabs.items():
            if tname.endswith('text'):
                yield tname, tab
            elif tname == 'words':
                for stname, stab in tab.items():
                    yield ':'.join((tname, stname)), stab

    def _parse_text(self, romkey):
        rom = self.srom[romkey]
        chst = self.chst[romkey]
        txt_skip = self.conf['text']['skip']
        txt_skip_fs = self.conf['text']['skipf']
        txts = {}
        for tname, tab in self._iter_txttab(rom):
            ttxts = {}
            for path, line in tab.iter_item(skiprep = True):
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
                    if sf(dec):
                        #report('warning', f'skip text {path}: {dec}')
                        dec = '#' + dec
                        break
                ttxts[pkey] = dec
            txts[tname] = ttxts
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
        var_prefix = self.conf['text']['var']['prefix']
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
                    #if tval and re.match(r'^[0-9A-Z_]+$', bval):
                    for vp in var_prefix:
                        if bval.startswith(vp):
                            #report('warning', f'varname: {bval} -> {tval}')
                            if tval:
                                tval = '#' + tval
                rtab[pkey] = [i if i else '' for i in [bval, tval]]
                if not tval or tval.startswith('#'):
                    if bval and not bval.startswith('#'):
                        rutab[pkey] = [bval, tval if tval else '']
            if rutab:
                utrslt[tname] = rutab
        return trslt, utrslt

    def parse_texts(self, atxt = True, utxt = False):
        bt = self._parse_text('base')
        tt = self._parse_text('text')
        t, ut = self._merge_texts(bt, tt, None)
        if atxt & utxt:
            return t, ut
        elif atxt:
            return t
        elif utxt:
            return ut

    def _rplc_txt_tab(self, mtxt):
        rtabs = {}
        for tname, tab in mtxt.items():
            if tname.startswith('#'):
                continue
            report('info', f'encode tab:{tname}')
            rtab = {}
            for idxr, (src, dst) in tab.items():
                if not dst or idxr.startswith('#'):
                    continue
                #report('info', f'encode line {idxr}')
                dst = self.chst['text'].encode(dst)
                if not dst:
                    continue
                idxp = tuple(int(i) for i in idxr.split('/'))
                rtab[idxp] = dst
            if rtab:
                rtabs[tname] = rtab
        return rtabs

    def repack_rom_with_text(self, mtxt):
        rtabs = self._rplc_txt_tab(mtxt)
        if not rtabs:
            return None
        rtabs['font'] = self.srom['font'].tabs['font']
        rmk, dirty = self.srom['base'].repack_with(rtabs)
        if not dirty:
            return None
        return rmk

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    def main():
        global md
        md = c_ffta_modifier(CONF)
        md.load()
        txts = md._parse_text('text')
        md.save_json('out_cn_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
        txts = md._parse_text('base')
        md.save_json('out_us_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
        txts, utxts = md.parse_texts(True, True)
        md.save_json('out_wk.json', txts)
        md.save_json('out_ut_wk.json', utxts)
        rmk = md.repack_rom_with_text(txts)
        md.save_rom('ffta_tst_uscn.gba', rmk)
    main()
