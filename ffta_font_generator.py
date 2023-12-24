#! python3
# coding: utf-8

# from https://github.com/SolidZORO/zpix-pixel-font/releases
FONT_NAME = 'font/zpix.ttf'

import os, os.path

try:
    from PIL import Image, ImageDraw, ImageFont
except:
    print('''Install Pillow with
pip3 install pillow
or
pip install pillow
''')
    raise

def report(*args):
    r = ' '.join(a for a in args if a)
    print(r)
    return r

class c_font_gen:

    def __init__(self, name, size, decos, packshape, offset):
        self.size = size
        self.decos = decos
        self.pshape = packshape
        self.offset = offset
        try:
            font = ImageFont.FreeTypeFont(name, size, encoding='utf-8')
        except:
            name = os.path.basename(os.path.splitext(name)[0])
            font = ImageFont.truetype(name, size, encoding='utf-8')
        self.font = font
        self.img = Image.new("1", (size, size), color=0xff)
        self.idr = ImageDraw.Draw(self.img)
        self.char_blank = self.get_char('\0')

    def _draw_char(self, c):
        self.idr.rectangle([(0, 0), self.img.size], fill=0xff)
        self.idr.text((0, 0), c, fill=0, font=self.font, spacing=0)

    def _deco_char(self, src, dinfo, dst):
        slen = len(src)
        for si, v in enumerate(src):
            if v:
                # 0 is black, 1 is white
                continue
            sx = si % self.size
            sy = si // self.size
            for (px, py), dv in dinfo.items():
                pi = (sy + py) * self.size + (sx + px)
                if 0 <= pi < slen:
                    dst[pi] = dv

    def _peek_char_val(self, src, shp, pos):
        dim = 2
        dv = [1] * dim
        pr = [-i for i in self.offset[:dim]]
        for zi, (pv, sv) in enumerate(zip(pos, shp)):
            pr[zi % dim] += pv * dv[zi % dim]
            dv[zi % dim] *= sv
        if not (0 <= pr[0] < self.size
            and 0 <= pr[1] < self.size):
            return 0
        pi = pr[1] * self.size + pr[0]
        return src[pi]

    def _pack_char(self, d, shp, pos = None, si = None):
        if si is None:
            si = len(shp) - 1
        if pos is None:
            pos = [0] * len(shp)
        if si < 0:
            return self._peek_char_val(d, shp, pos)
        rng = shp[si]
        r = []
        for i in range(rng):
            npos = pos.copy()
            npos[si] = i
            r.append(self._pack_char(d, shp, npos, si - 1))
        return r

    def get_char(self, c):
        try:
            self._draw_char(c)
        except:
            report('warning', f'invalid char in ttf: {c}')
            return self.char_blank
        s = self.img.getdata()
        d = [0] * (self.size ** 2)
        for deco in self.decos:
            self._deco_char(s, deco, d)
        return self._pack_char(d, self.pshape)

ffta_font_gen = c_font_gen(
    FONT_NAME, 12, [
        # outline
        {
            (-1, -1): 1,
            ( 0, -1): 1,
            ( 1, -1): 1,
            (-1,  0): 1,
            ( 1,  0): 1,
            (-1,  1): 1,
            ( 0,  1): 1,
            ( 1,  1): 1,
        },
        # shadow
        {
            ( 1,  1): 2,
        },
        # center
        {
            ( 0,  0): 3,
        },
    ],
    (8, 16, 2),
    (0, 2)
)

if __name__ == '__main__':
    pass
