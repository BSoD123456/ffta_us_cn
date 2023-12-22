#! python3
# coding: utf-8

import json

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

class c_ffta_charset_ocr(c_ffta_charset):

    def __init__(self, path, rom):
        super().__init__()
        self.rom = rom
        self.path = path

    def load(self):
        try:
            with open(self.path, 'r', encoding = 'utf-8') as fd:
                cs, csr = json.load(fd)
            self.chst = {int(k): v for k, v in cs.items()}
            self.chst_r = csr
        except:
            self.ocr()

    def save(self):
        with open(self.path, 'w', encoding = 'utf-8') as fd:
            json.dump((self.chst, self.chst_r), fd,
                ensure_ascii=False, indent=4, sort_keys=True)

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

    def _decode_unknown(self, typ, code):
        if typ == 'CTR_FUNC':
            return self._decode_ctr(typ, code)
        elif typ == 'CTR_EOS':
            return '@[ ]'
        else:
            return '@[E:{typ}:{code:X}]'

    def _decode_ctr(self, typ, code):
        if code == 0x52:
            return ' '
        else:
            return f'@[{code:X}]'

    def _decode_char(self, typ, code):
        if code in self.chst:
            return self.chst[code]
        else:
            return '@[U:{code:X}]'

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint
    ppr = lambda *a, **ka: pprint(*a, **ka, sort_dicts = False)

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_cn

    chs_us = c_ffta_charset_ocr('charset_us.json', None)
    chs_us.load()
    chs_cn = c_ffta_charset_ocr('charset_cn.json', rom_cn)
    chs_cn.load()
