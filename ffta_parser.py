#! python3
# coding: utf-8

# ===============
#     common
# ===============

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

    def exec(self, psr):
        rslt = {
            'step': 1,
            'valid': False,
            'type': 'unknown',
        }
        if self.op in self._cmd_tab:
            # self._cmd_tab[op][0].__get__(self, type(self)) to bind cmdfunc
            cmdfunc, cmdtyp = self._cmd_tab[self.op]
            rslt['valid'] = True
            rslt['type'] = cmdtyp
            rslt['output'] = cmdfunc(self, self.prms, psr, rslt)
        return rslt

    def __repr__(self):
        #prms_rpr = bytearray.hex(self.prms)
        prms_rpr = bytes.hex(self.prms)
        prms_rpr = ' '.join(prms_rpr[i:i+2] for i in range(0, len(prms_rpr), 2))
        return f'<{self.op:X}: {prms_rpr.upper()}>'

class c_ffta_scene_cmd(c_ffta_cmd):

    _CMDC_TOP = 0x72

    #cmd: text window
    #params: p1(c) p2(c) p3(c)
    #p1: index of text on this page
    #p2: index of portrait
    #p3: flags, 80: left, 82: right
    @cmdc(0x0f, 'text')
    def cmd_text(self, prms, psr, rslt):
        tidx = prms[0]
        cpidx = prms[1]
        t_line = psr.t_page[tidx]
        toks = psr.t_page[tidx].text.tokens
        return toks

class c_ffta_script_parser:

    def __init__(self, sects):
        self.sects = sects
        self.page_idx = None

    def enter_page(self, idx):
        assert(idx > 0)
        if idx == self.page_idx:
            return
        s_pi1, s_pi2, t_pi = self.sects['fat'].get_entry(idx)
        self.s_page = self.sects['script'][s_pi1, s_pi2]
        self.t_page = self.sects['text'][t_pi]
        self.cmds = []

    def _new_cmd(self, cmdtpl):
        cmdop, prms = cmdtpl
        if cmdop is None:
            return None, False
        try:
            return c_ffta_scene_cmd(cmdop, prms), True
        except ValueError:
            return None, True

    def _extend_cmd_to(self, idx):
        cmds = self.cmds
        if idx < len(cmds):
            return True
        elif cmds and cmds[-1] is None:
            # at the end of scripts
            return False
        sect_spage = self.s_page
        while True:
            lst_ci = len(cmds)
            if idx < lst_ci:
                return True
            cmd, in_sect = self._new_cmd(sect_spage.get_cmd(lst_ci))
            if not in_sect:
                break
            cmds.append(cmd)
            if cmd is None:
                return False
        sect_cmds = self.sects['cmds']
        ctx = sect_spage.extend_to(idx)
        cmdop = next(ctx)
        while not cmdop is None:
            cmdop = ctx.send(sect_cmds.get_cmd_len(cmdop))
            cmd, in_sect = self._new_cmd(sect_spage.get_last_cmd())
            assert(in_sect)
            self.cmds.append(cmd)
            if cmd is None:
                if cmdop is None:
                    break
                return False
        return True

    def get_cmd(self, idx):
        if self._extend_cmd_to(idx):
            return self.cmds[idx]
        else:
            return None

    def exec(self, st_idx = 0, flt = None, flt_out = None, cb_pck = None):
        nxt_idx = st_idx
        while not nxt_idx is None:
            cmd = self.get_cmd(nxt_idx)
            if cmd is None:
                break
            rslt = cmd.exec(self)
            lst_idx = nxt_idx
            nxt_idx += rslt['step']
            if not rslt['valid']:
                continue
            typ = rslt['type']
            if not flt is None and not typ in flt:
                continue
            if not flt_out is None and typ in flt_out:
                continue
            if callable(cb_pck):
                ro = cb_pck(lst_idx, rslt)
            else:
                ro = rslt['output']
            yield ro

if __name__ == '__main__':

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom

    def main():
        global spsr
        spsr = c_ffta_script_parser({
            'fat':      rom.tabs['s_fat'],
            'script':   rom.tabs['s_scrpt'],
            'cmds':     rom.tabs['s_cmds'],
            'text':     rom.tabs['s_text'],
        })
        spsr.enter_page(1)
        def _idx_pck(idx, rslt):
            return (idx, rslt['type'], rslt['output'])
        return spsr.exec(cb_pck = _idx_pck)
    ctx = main()
