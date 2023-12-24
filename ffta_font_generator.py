#! python3
# coding: utf-8

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

    def _deco_char(self, src, dinfo, dst, dsz, dofs):
        dlen = len(dst)
        for si, v in enumerate(src):
            if v:
                # 0 is black, 1 is white
                continue
            sx = si % self.size
            sy = si // self.size
            for (px, py), dv in dinfo.items():
                pi = (sy + py + dofs[1]) * dsz + (sx + px + dofs[0])
                if 0 <= pi < dlen:
                    dst[pi] = dv

    def _peek_char_val(self, src, ssz, shp, pos):
        dim = 2
        dv = [1] * dim
        pr = [-i for i in self.offset[:dim]]
        for zi, (pv, sv) in enumerate(zip(pos, shp)):
            pr[zi % dim] += pv * dv[zi % dim]
            dv[zi % dim] *= sv
        if not (0 <= pr[0] < ssz
            and 0 <= pr[1] < ssz):
            return 0
        pi = pr[1] * ssz + pr[0]
        return src[pi]

    def _pack_char(self, d, dsz, shp, pos = None, si = None):
        if si is None:
            si = len(shp) - 1
        if pos is None:
            pos = [0] * len(shp)
        if si < 0:
            return self._peek_char_val(d, dsz, shp, pos)
        rng = shp[si]
        r = []
        for i in range(rng):
            npos = pos.copy()
            npos[si] = i
            r.append(self._pack_char(d, dsz, shp, npos, si - 1))
        return r

    def get_char(self, c):
        try:
            self._draw_char(c)
        except:
            report('warning', f'invalid char in ttf: {c}')
            return self.char_blank
        s = self.img.getdata()
        # 1px * 2 for deco padding
        dsz = self.size + 2
        d = [0] * (dsz ** 2)
        for deco in self.decos:
            # 1px for deco padding
            self._deco_char(s, deco, d, dsz, (1, 1))
        return self._pack_char(d, dsz, self.pshape)

def make_ffta_font_gen(name, size):
    return c_font_gen(
        name, size, [
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
        (0, 0)
    )

if __name__ == '__main__':
    pass
