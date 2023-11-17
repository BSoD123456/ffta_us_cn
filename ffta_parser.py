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

def guess_tab_size(sect, ent_width):
    rdofs = lambda pos: sect.readval(pos, ent_width, False)
    cur_ent = 0
    ofs_min = INF
    ofs_max = 0
    ofs_ord = []
    ofs_sort = set()
    while cur_ent < ofs_min:
        ofs = rdofs(cur_ent)
        cur_ent += ent_width
        if ofs < ofs_min:
            ofs_min = ofs
        if ofs > ofs_max:
            ofs_max = ofs
        ofs_ord.append(ofs)
        ofs_sort.add(ofs)
    ofs_sort = sorted(ofs_sort)
    rslt = []
    for ofs in ofs_ord:
        i = ofs_sort.index(ofs)
        try:
            sz = ofs_sort[i+1] - ofs
        except:
            sz = None
        rslt.append((ofs, sz))
    return rslt, ofs_min, ofs_max

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
            'step': 1,
            'type': 'unknown',
        }
        if self.op in self._cmd_tab:
            # self._cmd_tab[op][0].__get__(self, type(self)) to bind cmdfunc
            cmdfunc, cmdtyp = self._cmd_tab[self.op]
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
    #params: p1(u8) p2(u8) p3(u8)
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
        self.page_info = self._guess_size()
        self.s_page = None

    def _guess_size(self):
        sect = self.sects['script']
        ew = sect.ENT_WIDTH
        grps, head_sz, last_grp = guess_tab_size(sect, ew)
        rslt = []
        for gidx, (grp_ofs, grp_sz) in enumerate(grps):
            assert(grp_ofs == sect.tbase_group(gidx))
            subsect = sect.get_group(gidx)
            pages, grp_head_sz, last_page = guess_tab_size(subsect, ew)
            rslt_grp = []
            for page_ofs, page_sz in pages:
                if page_sz is None:
                    if not grp_sz is None:
                        page_sz = grp_sz - page_ofs
                rslt_grp.append((grp_ofs + page_ofs, page_sz))
            rslt.append(rslt_grp)
        return rslt

    def new_program(self, pi1, pi2):
        sects = self.sects
        return c_ffta_script_program({
            'script': sects['script'][pi1, pi2],
            'cmds': sects['cmds'],
        }, None)

class c_ffta_script_program:

    def __init__(self, sects, page_size):
        self.sects = sects
        self.page_size = page_size
        self._parse_cmds_page()

    def _new_cmd(self, cmdop, prms):
        try:
            return c_ffta_scene_cmd(cmdop, prms)
        except ValueError:
            return None

    def _parse_cmds_page(self):
        sect_spage = self.sects['script']
        sect_cmds = self.sects['cmds']
        if self.page_size is None:
            max_ofs = None
        else:
            max_ofs = self.page_size - 1
        cmds_tab = {}
        all_size = 0
        for rdy, cofs, cop, cprms_or_cb in sect_spage.iter_lines_to(max_ofs):
            if rdy:
                cprms = cprms_or_cb
            else:
                clen = sect_cmds.get_cmd_len(cop)
                cprms = cprms_or_cb(clen)
            cmd = self._new_cmd(cop, cprms)
            if cmd is None:
                assert(callable(cprms_or_cb))
                cprms_or_cb(None)
            else:
                cmds_tab[cofs] = cmd
                all_size = cofs + len(cmd)
        self.cmds = cmds_tab
        if self.page_size is None:
            self.page_size = all_size
        assert(all_size == self.page_size)

    def get_cmd(self, ofs):
        return self.cmds.get(ofs, None)

    def exec(self, st_idx = 0, flt = None, flt_out = ['unknown'], cb_pck = None):
        nxt_idx = st_idx
        while not nxt_idx is None:
            cmd = self.get_cmd(nxt_idx)
            if cmd is None:
                break
            rslt = cmd.exec(self)
            lst_idx = nxt_idx
            nxt_idx += rslt['step']
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

class c_ffta_scene_script_parser(c_ffta_script_parser):

    def enter_page(self, idx):
        assert(idx > 0)
        s_pi1, s_pi2, t_pi = self.sects['fat'].get_entry(idx)
        if super().enter_page(s_pi1, s_pi2):
            self.t_page = self.sects['text'][t_pi]

if __name__ == '__main__':
    import pdb
    from hexdump import hexdump as hd
    from pprint import pprint as ppr

    from ffta_sect import main as sect_main
    sect_main()
    from ffta_sect import rom_us as rom

    def main(page_idx = 1):
        global spsr
        spsr = c_ffta_scene_script_parser({
            'fat':      rom.tabs['s_fat'],
            'script':   rom.tabs['s_scrpt'],
            'cmds':     rom.tabs['s_cmds'],
            'text':     rom.tabs['s_text'],
        })
        spsr.enter_page(page_idx)
        def _idx_pck(idx, rslt):
            return (idx, rslt['type'], rslt['output'])
        return spsr.exec(cb_pck = _idx_pck)
    #ctx = main()
    def main():
        global spsr
        spsr = c_ffta_script_parser({
            'script':   rom.tabs['b_scrpt'],
            'cmds':     rom.tabs['b_cmds'],
        })
    main()
    def list_cmds(st, ed):
        for i in range(st, ed):
            print(hex(i), spsr.get_cmd(i))
