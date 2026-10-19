"""Reproducible CCD preview and host performance evidence; no camera claim."""
import ctypes as C
import json,statistics,time,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_gr3_harman_reference import sample_tetrahedral
from scripts.fit_gr3_native_film_targets import render_quantized
from tests import test_gr3_m10v_library as host

def main():
 out=ROOT/'docs/previews/ccd-classic';out.mkdir(exist_ok=True)
 web=json.loads((ROOT/'web/gr3/curated-luts.json').read_text());table=np.array(web['stocks'][3]['values']).reshape(15,15,15,3)/255
 ref=json.loads((ROOT/'native/gr3/curated-reference.json').read_text());q=ref['native_profiles_full'][3]
 base=np.array(json.loads((ROOT/'native/gr3/native-film-fit-targets.json').read_text())['base_gamma_q14'])/16384
 source=Image.open(ROOT/'web/gr3/film-street-source.png').convert('RGB');source.thumbnail((640,420))
 rgb=np.array(source)/255;shape=rgb.shape
 views=[source,Image.fromarray(np.rint(sample_tetrahedral(table,rgb.reshape(-1,3)).reshape(shape)*255).astype('uint8')),Image.fromarray(np.rint(render_quantized(q,rgb.reshape(-1,3),base).reshape(shape)*255).clip(0,255).astype('uint8'))]
 w,h=source.size;sheet=Image.new('RGB',(w*3,h+35),'#141c20');d=ImageDraw.Draw(sheet)
 for i,(view,name) in enumerate(zip(views,['Source (existing display image)','CCD Classic / CPU LUT','CCD Classic / ISP model'])):
  sheet.paste(view,(w*i,35));d.text((w*i+12,10),name,fill='white')
 sheet.save(out/'comparison.jpg',quality=94)
 host.NativeFilmLibraryTests.setUpClass();lib=host.NativeFilmLibraryTests.lib
 try:
  state=host.State();lib.m10v_library_init(C.byref(state));ok=host.STORE(lambda _,v:0)
  assert lib.m10v_library_select(C.byref(state),0,72,ok,None)==0
  width,height=6000,4000;n=width*height
  original=(bytes(range(256))*(n//256+1))[:n]
  y=(C.c_uint8*n).from_buffer_copy(original);uv=(C.c_uint8*n).from_buffer_copy(bytes([128])*n)
  im=host.Image(y,uv,n,n,width,height,width)
  lib.m10v_library_render_native.argtypes=[C.POINTER(host.Image),C.POINTER(host.State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
  timings={}
  for completed,label in [(0,'cpu_lut_fallback'),(1,'native_color_completed_residual')]:
   samples=[]
   for _ in range(5):
    C.memmove(y,original,n);C.memset(uv,128,n)
    start=time.perf_counter();assert lib.m10v_library_render_native(C.byref(im),C.byref(state),0,None,42,None,0,completed)==0
    samples.append(time.perf_counter()-start)
   timings[label]={'median_seconds':statistics.median(samples),'samples_seconds':samples}
   if completed:assert bytes(y)==original and bytes(uv)==bytes([128])*n
  evidence={'camera_tested':False,'timing_scope':'host clang -O2; 24MP YUV422; excludes capture, ISP, encode and SD writes; not device latency','width':width,'height':height,'extra_scratch_bytes':0,'timings':timings,'interpolation':ref['stocks'][3]['interpolation'],'isp_target_fit':q['holdout'],'preview_scope':'existing display image, not paired GR DIGITAL capture; ISP model is approximate'}
  (out/'verification.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))
 finally:host.NativeFilmLibraryTests.doClassCleanups()
if __name__=='__main__':main()
