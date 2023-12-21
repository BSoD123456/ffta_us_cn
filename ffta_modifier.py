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
        },
        'align': {
            's_text': [
                ((36,), (35,)),
                ((60,), (60,)),
            ],
        },
    }
}

import json

from ffta_sect import load_rom
from ffta_charset import c_ffta_charset_ocr

INF = float('inf')

class c_tab_align_iter:

    def __init__(self, *tabs, align_map = []):
        self.tabs = tabs
        self.amap = self._hndl_amap(align_map)

    def _hndl_amap(self, align_map):
        ramap = []
        for idxps in align_map:
            ri = []
            mi = None
            mxidxp = None
            for i, idxp in enumerate(idxps):
                if mxidxp is None or self._cmp_idx(idxp, mxidxp) > 0:
                    mxidxp = idxp
                    mi = [i]
                elif self._cmp_idx(idxp, mxidxp) == 0:
                    mi.append(i)
                ri.append(idxp)
            for i in mi
                ri[i] = None
            ramap.append((mxidxp, ri))
        return ramap

    def _iter_tab(self, idx):
        yield from self.tabs[idx].items()

    def reset(self):
        self.stats = []
        for i in range(len(self.tabs)):
            itr = self._iter_tab(i)
            val = next(itr)
            self.stats.append([itr, val])

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
        return self._trim_idx(r)

    def _calc_cidx(self, idxp, si):
        cidxp = idxp
        for almnidxp, alidxps in self.amap:
            if self._cmp_idx(cidxp, almnidxp) < 0:
                break
            alidxp = alidxps[si]
            if alidxp is None:
                continue
            cidxp = self._add_idx(cidxp, almnidxp, alidxp)
        return cidxp

    def _next(self):
        mnidxp = None
        cidxps = []
        for si, (itr, (idxp, val)) in enumerate(self.stats):
            cidxp = self._calc_cidx(idxp, si)
            cidxps.append(cidxp)
            if mnidxp is None or self._cmp_idx(cidxp, mnidxp) < 0:
                mnidxp = cidxp
        if mnidxp and mnidxp[0] == INF:
            return None, True
        rs = []
        for sinfo, cidxp in zip(self.stats, cidxps):
            itr, (idxp, val) = sinfo
            if self._cmp_idx(cidxp, mnidxp) == 0:
                rs.append((idxp, val))
                try:
                    idxp, val = next(itr)
                except StopIteration:
                    idxp = (INF,)
                    val = None
                sinfo[1] = (idxp, val)
            else:
                rs.append((idxp, None))
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
            chst = c_ffta_charset_ocr(rom_conf['charset'], rom)
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
                ttxts[pkey] = dec
            txts[tname] = ttxts
        return txts

    def _merge_texts(self, tbas, ttxt, minfo):
        trslt = {}
        amaps = self.conf['text']['align']
        for tname, btab in tbas.items():
            ttab = ttxt[tname]
            rtab = {}
            trslt[tname] = rtab
            if tname in amaps:
                amap = amaps[tname]
            else:
                amap = []
            ta = c_tab_align_iter(btab, ttab, align_map = amap)
            for (bidxp, bval), (tidxp, tval) in ta.iter():
                if bval is None:
                    pkey = '#' + '/'.join(str(i) for i in tidxp)
                else:
                    pkey = '/'.join(str(i) for i in bidxp)
                rtab[pkey] = [i if i else '' for i in [bval, tval]]
        return trslt

    def parse_texts(self):
        bt = self._parse_text('base')
        tt = self._parse_text('text')
        return self._merge_texts(bt, tt, None)

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    def main():
        global md
        md = c_ffta_modifier(CONF)
        md.load()
        #txts = md._parse_text('text')
        #md.save_json('out_cn_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
        #txts = md._parse_text('base')
        #md.save_json('out_us_wk.json', {k:{'/'.join(str(i) for i in k):v for k, v in tab.items()} for k, tab in txts.items()})
        txts = md.parse_texts()
        md.save_json('out_wk.json', txts)
    main()
