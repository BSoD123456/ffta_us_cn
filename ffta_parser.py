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
        if 'thrd' in rslt:
            thrds = rslt['thrd']
        else:
            thrds = [{
                'ctx': None
            }]
            rslt['thrd'] = thrds
        for th in thrds:
            th['step'] = len(self)
        rslt.update({
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
        sc = self._p16(prms, 0)
        rslt['scene'] = sc
        return sc

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
        v += rslt['offset']
        rslt['dst_offset'] = v
        return v

    #cmd: set flag
    #params: p1(u16) p2(u8)
    #p1: flag idx
    #p2: dest value
    @cmdc(0x02, 'stat', 'set flg:{out[0]:x} = {out[1]}')
    def cmd_set_flg(self, prms, psr, rslt):
        fid = self._p16(prms, 0)
        dval = prms[2]
        assert dval in (0, 1)
        rslt['var'] = ('flg', fid)
        rslt['val'] = dval
        return fid, dval

    #cmd: test flag jump
    #params: p1(u16) p2(u16)
    #p1: flag idx
    #p2: cur cmd offset increment
    @cmdc(0x04, 'flow', 'if flg:{out[1]:x} jump {out[0]:0>4x}')
    def cmd_test_flg_jump(self, prms, psr, rslt):
        fidx = self._p16(prms, 0)
        rslt['condi'] = (('flg', fidx), 1)
        return self.cmd_jump(prms, psr, rslt), fidx

    #cmd: load scene
    #params: ?
    @cmdc(0x05, 'load', 'load scene {out}')
    def cmd_load_scene(self, prms, psr, rslt):
        sc = self._p16(prms, 0)
        rslt['scene'] = sc
        return sc

    #cmd: test chara stat1 jump
    #params: p1(u8) p2(u16)
    #p1: character idx
    #p2: cur cmd offset increment
    @cmdc(0x06, 'flow', 'if ch:{out[1]:x} is st1 jump {out[0]:0>4x}')
    def cmd_test_cha_st1_jump(self, prms, psr, rslt):
        cidx = prms[0]
        rslt['condi'] = (('__cur__', 'cha', cidx, 'st1'), 1)
        return self.cmd_jump(prms, psr, rslt), cidx

    #cmd: test cur chara attr101 jump
    #params: p1(u8) p2(u8) p3(u16)
    #p1: character idx
    #p2: dest value
    #p3: cur cmd offset increment
    @cmdc(0x07, 'flow', 'if cur_ch:{out[1]:x}.a101={out[2]} jump {out[0]:0>4x}')
    def cmd_test_cha_c_a101_jump(self, prms, psr, rslt):
        cidx = prms[0]
        dval = prms[1]
        rslt['condi'] = (('__cur__', 'cha', cidx, 'a101'), dval)
        return self.cmd_jump(prms, psr, rslt), cidx, dval

    #cmd: test gv1 jump
    #params: p1(u16) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc(0x08, 'flow', 'if gv1={out[1]} jump {out[0]:0>4x}')
    def cmd_test_gv1_jump(self, prms, psr, rslt):
        dval = self._p16(prms, 0)
        rslt['condi'] = (('__cur__', 'gv1'), dval)
        return self.cmd_jump(prms, psr, rslt), dval

    #cmd: test chara attr18 jump
    #params: p1(u8) p2(u8) p3(u16)
    #p1: character idx
    #p2: dest value
    #p3: cur cmd offset increment
    @cmdc(0x09, 'flow', 'if ch:{out[1]:x}.a18>={out[2]} jump {out[0]:0>4x}')
    def cmd_test_cha_a18_jump(self, prms, psr, rslt):
        cidx = prms[0]
        dval = prms[1]
        rslt['condi'] = (('__cur__', 'cha', cidx, 'a18'), dval)
        return self.cmd_jump(prms, psr, rslt), cidx, dval

    #cmd: test find chara by a4 jump
    #params: p1(u8) p2(u16)
    #p1: dest character attr 4 value
    #p2: cur cmd offset increment
    @cmdc(0x0a, 'flow', 'if ch.a4={out[1]} found jump {out[0]:0>4x}')
    def cmd_test_cha_f_a4_jump(self, prms, psr, rslt):
        dval = prms[0]
        rslt['condi'] = (('__cur__', 'cha', 'a4', dval), 1)
        return self.cmd_jump(prms, psr, rslt), dval

    #cmd: test sum cha a101 jump
    #params: p1(u8) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc(0x0b, 'flow', 'if sum(ch.a101)={out[1]} jump {out[0]:0>4x}')
    def cmd_test_sum_cha_a101_jump(self, prms, psr, rslt):
        dval = prms[0]
        rslt['condi'] = (('__cur__', 'sum', 'cha', 'a101'), dval)
        return self.cmd_jump(prms, psr, rslt), dval

    #cmd: test gv2 jump
    #params: p1(u8) p2(u16)
    #p1: dest value
    #p2: cur cmd offset increment
    @cmdc((0x0c, 0xd), 'flow', 'if gv2={out[1]} jump {out[0]:0>4x}')
    def cmd_test_gv2_jump(self, prms, psr, rslt):
        dval = prms[0]
        rslt['condi'] = (('__cur__', 'gv2'), dval)
        return self.cmd_jump(prms, psr, rslt), dval

    #cmd: test some chara1 st2 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x0e, 'flow', 'if ch:s1 is st2 jump {out:0>4x}')
    def cmd_test_cha_s1_st2_jump(self, prms, psr, rslt):
        rslt['condi'] = (('__cur__', 'cha', 's1', 'st2'), 1)
        return self.cmd_jump(prms, psr, rslt)

    #cmd: test find chara a4=0x0d and gv3=0x140 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x0f, 'flow', 'if ch.a4=0xd found and gv3=0x140 jump {out:0>4x}')
    def cmd_test_cha_f_a4_d_gv3_140_jump(self, prms, psr, rslt):
        rslt['condi'] = (('__cur__', 'cha', 'a4', 'd', 'gv3', '140'), 1)
        return self.cmd_jump(prms, psr, rslt)

    #cmd: test gcondi1 jump
    #params: p1(u16)
    #p1: cur cmd offset increment
    @cmdc(0x10, 'flow', 'if gc1 jump {out:0>4x}')
    def cmd_test_cha_gc1_jump(self, prms, psr, rslt):
        rslt['condi'] = (('__cur__', 'gc1'), 1)
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

    def _raise_rslt(self, rslt, msg):
        rslt.update({
            'type': 'error',
            'output': msg,
        })
        return rslt

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

    def exec(self, st_ofs = 0, flt = None, flt_out = ['unknown'], cb_pck = None, ctx = None, tid = None, wk = None):
        if wk is None:
            wk = set()
        if tid is None:
            tid = [0]
        elif not isinstance(tid, list):
            tid = list(tid)
        cur_ofs = st_ofs
        page_size = self.page_size
        while True:
            rslt = {
                'offset': cur_ofs,
                'tid': tuple(tid),
                'thrd': [{
                    'ctx': ctx,
                }],
            }
            if cur_ofs >= page_size:
                ro = self._hndl_rslt(
                    self._raise_rslt(rslt, f'overflow 0x{page_size:x}'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            elif cur_ofs in wk:
                ro = self._hndl_rslt(
                    self._raise_rslt(rslt, 'walked skip'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            cmd = self.get_cmd(cur_ofs)
            if cmd is None:
                ro = self._hndl_rslt(
                    self._raise_rslt(rslt, f'no valid cmd'),
                    flt, flt_out, cb_pck)
                if not ro is None:
                    yield ro
                break
            rslt['cmd'] = cmd
            rslt = cmd.exec(self, rslt)
            wk.add(cur_ofs)
            ro = self._hndl_rslt(rslt, flt, flt_out, cb_pck)
            if not ro is None:
                yield ro
            thrds = rslt['thrd']
            thlen = len(thrds)
            if thlen == 0:
                break
            for i, th in enumerate(thrds[:-1]):
                stp = th['step']
                nxt_ofs = cur_ofs + stp
                yield from self.exec(
                    nxt_ofs, flt, flt_out, cb_pck, th['ctx'],
                    [*tid, i], wk.copy())
            if thlen > 1:
                tid.append(thlen - 1)
            cur_ofs += thrds[-1]['step']

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
        return rslt['scene']

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
#     stream
# ===============

class c_steam_stats:

    def __init__(self):
        self.cur = 0
        self.det = {}
        self.ndet = {}

    def copy(self):
        r = c_steam_stats()
        r.cur = self.cur
        r.det = self.det.copy()
        r.ndet = self.ndet.copy()
        return r

    def __eq__(self, dst):
        return (
            self.cur == dst.cur and
            self.det == dst.det and
            self.ndet == dst.ndet)

    def det_eq(self, dst):
        return self.det == dst.det

    def reset_ndet(self):
        self.ndet = {}

    def step(self):
        self.cur += 1

    def _cvar(self, var):
        if var[0] == '__cur__':
            return (self.cur,) + var[1:]
        else:
            return var

    def _branch(self, var, val):
        var = self._cvar(var)
        if var in self.ndet:
            ov = self.ndet[var].copy()
            if isinstance(ov, set):
                if val in ov:
                    yield False, self
                    return
            else:
                if val == ov:
                    yield True, self
                else:
                    yield False, self
                return
        else:
            ov = set()
        ov.add(val)
        br_false = self.copy()
        br_false.ndet[var] = ov
        yield False, br_false
        br_true = self.copy()
        br_true.ndet[var] = val
        yield True, br_true

    def check(self, var, val, det = None):
        if var is None:
            yield False, self.copy()
            yield True, self.copy()
            return
        var = self._cvar(var)
        if det != False and (det == True or var in self.det):
            yield self.det.get(var, None) == val, self
        else:
            yield from self._branch(var, val)

    def setvar(self, var, val):
        var = self._cvar(var)
        assert not var in self.ndet
        if self.det.get(var, None) == val:
            return
        self.det[var] = val

class c_sp_blk:

    def __init__(self, sp):
        self.blk = []
        self.sp = sp

    def __len__(self):
        blk = self.blk
        if not blk:
            return 0
        if self.sp:
            ln = 1
            for sub in blk:
                if isinstance(sub, c_sp_blk):
                    ln *= len(sub)
        else:
            ln = 0
            for sub in blk:
                if isinstance(sub, c_sp_blk):
                    ln += len(sub)
                else:
                    ln += 1
        return ln

    def _iter_subs(self, subs):
        assert self.sp
        if not subs:
            yield []
            return
        sub = subs[0]
        tail = subs[1:]
        if isinstance(sub, c_sp_blk):
            itr = sub.__iter__()
        elif sub is None:
            itr = [[]]
        else:
            itr = [[sub]]
        for hd in itr:
            for tl in self._iter_subs(tail):
                yield [*hd, *tl]

    def __iter__(self):
        blk = self.blk
        if self.sp:
            yield from self._iter_subs(blk)
        else:
            for sub in blk:
                if isinstance(sub, c_sp_blk):
                    yield from sub
                else:
                    yield sub

    def __eq__(self, dst):
        if not isinstance(dst, c_sp_blk):
            return False
        if self.sp != dst.sp:
            return False
        ln = len(self.blk)
        if ln != len(dst.blk):
            return False
        for i in range(ln):
            ssub = self.blk[i]
            dsub = dst.blk[i]
            if ssub != dsub:
                return False
        return True

    def _copy_from_blk(self, sblk):
        for sub in sblk:
            if isinstance(sub, c_sp_blk):
                sub = sub.copy()
            self.blk.append(sub)

    def copy(self):
        r = type(self)(self.sp)
        r._copy_from_blk(self.blk)
        return r

    def merge(self, src, sp):
        dst = type(self)(sp)
        if self:
            if self.sp == sp:
                dst._copy_from_blk(self.blk)
            else:
                dst.blk.append(self.copy())
        if src:
            if src.sp == sp:
                if sp == False:
                    dst._merge_blk_ppp(src)
                else:
                    dst._copy_from_blk(src.blk)
            else:
                if sp == False:
                    dst._merge_blk_pps(src)
                else:
                    dst.blk.append(src.copy())
        return dst

    def append(self, v, sp):
        src = type(self)(sp)
        src.blk.append(v)
        return self.merge(src, sp)

    def _cmp_split(self, dblk):
        sblk = self.blk
        ln = min(len(sblk), len(dblk))
        for i in range(ln):
            if sblk[i] != dblk[i]:
                c1 = i
                break
        else:
            c1 = ln
            c2 = 0
        if c1 < ln:
            for i in range(ln):
                if sblk[-i-1] != dblk[-i-1]:
                    c2 = i
            else:
                c2 = ln
            if c1 + c2 > ln:
                c2 = ln - c1
        if c1 > 0:
            p_f = sblk[:c1]
        else:
            p_f = None
        if c2 > 0:
            p_b = sblk[-c2:]
        else:
            p_b = None
        cm = len(sblk) - c1 - c2
        if cm > 0:
            p_m_s = sblk[c1:-c2]
        else:
            p_m_s = None
        cm = len(dblk) - c1 - c2
        if cm > 0:
            p_m_d = dblk[c1:-c2]
        else:
            p_m_d = None
        return p_f, (p_m_s, p_m_d), p_b, c1, c2

    def _merge_blk_pss(self, dst):
        assert self.sp == dst.sp == True
        dblk = dst.blk
        p_f, (p_m_s, p_m_d), p_b, c1, c2 = self._cmp_split(dblk)
        if p_m_s:
            mblk_s = type(self)(self.sp)
            mblk_s._copy_from_blk(p_m_s)
        else:
            mblk_s = None
        if p_m_d:
            mblk_d = type(self)(self.sp)
            mblk_d._copy_from_blk(p_m_d)
        else:
            mblk_d = None
        if p_m_s or p_m_d:
            mblk = type(self)(not self.sp)
            mblk.blk = [mblk_s, mblk_d]
        else:
            mblk = None
        rblk = type(self)(self.sp)
        if p_f:
            rblk._copy_from_blk(p_f)
        if mblk:
            rblk.blk.append(mblk)
        if p_b:
            rblk._copy_from_blk(p_b)
        return rblk, c1, c2

    def _merge_blk_pps(self, dst, nocopy = False):
        assert self.sp == False and dst.sp == True
        cmax = (0, 0)
        maxsubrblk = None
        imax = None
        for si, sub in enumerate(self.blk):
            if not isinstance(sub, c_sp_blk):
                continue
            subrblk, c1, c2 = sub._merge_blk_pss(dst)
            if (c1+c2, c1) > cmax:
                cmax = (c1+c2, c1)
                maxsubrblk = subrblk
                imax = si
        if nocopy:
            rblk = self
        else:
            rblk = self.copy()
        if maxsubrblk:
            rblk.blk[imax] = maxsubrblk
        else:
            rblk.blk.append(dst.copy())

    def _merge_blk_ppp(self, dst, nocopy = False):
        assert self.sp == dst.sp == False
        if nocopy:
            rblk = self
        else:
            rblk = self.copy()
        for sub in dst.blk:
            rblk._merge_blk_pps(sub, True)
        return rblk

class c_branch_log:

    def __init__(self):
        self.blk = c_sp_blk(True)

    def copy(self):
        r = c_branch_log()
        r.blk = self.blk.copy()
        return r

    def __len__(self):
        return len(self.blk)

    def __iter__(self):
        yield from self.blk

    def write(self, val):
        self.blk = self.blk.append(val, True)

    def merge(self, dst):
        self.blk = self.blk.merge(dst.blk, False)

class c_ffta_battle_stream:

    def __init__(self, psr, pidx):
        self.psr = psr
        self.pidx = pidx

    @staticmethod
    def _merge_sinfo(osinfo, nsinfo):
        slen = len(osinfo)
        assert slen == len(nsinfo)
        rsinfo = []
        for si in range(slen):
            ovs = osinfo[si]
            nvs = nsinfo[si]
            if ovs is None and nvs is None:
                rvs = None
            elif ovs is None:
                rvs = nvs.copy()
            elif nvs is None:
                rvs = ovs.copy()
            elif isinstance(ovs, c_branch_log):
                assert isinstance(nvs, c_branch_log)
                rvs = ovs.copy()
                rvs.merge(nvs)
            else:
                rvs = ovs.copy()
                for nv in nvs:
                    for ov in ovs:
                        if ov == nv:
                            break
                    else:
                        rvs.append(nv)
            rsinfo.append(rvs)
        return rsinfo

    def _add_sts(self, sts, nst, *nsinfo):
        for i, (st, *sinfo) in enumerate(sts):
            if st == nst:
                sts[i] = (nst, *self._merge_sinfo(sinfo, nsinfo))
                return False
        sts.append((nst, *nsinfo))
        return True

    def _copy_sts(self, sts):
        rsts = []
        for sv in sts:
            rsts.append(tuple(None if v is None else v.copy() for v in sv))
        return rsts

    def _diff_sts(self, osts, nsts):
        dsts = []
        for nst, *nsinfo in nsts:
            nst.reset_ndet()
            for i, (ost, *osinfo) in enumerate(osts):
                if nst.det_eq(ost):
                    osts[i] = (nst, *self._merge_sinfo(osinfo, nsinfo))
                    break
            else:
                for i, (dst, *dsinfo) in enumerate(dsts):
                    if nst.det_eq(dst):
                        dsts[i] = (nst, *self._merge_sinfo(dsinfo, nsinfo))
                        break
                else:
                    dsts.append((nst, *nsinfo))
        return dsts

    @staticmethod
    def _step_sts(sts):
        for st, *_ in sts:
            st.step()

    def _exec_cmd(self, rslt):
        typ = rslt['type']
        tid = rslt['tid']
        thrds = rslt['thrd']
        ret = []
        ret_done = False
        del_ti = []
        nthrds = []
        for ti, thrd in enumerate(thrds):
            ctx = thrd['ctx']
            if typ == 'error':
                lds = ctx['lds']
                if lds:
                    lds = lds.copy()
                ret.append((tid, lds, ctx['stat']))
                del_ti.append(ti)
            elif typ == 'load':
                lds = ctx['lds']
                if lds:
                    lds = lds.copy()
                else:
                    lds = c_branch_log()
                ldsc = rslt['scene']
                lds.write(ldsc)
                ret.append((tid, lds, ctx['stat']))
                ret_done = True
                del_ti.append(ti)
            elif typ == 'stat':
                dvar = rslt['var']
                dval = rslt['val']
                st = ctx['stat']
                st.setvar(dvar, dval)
            elif typ == 'flow':
                cvar, cval = rslt.get('condi', (None, None))
                step = rslt['flow_offset']
                if cvar is None:
                    thrd['step'] = step
                    continue
                if cvar[0] == '__cur__' and cvar[1] in ['cha', 'sum']:
                    cvar = None
                    cdet = None
                else:
                    cdet = (cvar[0] == 'flg')
                st = ctx['stat']
                no_false = True
                for rcondi, nst in st.check(cvar, cval, cdet):
                    nctx = ctx.copy()
                    nctx['stat'] = nst
                    if rcondi:
                        nthrds.append({
                            'ctx': nctx,
                            'step': step,
                        })
                    else:
                        thrd['ctx'] = nctx
                        no_false = False
                if no_false:
                    del_ti.append(ti)
        for ti in reversed(del_ti):
            thrds.pop(ti)
        thrds.extend(nthrds)
        if ret:
            return ret, ret_done

    def _exec(self, sts):
        xsts = []
        for prog in self.psr.iter_program(self.pidx):
            #print('h', prog.page_idx, len(sts))
            nsts = []
            for st, tids, lds in sts:
                for rets, rdone in prog.exec(
                    cb_pck = self._exec_cmd, ctx = {
                        'stat': st,
                        'lds': lds,
                    }, tid = tids[0] if tids else None):
                    for rtid, rlds, rst in rets:
                        assert rlds or not lds
                        if rdone:
                            #print('x1', rst.det, [*rlds] if rlds else None)
                            self._add_sts(xsts, rst, [rtid], rlds)
                        else:
                            #print('n1', rst.det, [*rlds] if rlds else None)
                            self._add_sts(nsts, rst, [rtid], rlds)
            sts = nsts
            #for _, _, _ld in nsts:
            #    if _ld:
            #        print('h2', prog.page_idxs, [*_ld])
            #print('h2a', prog.page_idxs, [len(_ld) for _, _, _ld in nsts if _ld])
        for st, tids, lds in sts:
            #print('x2', st.det, lds)
            self._add_sts(xsts, st, tids, lds)
        self._step_sts(xsts)
        return xsts

    def exec(self):
        rlds = set()
        sts = [(c_steam_stats(), None, None)]
        while sts:
            osts = self._copy_sts(sts)
            nsts = self._exec(sts)
            nsts = self._diff_sts(osts, nsts)
##            print('===')
##            for st, _, ld in osts:
##                print(st.det, ld)
##            print('---')
##            for st, _, ld in nsts:
##                print(st.det, list(ld) if ld else None)
            for _, _, lds in osts:
                if not lds:
                    continue
                for ld in lds:
                    rlds.add(tuple(ld))
            sts = nsts
        return sorted(rlds)

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
        for v in srels.refer_heads:
            print(v, srels.refer[v])

    def scan_strm(bi):
        global strm_b
        strm_b = c_ffta_battle_stream(spsr_b, bi)
        lds = strm_b.exec()
        ppr(lds)

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

