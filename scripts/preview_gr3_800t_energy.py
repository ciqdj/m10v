"""Software preview of the production C pipeline, never a camera ISP prediction."""
import argparse,ctypes as C,json,subprocess,tempfile,time
from pathlib import Path
import numpy as np
from PIL import Image as PIL,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
class Slot(C.Structure):
    _fields_=[('film',C.c_uint16)]+[(n,C.c_uint8) for n in ('grain','soft','halo_gain','halo_spread','halo_threshold','halo_profile')]
class State(C.Structure):
    _fields_=[('magic',C.c_uint32),('version',C.c_uint16),('size',C.c_uint16),('sequence',C.c_uint32),('slots',Slot*5)]+[(n,C.c_uint8) for n in ('stamp','format','corner','color')]+[('reserved',C.c_uint32),('crc',C.c_uint32)]
class Image(C.Structure):
    _fields_=[('y',C.POINTER(C.c_uint8)),('chroma',C.POINTER(C.c_uint8))]+[(n,C.c_uint32) for n in ('y_bytes','chroma_bytes','width','height','stride')]
STORE=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(State))
def preview(source,out,baseline='21b4247'):
    original=PIL.open(source).convert('RGB');w,h=original.size
    if w%2:original=original.crop((0,0,w-1,h));w-=1
    out.mkdir(parents=True,exist_ok=True)
    pixels=np.asarray(original.convert('YCbCr'));y=pixels[:,:,0].copy();uv=np.empty((h,w),np.uint8)
    for k in (0,1):uv[:,k::2]=((pixels[:,0::2,k+1].astype(np.uint16)+pixels[:,1::2,k+1]+1)>>1).astype(np.uint8)
    step=1
    while (w+step-1)//step>384 or (h+step-1)//step>256:step*=2
    n=(6*((w+step-1)//step)*((h+step-1)//step)+3)&~3
    ptr=lambda a:a.ctypes.data_as(C.POINTER(C.c_uint8))
    outputs={'input':original};timings={}
    with tempfile.TemporaryDirectory() as directory:
        d=Path(directory)
        (d/'old.c').write_bytes(subprocess.check_output(['git','show',baseline+':native/gr3/m10v_library.c'],cwd=ROOT))
        # Header-only renderer must come from the same baseline, not today's tree.
        old_header=subprocess.run(['git','show',baseline+':native/gr3/halation_energy.h'],cwd=ROOT,capture_output=True)
        if old_header.returncode==0:(d/'halation_energy.h').write_bytes(old_header.stdout)
        for version,code in [('old',d/'old.c'),('new',ROOT/'native/gr3/m10v_library.c')]:
            binary=d/(version+'.dylib')
            subprocess.run(['clang','-O2','-dynamiclib','-I',str(ROOT/'native/gr3'),str(code),str(ROOT/'native/gr3/halation_core.c'),'-o',str(binary)],check=True,capture_output=True)
            lib=C.CDLL(str(binary));lib.m10v_library_init.argtypes=[C.POINTER(State)]
            lib.m10v_library_halation.argtypes=[C.POINTER(State)]+[C.c_uint32]*5+[STORE,C.c_void_p]
            lib.m10v_library_render.argtypes=[C.POINTER(Image),C.POINTER(State),C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32]
            modes=[('old-observed-settings',8,8,0,3),('old-default',3,3,5,2)] if version=='old' else [('new-color-only',0,3,5,2),('new-default',3,3,5,2),('new-high',6,3,5,2)]
            for label,gain,spread,gate,profile in modes:
                state=State();lib.m10v_library_init(C.byref(state));store=STORE(lambda *_:0)
                assert lib.m10v_library_halation(C.byref(state),4,gain,spread,gate,profile,store,None)==0
                yy=y.copy();cc=uv.copy();scratch=np.zeros(n,np.uint8);im=Image(ptr(yy),ptr(cc),yy.size,cc.size,w,h,w)
                start=time.perf_counter();assert lib.m10v_library_render(C.byref(im),C.byref(state),4,None,123,ptr(scratch),n)==0
                timings[label]=time.perf_counter()-start
                ycc=np.empty((h,w,3),np.uint8);ycc[:,:,0]=yy;ycc[:,:,1]=np.repeat(cc[:,0::2],2,1);ycc[:,:,2]=np.repeat(cc[:,1::2],2,1)
                outputs[label]=PIL.frombytes('YCbCr',(w,h),ycc.tobytes()).convert('RGB');outputs[label].save(out/(label+'.png'))
    width=650;height=round(h*width/w);sheet=PIL.new('RGB',(width*3,(height+32)*2),(20,20,20));draw=ImageDraw.Draw(sheet)
    for i,(label,img) in enumerate(outputs.items()):
        x=(i%3)*width;top=(i//3)*(height+32);sheet.paste(img.resize((width,height)),(x,top+32));draw.text((x+10,top+9),label,fill='white')
    sheet.save(out/'comparison.jpg',quality=94)
    reference=np.asarray(outputs['new-color-only'],np.int16);delta=np.asarray(outputs['new-default'],np.int16)-reference
    heat=np.zeros((h,w,3),np.uint8);heat[:,:,0]=np.clip(np.maximum(delta[:,:,0]-delta[:,:,1],0)*16,0,255);PIL.fromarray(heat).save(out/'added-red-x16.png')
    (out/'simulation.json').write_text(json.dumps({'source':str(source),'baseline_commit':baseline,'dimensions':[w,h],'new_default':[3,3,5],'grain':0,'soft':0,'host_seconds':timings,'camera_tested':False,'note':'Already rendered RGB input, software YCbCr422 round trip; old-observed-settings uses prior source, not proof of uploaded ISP output.'},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('--baseline',default='21b4247');a=p.parse_args();preview(a.source,a.out,a.baseline)
