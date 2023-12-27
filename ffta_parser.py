#! python3
# coding: utf-8

# ===============
#     common
# ===============

INF = float('inf')

def clsdec(hndl, *args, **kargs):
    class _dec:
        def __init__(self, mth):
            self.mth = mth
        def __set_name__(self, cls, mname):
            nmth = hndl(cls, mname, self.mth, *args, **kargs)
            if nmth is None:
                nmth = self.mth
            setattr(cls, mname, nmth)
    return _dec

# ===============
#   ffta spec
# ===============

# ===============
#    scripts
# ===============

def cmdc(code, typ = 'unknown'):
    def _hndl(cls, mname, mth):
        #if not hasattr(cls, '_cmd_tab'):
        # in __dict__ is the same as js hasOwnProperty
        # but hasattr check parents
        if not '_cmd_tab' in cls.__dict__:
            cls._cmd_tab = {}
        cls._cmd_tab[code] = (mth, typ)
    return clsdec(_hndl)

class c_ffta_cmd:

    _CMDC_TOP = 0xff

    _cmd_tab = {}

    def __init__(self, op, prms):
        if not 0 <= op < self._CMDC_TOP:
            raise ValueError('invalid opcode')
        self.op = op
        self.prms = prms

    def __len__(self):
        return 1 + len(self.prms)

    def exec(self, psr):
        rslt = {
            'step': [len(self)],
            'type': 'unknown',
        }
        if self.op in self._cmd_tab:
            # self._cmd_tab[op][0].__get__(self, type(self)) to bind cmdfunc
            cmdfunc, cmdtyp = self._cmd_tab[self.op]
            rslt['type'] = cmdtyp
            rslt['output'] = cmdfunc(self, self.prms, psr, rslt)
        return rslt

    def __repr__(self):
        prms_rpr = type(self.prms).hex(self.prms)
        prms_rpr = ' '.join(prms_rpr[i:i+2] for i in range(0, len(prms_rpr), 2))
        return f'<{self.op:X}: {prms_rpr.upper()}>'

class c_ffta_scene_cmd(c_ffta_cmd):

    _CMDC_TOP = 0x72

    #cmd: text window
    #params: p1(u8) p2(u8) p3(u8)
    #p1: index of text on this page
    #p2: index of portrait
    #p3: flags, 80: left, 82: right
    @cmdc(0x0f, 'text')
    def cmd_text(self, prms, psr, rslt):
        tidx = prms[0]
        rslt['win_type'] = 'normal'
        rslt['win_portrait'] = prms[1]
        t_page = psr.sects['text']
        t_line = t_page[tidx]
        toks = t_page[tidx].text.tokens
        return toks

    #cmd: text window with ask(yes or no) / notice
    #params: p1(u8)
    #p1: index of text on this page
    @cmdc(0x12, 'text')
    def cmd_text_yon(self, prms, psr, rslt):
        tidx = prms[0]
        if tidx > 0x80:
            tidx -= 0x80
            pidx = 1
            rslt['win_type'] = 'ask'
        else:
            pidx = 2
            rslt['win_type'] = 'notice'
        t_page = psr.sects['fx_text'][pidx]
        t_line = t_page[tidx]
        toks = t_page[tidx].text.tokens
        return toks

    #cmd: jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x19, 'flow')
    def cmd_jump(self, prms, psr, rslt):
        pass

    #cmd: new thread
    #params: ?
    @cmdc(0x04, 'thread')
    def cmd_new_thread(self, prms, psr, rslt):
        pass

    #cmd: end thread
    #params: ?
    @cmdc(0x02, 'thread')
    def cmd_end_thread(self, prms, psr, rslt):
        pass

    #cmd: load scene
    #params: ?
    @cmdc(0x1c, 'load')
    def cmd_load_scene(self, prms, psr, rslt):
        pass

