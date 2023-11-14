#! python3
# coding: utf-8

try:
    from PIL import Image, ImageDraw
except:
    print('''
please install Pillow with
pip3 install pillow
or
pip install pillow
or
py -3 -m pip install pillow
or
python -m pip install pillow''')
    raise

class c_font_drawer:

    PAL = [(255, 255, 255), (100, 100, 100), (200, 200, 200), (0, 0, 0)]

    def __init__(self, font):
        self.sect = font

    def draw_char(self, cidx, half = False):
        pal = self.PAL
        sect = self.sect
        cw = None
        for line in sect.gen_char(cidx, half):
            rline = []
            for v in line:
                rline.append(pal[v])
            if cw is None:
                cw = len(rline)
            yield rline, True
        while True:
            rline = []
            for x in range(cw):
                rline.append(pal[0])
            yield rline, False

    def _draw_comment(self, width, height, txt):
        pal = self.PAL
        im = Image.new('RGB', (width, height), pal[0])
        dr = ImageDraw.Draw(im)
        dr.text((0, 0), txt, fill = pal[2])
        sq = im.getdata()
        w = im.width
        h = im.height
        for y in range(h):
            p = y * w
            rline = []
            for x in range(w):
                v = sq[p + x]
                rline.append(v)
            yield rline, True
        while True:
            rline = []
            for x in range(w):
                rline.append(pal[0])
            yield rline, False

    def draw_comment(self, txt):
        fw = 8
        fh = 12
        return self._draw_comment(fw*len(txt), fh, txt)

    @staticmethod
    def draw_padding(width, height):
        clr_blank = c_font_drawer.PAL[0]
        for y in range(height):
            rline = []
            for x in range(width):
                rline.append(clr_blank)
            yield rline, True
        while True:
            rline = []
            for x in range(width):
                rline.append(clr_blank)
            yield rline, False

    @staticmethod
    def draw_horiz(*blks, pad = 5):
        clr_blank = c_font_drawer.PAL[0]
        rwidth = 0
        while True:
            unfinished = False
            rline = []
            blen = len(blks)
            for i in range(blen):
                blk = blks[i]
                rl, uf = next(blk)
                if uf:
                    unfinished = True
                rline.extend(rl)
                if i < blen -1:
                    for x in range(pad):
                        rline.append(clr_blank)
            if not rwidth:
                rwidth = len(rline)
            if unfinished:
                yield rline, True
            else:
                break
        while True:
            rline = []
            for x in range(rwidth):
                rline.append(clr_blank)
            yield rline, False

    @staticmethod
    def draw_vert(*blks, pad = 10):
        clr_blank = c_font_drawer.PAL[0]
        blk_info = []
        for blk in blks:
            rl, uf = next(blk)
            if uf:
                blk_info.append((blk, rl, len(rl)))
        rwidth = max(p[2] for p in blk_info)
        blen = len(blk_info)
        for i in range(blen):
            blk, rl, rlen = blk_info[i]
            rl_pad = []
            for x in range(rwidth - rlen):
                rl_pad.append(clr_blank)
                rl.append(clr_blank)
            yield rl, True
            for rl, uf in blk:
                if not uf:
                    break
                if rl_pad:
                    rl.extend(rl_pad)
                yield rl, True
            if i < blen - 1:
                for y in range(pad):
                    rline = []
                    for x in range(rwidth):
                        rline.append(clr_blank)
                    yield rline, True
        while True:
            rline = []
            for x in range(rwidth):
                rline.append(clr_blank)
            yield rline, False

    def make_img(self, blk):
        dat = []
        bh = 0
        bw = 0
        for rl, uf in blk:
            if not uf:
                break
            if not bw:
                bw = len(rl)
            dat.extend(rl)
            bh += 1
        im = Image.new('RGB', (bw, bh))
        im.putdata(dat)
        return im

if __name__ == '__main__':
    
    from sect import main
    main()
    from sect import rom_us
    dr = c_font_drawer(rom_us.tabs['font'])
    im = dr.make_img(
        dr.draw_vert(
            dr.draw_comment('comment'),
            dr.draw_horiz(
                dr.draw_char(1), dr.draw_char(10),
            )
        )
    )
