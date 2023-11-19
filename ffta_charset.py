#! python3
# coding: utf-8

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
