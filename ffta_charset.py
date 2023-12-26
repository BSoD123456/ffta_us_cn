#! python3
# coding: utf-8

import json

def report(*args):
    r = ' '.join(a for a in args if a)
    print(r)
    return r

class c_ffta_charset:

    def _decode_char(self, typ, code):
        return char

    def _decode_unknown(self, typ, code):
        return None

    def _decode_tok(self, tok):
        typ, val = tok
        if typ.startswith('CHR_'):
            return self._decode_char(typ, val)
        else:
            return self._decode_unknown(typ, val)

    def decode_tokens(self, toks):
        for tok in toks:
            dc = self._decode_tok(tok)
            if dc:
                yield dc

    def decode(self, toks):
        return ''.join(self.decode_tokens(toks))

    def _encode_tok(self, gc):
        return NotImplemented

    def _encode_tokens(self, txt):
        def gc():
            for c in txt:
                yield c
        gci = gc()
        while True:
            ttyp, tchr = self._encode_tok(gci)
            if ttyp is None:
                continue
            elif ttyp == 'EOS':
                break
            yield ttyp, tchr

    def encode(self, txt):
        return list(self._encode_tokens(txt))

class c_ffta_charset_us_dummy(c_ffta_charset):

    def _decode_unknown(self, typ, code):
        #return f'[{typ}:{code:X}]'
        return ' '

    def _decode_char(self, typ, code):
        if code < 0xa6:
            d = '.'
        elif code < 0xb0:
            d = chr(code - 0xa6 + ord('0'))
        elif code < 0xca:
            d = chr(code - 0xb0 + ord('A'))
        elif code < 0xe4:
            d = chr(code - 0xca + ord('a'))
        else:
            d = '.'
        return d

class c_ffta_charset_base(c_ffta_charset):

    def __init__(self, path):
        super().__init__()
        self.path = path

    def reset(self):
        self.chst = {}
        self.chst_r = {}

    def load(self):
        try:
            with open(self.path, 'r', encoding = 'utf-8') as fd:
                cs, csr = json.load(fd)
            self.chst = {int(k): v for k, v in cs.items()}
            self.chst_r = csr
            return True
        except:
            self.reset()
            return False

    def save(self):
        with open(self.path, 'w', encoding = 'utf-8') as fd:
            json.dump((self.chst, self.chst_r), fd,
                ensure_ascii=False, indent=4, sort_keys=True)

    def _decode_unknown(self, typ, code):
        if typ == 'CTR_FUNC':
            return self._decode_ctr(typ, code)
        elif typ == 'CTR_EOS':
            return '@[ ]'
        else:
            return f'@[E:{typ}:{code:X}]'

    def _decode_ctr(self, typ, code):
        if code == 0x52:
            return ' '
        else:
            return f'@[{code:X}]'

    def _decode_char(self, typ, code):
        if code in self.chst:
            return self.chst[code]
        else:
            return f'@[U:{code:X}]'

    def _encode_char(self, char):
        if char in self.chst_r:
            return self.chst_r[char]
        else:
            return None

    def _encode_tok(self, gc):
        try:
            c = next(gc)
        except StopIteration:
            return 'EOS', 0
        if c == '#':
            return 'EOS', 0
        elif c == '@':
            c = next(gc)
            assert(c == '[')
            cs = []
            while True:
                c = next(gc)
                if c == ']':
                    break
                else:
                    cs.append(c)
            cs = ''.join(cs)
            if cs == ' ':
                return 'CTR_EOS', 0
            cs = cs.split(':')
            if cs[0] == 'U':
                return 'CHR_FULL', int(cs[1], 16)
            elif cs[0] == 'E':
                return cs[1], int(cs[2], 16)
            elif not len(cs) == 1:
                report('warning', f'unknown ctrl: {cs}')
                return None, None
            try:
                cv = int(cs[0], 16)
            except:
                report('warning', f'unknown ctrl: {cs[0]}')
                return None, None
            return 'CTR_FUNC', cv
        elif c == ' ':
            return 'CTR_FUNC', 0x52
        ch = self._encode_char(c)
        if ch is None:
            report('warning', f'unknown char: {c}')
            return None, None
        else:
            return 'CHR_FULL', self.chst_r[c]

class c_ffta_charset_ocr(c_ffta_charset_base):

    def __init__(self, path, rom):
        super().__init__(path)
        self.rom = rom

    def reset(self):
        self.ocr()

    def ocr(self):
        from ffta_font import c_ffta_font_drawer
        from ffta_ocr import c_ffta_ocr_parser, iter_toks
        if self.rom:
            dr = c_ffta_font_drawer(self.rom.tabs['font'])
            ocr = c_ffta_ocr_parser(iter_toks(self.rom), dr)
            ocr.parse()
            ocr.feed_all()
        else:
            ocr = c_ffta_ocr_parser(None, None)
            ocr.parse(noambi = True)
        self.chst, self.chst_r = ocr.final_charset()
        self.save()

class c_ffta_charset_dynamic(c_ffta_charset_base):

    def __init__(self, path, nosave = False):
        super().__init__(path)
        self.nosave = nosave

    def load(self, src, base):
        self.base_char = base
        if super().load():
            mxc = 0
            for c in src.chst:
                if c > mxc:
                    mxc = c
            self.chst_dyidx = mxc + 1
        else:
            for c, ch in src.chst.items():
                if c < base:
                    self.chst[c] = ch
            for ch, c in src.chst_r.items():
                if c < base:
                    self.chst_r[ch] = c
            self.chst_dyidx = base
        self.dirty = False

    def iter_dychrs(self):
        if self.dirty and not self.nosave:
            self.save()
        for c in range(self.base_char, self.chst_dyidx):
            yield c, self.chst[c]

    def _encode_char(self, char):
        ch = super()._encode_char(char)
        if ch is None:
            ch = self.chst_dyidx
            self.chst_dyidx += 1
            #report('debug', f'record new char {char} to 0x{ch:x}')
            self.chst_r[char] = ch
            self.chst[ch] = char
            self.dirty = True
        return ch
            
if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_cn

    def diff_chs(ofn, nfn):
        ochs = c_ffta_charset_ocr(ofn, None)
        ochs.load()
        nchs = c_ffta_charset_ocr(nfn, None)
        nchs.load()
        for code, ch in nchs.chst.items():
            if code in ochs.chst:
                och = ochs.chst[code]
                if och != ch:
                    print(f"0x{code:x}: '{och}', # {ch}")

    chs_us = c_ffta_charset_ocr('charset_us.json', None)
    chs_us.load()
    chs_cn = c_ffta_charset_ocr('charset_cn.json', rom_cn)
    chs_cn.load()
