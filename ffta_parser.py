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

def cmdc(code, typ = 'unknown', rpr = None):
    def _hndl(cls, mname, mth):
        #if not hasattr(cls, '_cmd_tab'):
        # in __dict__ is the same as js hasOwnProperty
        # but hasattr check parents
        if not '_cmd_tab' in cls.__dict__:
            cls._cmd_tab = {}
        nm = mth.__name__
        assert nm.startswith('cmd_')
        nm = nm[4:]
        if isinstance(code, int):
            codes = (code,)
        else:
            codes = code
        for c in codes:
            cls._cmd_tab[c] = (mth, typ, nm, rpr)
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

    @staticmethod
    def _p16(prms, idx):
        return prms[idx] + (prms[idx + 1] << 8)

    def exec(self, psr, rslt = None):
        if rslt is None:
            rslt = {}
        rslt.update({
            'step': [len(self)],
            'type': 'unknown',
        })
        if self.op in self._cmd_tab:
            # self._cmd_tab[op][0].__get__(self, type(self)) to bind cmdfunc
            cmdfunc, cmdtyp, cmdnm, cmdrpr = self._cmd_tab[self.op]
            rslt['type'] = cmdtyp
            rslt['name'] = cmdnm
            rslt['repr'] = cmdrpr
            rslt['output'] = cmdfunc(self, self.prms, psr, rslt)
        return rslt

    def __repr__(self):
        prms_rpr = type(self.prms).hex(self.prms)
        prms_rpr = ' '.join(prms_rpr[i:i+2] for i in range(0, len(prms_rpr), 2))
        return f'<{self.op:X}: {prms_rpr.upper()}>'

class c_ffta_scene_cmd(c_ffta_cmd):

    _CMDC_TOP = 0x72

    #tips:
    #<44: ?? idx ?? ??> path move, path idxed from the tabref after s_fat

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
        try:
            t_line = t_page[tidx]
            toks = t_page[tidx].text.tokens
        except:
            rslt['txt_invalid'] = True
            toks = f'text with invalid tidx {tidx}'
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
    @cmdc(0x19, 'flow', 'jump {out:0>4x}')
    def cmd_jump(self, prms, psr, rslt):
        v = self._p16(prms, -2)
        if 0x8000 & v:
            v -= 0x10000
        v += len(prms) + 1
        rslt['flow_offset'] = v
        return v + rslt['offset']

    #cmd: call ?
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x1, 'flow', 'call {out:0>4x}')
    def cmd_call(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt)

    #cmd: wait
    #params: p1(u8)
    #p1: waited frames, 1/60 sec
    @cmdc(0x15, 'time', 'wait {out:d} frms')
    def cmd_wait(self, prms, psr, rslt):
        return prms[0]

    #cmd: fade
    #params: p1(u8) p2(u8) p3(u8)
    #p1: 0x31 fade out / 0x13 fade in
    #p2: duration frames, 1/60 sec
    #p3: end brightness 0~0x64(100)
    @cmdc(0x6, 'effect',
        lambda o, c: (
            lambda io, dur, br:
                f'fade {io} with {dur} frms to {br}%'
        )('out' if o[0] else 'in', o[1], o[2])
    )
    def cmd_fade(self, prms, psr, rslt):
        io = prms[0]
        is_out = ((io >> 4) > (io & 0xf))
        dur = prms[1]
        br = prms[2]
        return is_out, dur, br

    #cmd: end thread
    #params: -
    @cmdc(0x02, 'thread', 'ret')
    def cmd_end_thread(self, prms, psr, rslt):
        pass

    #cmd: switch thread
    #params: p1(u8)
    #p1: thread idx
    @cmdc(0x03, 'thread', 'sw_thread {out}')
    def cmd_uk1_thread(self, prms, psr, rslt):
        return prms[0]

    #cmd: new thread
    #params: -
    #eq to <03: ff>
    @cmdc(0x04, 'thread', 'new_thread')
    def cmd_new_thread(self, prms, psr, rslt):
        pass

    #cmd: load scene
    #params: p1(u16)
    #p1: scene idx in s_fat
    @cmdc(0x1c, 'load', 'load scene {out}')
    def cmd_load_scene(self, prms, psr, rslt):
        return self._p16(prms, 0)

    #cmd: done scene
    #params: ?
    @cmdc(0x17, 'flow')
    def cmd_done_scene(self, prms, psr, rslt):
        pass

