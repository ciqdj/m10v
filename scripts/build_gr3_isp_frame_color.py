"""Compile the bounded frame-owned ISP parameter writer; no firmware hooks.

Activation is intentionally separate: target fidelity and per-shot backend
identity must be proved before replacing full LUT processing in a firmware.
"""
import argparse,json,os,shutil,subprocess,tempfile
from pathlib import Path
from scripts.build_gr3_m10v_library import ROOT,FLAGS,link_object

def build(out,base=0x54160000):
    compiler=os.environ.get('M10V_LLVM_CLANG') or '/opt/homebrew/opt/llvm/bin/clang'
    if not Path(compiler).is_file():compiler=shutil.which('clang')
    with tempfile.TemporaryDirectory() as directory:
        obj=Path(directory)/'isp.o'
        subprocess.run([compiler,*FLAGS,'-c',str(ROOT/'native/gr3/m10v_isp_frame_color.c'),'-o',str(obj)],check=True,capture_output=True)
        code,symbols=link_object(obj.read_bytes(),base,prefix='m10v_isp_frame_')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest={'base':base,'bytes':len(code),'symbols':symbols,'patches':[],
      'workspace_bytes':2048,'cache_mutations':False,'firmware_activated':False,
      'scope':'relative matrix + monotone curves + relative post; not arbitrary 3-D LUT or spatial effects'}
    (out/'isp-frame-color.bin').write_bytes(code)
    (out/'isp-frame-color.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return code,manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();build(a.out)
