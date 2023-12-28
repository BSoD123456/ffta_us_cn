#! python3
# coding: utf-8

import json, re
import os, os.path, shutil
import sys

class c_trans_checker:

    ignore_ctrls = ['4D']

    def __init__(self, fn):
        self.fn = fn
        self.txts = self.load_json(fn)
        self.nowarn = False
        self.err_cnt = 0

    def load_json(self, fn):
        with open(fn, 'r', encoding = 'utf-8') as fd:
            return json.load(fd)

    def save_json(self, fn, obj):
        with open(fn, 'w', encoding = 'utf-8') as fd:
            json.dump(obj, fd,
                ensure_ascii=False, indent=4, sort_keys=False)

    def bak_file(self, fn):
        if not os.path.isfile(fn):
            return
        f1, f2 = os.path.splitext(fn)
        shutil.copy2(fn, f1 + '.bak' + f2)

    def _pick_txt_ctrls(self, txt):
        def _rplc(m):
            return '-'
        dtxt = txt
        pt_c = r'\@\[([0-9 ][0-9a-fA-F]*)\]'
        pt_ci = r'^[0-9 ][0-9a-fA-F]*$'
        ctrls = re.findall(pt_c, dtxt)
        if ctrls:
            dtxt = re.sub(pt_c, _rplc, dtxt)
        pt_o = r'\@\[([A-Z]+\:[^\[\]]+)\]'
        oth_ctrls = re.findall(pt_o, dtxt)
        if oth_ctrls:
            dtxt = re.sub(pt_o, _rplc, dtxt)
        non_ctrls = re.findall(r'(?:^|[^\@])\[([^\[\]]+)\]', dtxt)
        for nc in non_ctrls:
            if re.match(pt_ci, nc):
                self.report('error', f'invalid ctrl symbol in text: {nc}')
        if not (
            txt.count('@') == len(ctrls) + len(oth_ctrls) and
            txt.count('[') == txt.count(']') == len(ctrls) + len(oth_ctrls) + len(non_ctrls) ):
            self.report('error', f'invalid ctrl symbol in text: {txt}')
            return None
        for ignb in self.ignore_ctrls:
            for ign in [ignb.upper(), ignb.lower()]:
                while True:
                    try:
                        ctrls.remove(ign)
                    except:
                        break
        return ctrls

    def _check_valid_trans(self, src, dst):
        sctr = self._pick_txt_ctrls(src)
        if sctr is None:
            return False
        dctr = self._pick_txt_ctrls(dst)
        if dctr is None:
            return False
        slen = len(sctr)
        dlen = len(dctr)
        if slen > dlen:
            clen = dlen
            ov = False
        elif slen < dlen:
            clen = slen
            ov = True
        else:
            clen = slen
            ov = None
        for i in range(clen):
            sc = sctr[i]
            dc = dctr[i]
            if sc.upper() != dc.upper():
                self.report('warning', f'unmatched ctrl symbol: ({i}) {sc} -> {dc}')
                return False
        if not ov is None:
            if ov:
                self.report('warning', f'unmatched ctrl symbol: (clen) / -> {dctr[clen]}')
            else:
                self.report('warning', f'unmatched ctrl symbol: (clen) {sctr[clen]} -> /')
            return False
        return True

    def check(self, nowarn = False):
        self.nowarn = nowarn
        cnts = [0, 0]
        for tname, tab in self.txts.items():
            for idxr, (src, dst) in tab.items():
                cnts[0] += 1
                if not dst or dst.startswith('#'):
                    continue
                cnts[1] += 1
                self.cpos = (tname, idxr)
                if dst.startswith('*'):
                    dst = dst[1:]
                self._check_valid_trans(src, dst)
        return cnts

    def _merge_txt(self, src, force_merge = False):
        for tname, tab in src.items():
            self.cpos = (tname, '-')
            if not tname in self.txts:
                self.report('warning', 'src tab not in trans')
                continue
            rtab = self.txts[tname]
            for idxr, (ts, td) in tab.items():
                self.cpos = (tname, idxr)
                if not idxr in rtab:
                    self.report('warning', 'text not in trans')
                    continue
        dirty = False
        for tname, tab in self.txts.items():
            if not tname in src:
                continue
            stab = src[tname]
            for idxr, tpair in tab.items():
                if not idxr in stab:
                    continue
                self.cpos = (tname, idxr)
                d_raw, d_trans = tpair
                s_raw, s_trans = stab[idxr]
                if not s_trans or s_trans.startswith('#'):
                    continue
                if s_trans.startswith('*'):
                    s_trans = s_trans[1:]
                if s_raw != d_raw:
                    self.report('warning', 'unmatched raw text')
                    continue
                if d_trans and not d_trans.startswith('#'):
                    if s_trans != d_trans:
                        em = f'unmatched trans text: {d_trans} / {s_trans}'
                        if force_merge:
                            self.report('warning', em)
                        else:
                            self.report('error', em)
                            continue
                    else:
                        continue
                tpair[1] = s_trans
                dirty = True
        return dirty

    def merge(self, src, **kargs):
        self.errors
        dirty = self._merge_txt(src.txts, **kargs)
        if self.errors == 0:
            if dirty:
                self.bak_file(self.fn)
                self.save_json(self.fn, self.txts)
        else:
            self.cpos = ('-', '-')
            self.report('error', 'merge failed')

    def report(self, lvl, msg):
        if self.nowarn and lvl == 'warning':
            return
        tname, idxr = self.cpos
        print(f'[{tname} {idxr}: {lvl}]: ', msg)
        if lvl == 'error':
            self.err_cnt += 1

    @property
    def errors(self):
        e = self.err_cnt
        self.err_cnt = 0
        return e
    
if __name__ == '__main__':

    FN_TRANS = 'trans_txt.json'
    def main(fn):
        if len(sys.argv) > 2 and sys.argv[2] == '-f':
            force_merge = True
        else:
            force_merge = False
        if len(sys.argv) > 1:
            mfn = sys.argv[1]
            mc = c_trans_checker(mfn)
            print(f'check {mfn}')
            mc.check()
            if mc.errors > 0:
                return
        else:
            mc = None
        tc = c_trans_checker(fn)
        if mc:
            print(f'merge {mfn}')
            tc.merge(mc, force_merge = force_merge)
            if tc.errors > 0:
                return
        print(f'check {fn}')
        cnts = tc.check()
        print(f'translated: {cnts[1]}/{cnts[0]}')
    main(FN_TRANS)
