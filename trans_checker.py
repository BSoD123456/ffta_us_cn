#! python3
# coding: utf-8

import json, re

class c_trans_checker:

    ignore_ctrls = ['4D']

    def __init__(self, fn):
        self.txts = self.load_json(fn)

    def load_json(self, fn):
        with open(fn, 'r', encoding = 'utf-8') as fd:
            return json.load(fd)

    def save_json(self, fn, obj):
        with open(fn, 'w', encoding = 'utf-8') as fd:
            json.dump(obj, fd,
                ensure_ascii=False, indent=4, sort_keys=False)

    def _pick_txt_ctrls(self, txt):
        ctrls = re.findall(r'\@\[([0-9a-fA-F ]+)\]', txt)
        if not txt.count('@') == txt.count('[') == txt.count(']') == len(ctrls):
            self.report('error', 'invalid ctrl symbol in text')
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
                self.report('warning', f'unmatched ctrl symbol: (clen) / -> {dc}')
            else:
                self.report('warning', f'unmatched ctrl symbol: (clen) {sc} -> /')
            return False
        return True

    def check(self):
        for tname, tab in self.txts.items():
            for idxr, (src, dst) in tab.items():
                if not dst or dst.startswith('#'):
                    continue
                self.cpos = (tname, idxr)
                if dst.startswith('*'):
                    dst = dst[1:]
                self._check_valid_trans(src, dst)

    def report(self, lvl, msg):
        tname, idxr = self.cpos
        print(f'[{tname} {idxr}: {lvl}]: ', msg)
    
if __name__ == '__main__':
    tc = c_trans_checker('trans_txt.json')
    tc.check()
