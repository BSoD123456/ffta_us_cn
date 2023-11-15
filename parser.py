#! python3
# coding: utf-8

# ===============
#    scripts
# ===============

def cmdc(code):
    def _hndl(cls, mname, mth):
        #if not hasattr(cls, '_cmd_tab'):
        # in __dict__ is the same as js hasOwnProperty
        # but hasattr check parents
        if not '_cmd_tab' in cls.__dict__:
            cls._cmd_tab = {}
        cls._cmd_tab[code] = mth
    return clsdec(_hndl)

class c_ffta_sect_cmd(c_ffta_sect):

    _cmd_tab = {}

    def _cmd(self, code):
        if not code in self._cmd_tab:
            return None
        return self._cmd_tab[code].__get__(self, type(self))

    def exec(self, params):
        pass

class c_ffta_sect_scene_cmd(c_ffta_sect_cmd):

    #cmd: text window
    #params: p1(c) p2(c) p3(c)
    #p1: index of text on this page
    #p2: index of portrait
    #p3: flags, 80: left, 82: right
    @cmdc(0x0f)
    def cmd_text(self, params):
        pass

class c_ffta_script_parser:

    def __init__(self, sects):
        self.sects = sects

    

if __name__ == '__main__':
    pass