class c_ffta_battle_cmd(c_ffta_cmd):

    _CMDC_TOP = 0x12

    #cmd: nop
    #params:
    @cmdc(0x00, 'none', 'nop')
    def cmd_nop(self, prms, psr, rslt):
        return None

    #cmd: jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x01, 'flow', 'jump {out:0>4x}')
    def cmd_jump(self, prms, psr, rslt):
        v = self._p16(prms, -2)
        if 0x8000 & v:
            v -= 0x10000
        v += len(prms) + 1
        rslt['flow_offset'] = v
        return v + rslt['offset']

    #cmd: set flag
    #params: p1(u16) p2(u8)
    #p1: flag idx
    #p2: dest value
    @cmdc(0x02, 'stat', 'set flg:{out[0]:x} = {out[1]}')
    def cmd_set_flg(self, prms, psr, rslt):
        return self._p16(prms, 0), prms[2]

    #cmd: test flag jump
    #params: p1(u16) p2(u16)
    #p1: flag idx
    #p2: cur cmd offset increment
    @cmdc(0x04, 'flow', 'if flg:{out[1]:x} jump {out[0]:0>4x}')
    def cmd_test_flg_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), self._p16(prms, 0)

    #cmd: load scene
    #params: ?
    @cmdc(0x05, 'load', 'load scene {out}')
    def cmd_load_scene(self, prms, psr, rslt):
        return self._p16(prms, 0)

    #cmd: test chara stat1 jump
    #params: p1(u8) p2(u16)
    #p1: character idx
    #p2: cur cmd offset increment
    @cmdc(0x06, 'flow', 'if ch:{out[1]:x} is st1 jump {out[0]:0>4x}')
    def cmd_test_cha_st1_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0]

    #cmd: test cur chara attr101 jump
    #params: p1(u8) p2(u8) p3(u16)
    #p1: character idx
    #p2: dest value
    #p3: cur cmd offset increment
    @cmdc(0x07, 'flow', 'if cur_ch:{out[1]:x}.a101={out[2]} jump {out[0]:0>4x}')
    def cmd_test_cha_c_a101_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0], prms[1]

    #cmd: test gv1 jump
    #params: p1(u16) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc(0x08, 'flow', 'if gv1={out[1]} jump {out[0]:0>4x}')
    def cmd_test_gv1_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), self._p16(prms, 0)

    #cmd: test chara attr18 jump
    #params: p1(u8) p2(u8) p3(u16)
    #p1: character idx
    #p2: dest value
    #p3: cur cmd offset increment
    @cmdc(0x09, 'flow', 'if ch:{out[1]:x}.a18>={out[2]} jump {out[0]:0>4x}')
    def cmd_test_cha_a18_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0], prms[1]

    #cmd: test find chara by a4 jump
    #params: p1(u8) p2(u16)
    #p1: dest character attr 4 value
    #p2: cur cmd offset increment
    @cmdc(0x0a, 'flow', 'if ch.a4={out[1]} found jump {out[0]:0>4x}')
    def cmd_test_cha_f_a4_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0]

    #cmd: test sum cha a101 jump
    #params: p1(u8) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc(0x0b, 'flow', 'if sum(ch.a101)={out[1]} jump {out[0]:0>4x}')
    def cmd_test_sum_cha_a101_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0]

    #cmd: test gv2 jump
    #params: p1(u8) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc((0x0c, 0xd), 'flow', 'if gv2={out[1]} jump {out[0]:0>4x}')
    def cmd_test_gv2_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt), prms[0]

    #cmd: test some chara1 st2 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x0e, 'flow', 'if ch:s1 is st2 jump {out:0>4x}')
    def cmd_test_cha_s1_st2_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt)

    #cmd: test find chara a4=0x0d and gv3=0x140 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x0f, 'flow', 'if ch.a4=0xd found and gv3=0x140 jump {out:0>4x}')
    def cmd_test_cha_s1_st2_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt)

    #cmd: test gcondi1 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x10, 'flow', 'if gc1 jump {out:0>4x}')
    def cmd_test_cha_s1_st2_jump(self, prms, psr, rslt):
        return self.cmd_jump(prms, psr, rslt)

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
        }, (pi1, pi2))

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

    def _dummy_program(self, pi1, pi2):
        return self.get_program(pi1, pi2)

    def refresh_sect_top(self):
        sect = self.sects['script']
        for pi1 in sect.last_idxs:
            sub = sect[pi1]
            for pi2 in sub.last_idxs:
                self._dummy_program(pi1, pi2)

    def iter_program(self, pi1 = None):
        sect = self.sects['script']
        if pi1 is None:
            idxprv = tuple()
        else:
            sect = sect[pi1]
            idxprv = (pi1,)
        for idxp, _ in sect.iter_item():
            prog = self.get_program(*idxprv, *idxp)
            if prog:
                yield prog

