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
}

import json

from ffta_sect import load_rom
from ffta_charset import c_ffta_charset_ocr

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

    def parse_text(self, romkey):
        rom = self.srom[romkey]
        chst = self.chst[romkey]
        txts = {}
        for tname, tab in self._iter_txttab(rom):
            ttxts = {}
            for path, line in tab.iter_item():
                if line is None:
                    continue
                try:
                    line = line.text
                except:
                    pass
                pkey = '/'.join(str(i) for i in path)
                dec = chst.decode(line.tokens)
                ttxts[pkey] = dec
            txts[tname] = ttxts
        return txts

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    def main():
        global md
        md = c_ffta_modifier(CONF)
        md.load()
        txts = md.parse_text('text')
        md.save_json('out_wk.json', txts)
        txts = md.parse_text('base')
        md.save_json('out_us_wk.json', txts)
    main()
