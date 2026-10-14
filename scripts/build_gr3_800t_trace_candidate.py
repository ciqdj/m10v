"""Construct the current guarded 800T candidate with hardware tracing.

Instrumentation preserves production guards; camera validation is still required.
"""
import sys,json,hashlib,struct,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'.runtime/grlife'))
from scripts.build_gr3_800t_trace import build_trace,RETURN_STAGES
from reconstruction.firmware_store.extended_container import rebuild_extended_rtos
from reconstruction.firmware_patch import PatchSpec
from reconstruction.firmware_store.profile import inspect_official_source
s=importlib.util.spec_from_file_location('trace_base',ROOT/'node/gr3-800t-worker.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def construct(source,prepared):
 baseline,receipt,expected=m.construct_800t(source,prepared,1)
 program=bytearray.fromhex(expected['tail_hex'])
 modules=dict(build_trace());logger=modules['logger'];adapter=modules['adapter']
 struct.pack_into('<I',program,0x5008,0xeb0006fc)
 program[0x6800:0x6800+len(logger)]=logger
 program[0x6c00:0x6c00+len(adapter)]=adapter
 checked=inspect_official_source(source)
 patches=tuple(PatchSpec(offset=r['offset'],expected=bytes.fromhex(r['expected_hex']),replacement=bytes.fromhex(r['replacement_hex']),label='Reviewed trace color/base patch',provenance='800T trace') for r in expected['patches'])
 candidate,structural=rebuild_extended_rtos(source,tail_offset=expected['tail_offset'],tail=bytes(program),patches=patches,locks=checked.profile.locks)
 expected['tail_hex']=program.hex()
 sha=lambda b:hashlib.sha256(b).hexdigest()
 receipt.update(status='HARDWARE_TRACE_REQUIRED',candidate_sha256=sha(candidate),container=structural,
  trace_file='C:\\M10V8.BIN',trace_bytes=256,trace_format_version=3,trace_control_word=47,trace_stages={str(i+1):n for i,n in enumerate(RETURN_STAGES)}|{'100':'core_returned_and_freed'},
  trace_machine_code={n:{'sha256':sha(code),'bytes':len(code)} for n,code in modules.items()},
  limitations=['This candidate still requires real camera validation','Instrumentation preserves production guards and pixel behavior','Temporary unique trace file overwritten on each capture'])
 return candidate,receipt,expected
if __name__=='__main__':
 source=Path(sys.argv[1]).read_bytes();prepared=json.loads(Path(sys.argv[2]).read_text());out=Path(sys.argv[3])
 candidate,receipt,expected=construct(source,prepared);out.write_bytes(candidate)
 out.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 out.with_suffix('.expected.json').write_text(json.dumps(expected,indent=2)+'\n')
 print(json.dumps({'status':receipt['status'],'bytes':len(candidate),'sha256':receipt['candidate_sha256']}))