class c_ffta_script_program:

    EOSCRPT = 0xff

    def __init__(self, sects, page_idxs):
        self.sects = sects
        self.page_idxs = page_idxs
        self.page_idx = page_idxs

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
        inv_cofs = None
        for rdy, cofs, cop, cprms_or_cb in sect_spage.iter_lines_to(max_ofs):
            if rdy:
                cprms = cprms_or_cb
            else:
                clen = sect_cmds.get_cmd_len(cop)
                cprms = cprms_or_cb(clen)
            cmd = self._new_cmd(cop, cprms, cls_cmd)
            if cmd is None:
                assert callable(cprms_or_cb)
                cprms_or_cb(None)
                # end of script padding
                assert cop == self.EOSCRPT
                inv_cofs = cofs
            else:
                cmds_tab[cofs] = cmd
                all_size = cofs + len(cmd)
        if inv_cofs:
            assert inv_cofs == all_size
            while True:
                if sect_spage.U8(inv_cofs) != self.EOSCRPT:
                    break
                inv_cofs += 1
            all_size = inv_cofs
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
            rslt = {
                'offset': cur_ofs,
                'cmd': cmd,
            }
            rslt = cmd.exec(self, rslt)
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
        prog = super().get_program(s_pi1, s_pi2, sect_text = stext, **kargs)
        if prog:
            prog.page_idx = idx
            prog.text_idx = t_pi
        return prog

    def _new_program(self, pi1, pi2, *, sect_text):
        prog = super()._new_program(pi1, pi2)
        if prog is None:
            return None
        prog.sects['text'] = sect_text
        prog.sects['fx_text'] = self.sects['fx_text']
        prog.parse(c_ffta_scene_cmd)
        return prog

    def _dummy_program(self, pi1, pi2):
        return super().get_program(pi1, pi2, sect_text = None)

    def iter_program(self):
        sect = self.sects['fat']
        for i in range(1, sect.tsize):
            prog = self.get_program(i)
            if prog:
                yield prog

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
        if typ == 'text' and not rslt.get('txt_invalid', False):
            toks = rslt['output']
            rslt['output'] = self.charset.decode(toks)
        rrpr = rslt.get('repr', None)
        rout = rslt.get('output', None)
        if not rrpr is None:
            if callable(rrpr):
                rs = rrpr(rout, rslt['cmd'])
            elif isinstance(rrpr, str):
                rs = rslt['repr'].format(out = rout, cmd = rslt['cmd'])
            else:
                raise ValueError('invalid cmd repr')
        elif not rout is None:
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
#    relation
# ===============

class c_ffta_script_relation:

    def __init__(self, psr_s, psr_b):
        self.psr_s = psr_s
        self.psr_b = psr_b

    def _pck_rslt(self, rslt):
        nm = rslt['name']
        if not nm == 'load_scene':
            return None
        return rslt['output']

    def _scan(self, pname, psr, rtab, rtab_r, rchain, allidxs):
        for prog in psr.iter_program():
            src = (pname, prog.page_idx)
            allidxs.add(src)
            refs = set()
            for ref in prog.exec(
                    cb_pck = self._pck_rslt,
                    flt = ['load']):
                assert ref
                ref = ('sc', ref)
                refs.add(ref)
                if ref in rtab_r:
                    rr = rtab_r[ref]
                else:
                    rr = []
                    rtab_r[ref] = rr
                if not src in rr:
                    rr.append(src)
                if ref in rchain[0]:
                    rchain[0].remove(ref)
                    rchain[1].add(ref)
                if not (src in rchain[0] or src in rchain[1]):
                    rchain[0].add(src)
            if refs:
                rtab[src] = sorted(refs)

    def scan(self):
        rtab = {}
        rtab_r = {}
        rchain = (set(), set())
        allidxs = set()
        self._scan('sc', self.psr_s, rtab, rtab_r, rchain, allidxs)
        self._scan('bt', self.psr_b, rtab, rtab_r, rchain, allidxs)
        self.refer = rtab
        self.refer_rvs = rtab_r
        self.refer_heads = sorted(rchain[0])
        unref = []
        for i in allidxs:
            if not i in rtab_r and not i in rtab:
                unref.append(i)
        self.unrefer = sorted(unref)

# ===============
#      main
# ===============

def make_script_parser(rom, typ):
    if typ == 'scene':
        return c_ffta_scene_script_parser({
            'fat':      rom.tabs['s_fat'],
            'script':   rom.tabs['s_scrpt'],
            'cmds':     rom.tabs['s_cmds'],
            'text':     rom.tabs['s_text'],
            'fx_text':  rom.tabs['fx_text'],
        })
    elif typ == 'battle':
        return c_ffta_battle_script_parser({
            'script':   rom.tabs['b_scrpt'],
            'cmds':     rom.tabs['b_cmds'],
        })
    else:
        raise ValueError(f'invalid script type {typ}')

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

    spsr_s = make_script_parser(rom, 'scene')
    spsr_b = make_script_parser(rom, 'battle')

    def find_scene_by_txts(rom, tidxs):
        sfat = rom.tabs['s_fat']
        for i in range(sfat.tsize):
            pi1, pi2, ti = sfat.get_entry(i)
            if ti in tidxs:
                print(f'scene {i}: txt {ti}')

    def scan_rels():
        global srels
        srels = c_ffta_script_relation(spsr_s, spsr_b)
        srels.scan()
        ppr(srels.refer_heads)

    def _show_log(slog):
        for i, v in enumerate(slog.logs):
            print(f'{i}-{v}')

    def sc_show(page_idx = 1):
        _show_log(c_ffta_script_log(spsr_s.get_program(page_idx), chs))

    def bt_show(pi2 = 0, pi1 = 3):
        if pi2 is None:
            for prog in spsr_b.iter_program(pi1):
                print(f'page {prog.page_idxs[1]}:')
                _show_log(c_ffta_script_log(prog, chs))
        else:
            _show_log(c_ffta_script_log(spsr_b.get_program(pi1, pi2), chs))