class c_ffta_battle_cmd(c_ffta_cmd):

    _CMDC_TOP = 0x12

    #cmd: nop
    #params:
    @cmdc(0x00, 'none')
    def cmd_nop(self, prms, psr, rslt):
        return None

    #cmd: jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x01, 'flow')
    def cmd_jump(self, prms, psr, rslt):
        pass

    #cmd: test jump
    #params: ?
    @cmdc(0x04, 'flow')
    def cmd_test_jump(self, prms, psr, rslt):
        pass

    #cmd: load scene
    #params: ?
    @cmdc(0x05, 'load')
    def cmd_load_scene(self, prms, psr, rslt):
        pass

class c_ffta_script_parser:

    def __init__(self, sects):
        self.sects = sects
        self._progs = {}

    def _new_program(self, pi1, pi2):
        sects = self.sects
        try:
            spage = sects['script'][pi1][pi2]
        except IndexError:
            return None
        return c_ffta_script_program({
            'script': spage,
            'cmds': sects['cmds'],
        })

    def get_program(self, pi1, pi2, **kargs):
        pi = (pi1, pi2)
        progs = self._progs
        if pi in progs:
            prog = progs[pi]
        else:
            prog = self._new_program(pi1, pi2, **kargs)
            if prog is None:
                return None
            progs[pi] = prog
        return prog

