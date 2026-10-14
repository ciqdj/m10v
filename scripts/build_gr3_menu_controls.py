"""Compile standalone, bounded dedicated 800T setting backend."""
import subprocess,tempfile
from pathlib import Path
from scripts.build_gr3_halation import ROOT,FLAGS,extract_text
MENU_ADDRESS=0x540be000

def build_menu_controls():
    with tempfile.TemporaryDirectory(prefix='m10v-menu-') as d:
        obj=Path(d)/'menu.o'
        result=subprocess.run(['clang',*FLAGS,'-fno-jump-tables','-c',str(ROOT/'native/gr3/menu_controls.c'),'-o',str(obj)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        return extract_text(obj.read_bytes(),'m10v_menu_800t')
