#! python3
# coding: utf-8

import os, os.path
import json

class c_trans_fmt:

    def __init__(self, src_fn, raw_fn, trans_fn, blk_sz = 10):
        self.src_fn = src_fn
        s1, s2 = os.path.splitext(src_fn)
        self.dst_fn = s1 + '_auto' + s2
        self.raw_fn = raw_fn
        self.trs_fn = trans_fn
        self.blk_sz = blk_sz

    def load(self):
        self.tab = self.load_json(self.src_fn)
        raw_txt = self.load_txt(self.raw_fn)
        if not raw_txt:
            raw_txt = self.export_raw()
            self.save_txt(self.raw_fn, raw_txt)
        self.raw_txt = raw_txt
        trs_txt = self.load_txt(self.trs_fn)
        if not trs_txt:
            trs_txt = []
            self.save_txt(self.trs_fn, trs_txt)
        self.trs_txt = trs_txt

    def export(self):
        if not self.trs_txt:
            return
        self.import_trans()
        self.save_json(self.dst_fn, self.tab)

    def _iter_text(self):
        for tname, tab in self.tab.items():
            for idxr, tpair in tab.items():
                st, tt = tpair
                if tt and not tt.startswith('#'):
                    continue
                r = yield st
                if r and not r.startswith('#'):
                    tpair[1] = '#' + r

    def export_raw(self):
        lines = []
        for i, txt in enumerate(self._iter_text()):
            if i > 0 and i % self.blk_sz == 0:
                lines.append('')
            lines.append(txt)
        return lines

    def import_trans(self):
        rit = self._iter_text()
        rt = next(rit)
        is_done = False
        for st, tt in zip(self.raw_txt, self.trs_txt):
            assert not is_done
            if not st:
                assert not tt
                continue
            assert st and tt
            assert rt == st
            try:
                rt = rit.send(tt)
            except:
                is_done = True

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

    def load_txt(self, fn):
        try:
            with open(fn, 'r', encoding = 'utf-8') as fd:
                return fd.read().splitlines()
        except:
            return None

    def save_txt(self, fn, txts):
        with open(fn, 'w', encoding = 'utf-8') as fd:
            for t in txts:
                fd.write(t)
                fd.write('\n')

if __name__ == '__main__':
    import pdb

    def main():
        global tf
        tf = c_trans_fmt('trans_txt.json', 'at_raw_wk.txt', 'at_trans_wk.txt')
        tf.load()
        tf.export()
    main()