class c_ffta_script_program:

    def __init__(self, sects):
        self.sects = sects

    def parse(self, cls_cmd):
        self._parse_cmds_page(cls_cmd)

    def reset(self):
        pass

    def _new_cmd(self, cmdop, prms, cls_cmd):
        try:
            return cls_cmd(cmdop, prms)
        except ValueError:
            return None

    def _parse_cmds_page(self, cls_cmd):
        sect_spage = self.sects['script']
        sect_cmds = self.sects['cmds']
        max_ofs = sect_spage._sect_top
        if not max_ofs is None:
            max_ofs -= 1
        cmds_tab = {}
        all_size = 0
        for rdy, cofs, cop, cprms_or_cb in sect_spage.iter_lines_to(max_ofs):
            if rdy:
                cprms = cprms_or_cb
            else:
                clen = sect_cmds.get_cmd_len(cop)
                cprms = cprms_or_cb(clen)
            cmd = self._new_cmd(cop, cprms, cls_cmd)
            if cmd is None:
                assert(callable(cprms_or_cb))
                cprms_or_cb(None)
            else:
                cmds_tab[cofs] = cmd
                all_size = cofs + len(cmd)
        self.cmds = cmds_tab
        sect_spage.set_real_top(all_size)
        self.page_size = all_size

    def get_cmd(self, ofs):
        return self.cmds.get(ofs, None)

    def _raise_rslt(self, ofs, msg, **kargs):
        kargs.update({
            'type': 'error',
            'offset': ofs,
            'output': msg,
        })
        return kargs

    def _hndl_rslt(self, rslt, flt, flt_out, cb_pck):
        typ = rslt['type']
        if not flt is None and not typ in flt:
            return None
        elif not flt_out is None and typ in flt_out:
            return None
        if callable(cb_pck):
            ro = cb_pck(rslt)
        else:
            ro = rslt['output']
        return ro

    def exec(self, st_ofs = 0, flt = None, flt_out = ['unknown'], cb_pck = None, wk = None):
        if wk is None:
            wk = set()
        cur_ofs = st_ofs
        page_size = self.page_size
        while True:
            if cur_ofs >= page_size:
                ro = self._hndl_rslt(
                    self._raise_rslt(cur_ofs, f'overflow 0x{page_size:x}'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            elif cur_ofs in wk:
                ro = self._hndl_rslt(
                    self._raise_rslt(cur_ofs, 'walked skip'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            cmd = self.get_cmd(cur_ofs)
            if cmd is None:
                ro = self._hndl_rslt(
                    self._raise_rslt(cur_ofs, f'no valid cmd'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            rslt = cmd.exec(self)
            rslt['offset'] = cur_ofs
            rslt['cmd'] = cmd
            wk.add(cur_ofs)
            ro = self._hndl_rslt(rslt, flt, flt_out, cb_pck)
            if not ro is None:
                yield ro
            stps = rslt['step']
            if len(stps) == 0:
                break
            for stp in stps[:-1]:
                nxt_ofs = cur_ofs + stp
                yield from self.exec(
                    nxt_ofs, flt, flt_out, cb_pck, wk)
            cur_ofs += stps[-1]

# ===============
#     scene
# ===============

class c_ffta_scene_script_parser(c_ffta_script_parser):

    def _get_fat_entry(self, idx):
        assert(idx > 0)
        s_pi1, s_pi2, t_pi = self.sects['fat'].get_entry(idx)
        return s_pi1, s_pi2, t_pi

    def get_program(self, idx, **kargs):
        s_pi1, s_pi2, t_pi = self._get_fat_entry(idx)
        stext = self.sects['text'][t_pi]
        return super().get_program(s_pi1, s_pi2, sect_text = stext, **kargs)

    def _new_program(self, pi1, pi2, *, sect_text):
        prog = super()._new_program(pi1, pi2)
        if prog is None:
            return None
        prog.sects['text'] = sect_text
        prog.sects['fx_text'] = self.sects['fx_text']
        prog.parse(c_ffta_scene_cmd)
        return prog

# ===============
#     battle
# ===============

class c_ffta_battle_script_parser(c_ffta_script_parser):

    def _new_program(self, pi1, pi2):
        prog = super()._new_program(pi1, pi2)
        if prog is None:
            return None
        prog.parse(c_ffta_battle_cmd)
        return prog

# ===============
#      log
# ===============

class c_ffta_script_log:

    def __init__(self, prog, charset):
        self.prog = prog
        self.charset = charset
        self._exec()

    def _pck_rslt(self, rslt):
        typ = rslt['type']
        if typ == 'text':
            toks = rslt['output']
            rs = self.charset.decode(toks)
        elif typ == 'error':
            rs = rslt['output']
        else:
            rs = str(rslt['cmd'])
        if 'cmd' in rslt:
            cmdop = f"{rslt['cmd'].op:0>2X}"
        else:
            cmdop = '--'
        return f'{rslt["offset"]:0>4x}({typ[:3]:<3s}:{cmdop}): {rs}'

    def _exec(self):
        log = []
        self.logs = log
        for line in self.prog.exec(
                cb_pck = self._pck_rslt,
                flt_out = None):
            log.append(line)

# ===============
#      main
# ===============

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us, rom_jp, rom_cn
    rom = rom_us

    if False:
        from ffta_charset import c_ffta_charset_us_dummy as c_charset
        chs = c_charset()
    elif True:
        from ffta_charset import c_ffta_charset_ocr
        chs_cn = c_ffta_charset_ocr('charset_cn.json', rom_cn)
        chs_cn.load()
        chs = chs_cn

    def enum_text(page_idx, ln = 0x100, tkey = 'text'):
        t_page = spsr_s.sects[tkey][page_idx]
        charset = chs
        for i in range(ln):
            try:
                toks = t_page[i].text.tokens
            except:
                print(hex(i), '--failed--')
                break
            dec = charset.decode(toks)
            print(hex(i), dec)

    def enum_all_text(tkey):
        t_sect = spsr_s.sects[tkey]
        charset = chs
        for path, t_line in t_sect.iter_item():
            if t_line is None:
                continue
            toks = t_line.text.tokens
            dec = charset.decode(toks)
            rpath = '/'.join(str(i) for i in path)
            print(f'{rpath}: {dec}')

    def main(page_idx = 1):
        global spsr_s, spsr_b
        spsr_s = c_ffta_scene_script_parser({
            'fat':      rom.tabs['s_fat'],
            'script':   rom.tabs['s_scrpt'],
            'cmds':     rom.tabs['s_cmds'],
            'text':     rom.tabs['s_text'],
            'fx_text':  rom.tabs['fx_text'],
        })
        spsr_b = c_ffta_battle_script_parser({
            'script':   rom.tabs['b_scrpt'],
            'cmds':     rom.tabs['b_cmds'],
        })
        global slog_s
        slog_s = c_ffta_script_log(spsr_s.get_program(page_idx), chs)
    main(6)
