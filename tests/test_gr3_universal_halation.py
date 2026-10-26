"""Real C renderer contracts for opt-in, per-film universal halation."""
import ctypes as C
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Slot, Image
ROOT=Path(__file__).resolve().parents[1]
class State(C.Structure):
    _fields_=[('magic',C.c_uint32),('version',C.c_uint16),('size',C.c_uint16),('sequence',C.c_uint32),('slots',Slot*10),('stamp',C.c_uint8),('format',C.c_uint8),('corner',C.c_uint8),('color',C.c_uint8),('effects',(C.c_uint8*8)*10),('reserved',C.c_uint32),('crc',C.c_uint32)]
STORE=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(State))
OK=STORE(lambda *_:0)
BAD=STORE(lambda *_:-1)
class UniversalHalationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.libs=[]
        sources=['film_5207','film_harman','film_curated','film_newstocks','film_style_filters_0','film_style_filters_1','film_d76_0','film_d76_1']
        for enabled in (0,1):
            source=Path(cls.tmp.name)/f'core{enabled}.c';out=source.with_suffix('.dylib')
            source.write_text('#include "'+str(ROOT/'native/gr3/m10v_library.c')+'"\nunsigned stages(const m10v_library_state*s,unsigned slot,unsigned done){return m10v_library_cpu_stages(s,slot,done);}\n')
            subprocess.run([shutil.which('clang'),'-O2','-Wall','-Wextra','-Werror','-dynamiclib',f'-DM10V_UNIVERSAL_HALATION={enabled}',str(source),*[str(ROOT/f'native/gr3/{s}.c') for s in sources],'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));cls.libs.append(lib)
            lib.m10v_library_init.argtypes=[C.POINTER(State)]
            lib.m10v_library_valid.argtypes=[C.POINTER(State)]
            lib.m10v_library_remove.argtypes=[C.POINTER(State),C.c_uint32,STORE,C.c_void_p]
            lib.m10v_library_select.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,STORE,C.c_void_p]
            lib.m10v_library_select_custom.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
            lib.m10v_library_halation.argtypes=[C.POINTER(State),*[C.c_uint32]*5,STORE,C.c_void_p]
            lib.m10v_library_reset.argtypes=[C.POINTER(State),C.c_uint32,STORE,C.c_void_p]
            lib.m10v_library_render_native.argtypes=[C.POINTER(Image),C.POINTER(State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
            lib.m10v_library_render_custom.argtypes=lib.m10v_library_render_native.argtypes+[C.c_void_p,C.c_char_p]
            lib.stages.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32]
    def state(self,lib,film=1,profile=4,gain=4,spread=3,threshold=5):
        s=State();lib.m10v_library_init(C.byref(s))
        for i in range(4,0,-1):self.assertEqual(lib.m10v_library_remove(C.byref(s),i,OK,None),0)
        if film==100:r=lib.m10v_library_select_custom(C.byref(s),0,film,20,OK,None)
        else:r=lib.m10v_library_select(C.byref(s),0,film,OK,None)
        self.assertEqual(r,0)
        self.assertEqual(lib.m10v_library_halation(C.byref(s),0,gain,spread,threshold,profile,OK,None),0)
        return s
    def scene(self,lib,s,w=128,h=96,done=1,workspace=True,source=True,randomize=False):
        stride=w+8;n=stride*h
        y=(C.c_uint8*(n+32))(*([50]*(n+32)));uv=(C.c_uint8*(n+32))(*([128]*(n+32)))
        if randomize:
            rng=random.Random(351);y[:n]=[rng.randrange(256) for _ in range(n)];uv[:n]=[rng.randrange(80,177) for _ in range(n)]
        if source:y[(h//2)*stride+(w//2&~1)]=y[(h//2)*stride+(w//2&~1)+1]=255
        before=(bytes(y),bytes(uv));im=Image(y,uv,n,n,w,h,stride)
        scratch=(C.c_uint32*(6*384*256//4+8))();C.memset(scratch,173,C.sizeof(scratch))
        if s.slots[0].film==100:
            lut=(C.c_uint8*(13**3*3))(*[round(v*255/12) for b in range(13) for g in range(13) for r in range(13) for v in (r,g,b)])
            result=lib.m10v_library_render_custom(C.byref(im),C.byref(s),0,None,0,scratch if workspace else None,C.sizeof(scratch)-32 if workspace else 0,done,lut,b'CUSTOM')
        else:result=lib.m10v_library_render_native(C.byref(im),C.byref(s),0,None,0,scratch if workspace else None,C.sizeof(scratch)-32 if workspace else 0,done)
        for row in range(h):
            self.assertEqual(bytes(y[row*stride+w:(row+1)*stride]),before[0][row*stride+w:(row+1)*stride])
            self.assertEqual(bytes(uv[row*stride+w:(row+1)*stride]),before[1][row*stride+w:(row+1)*stride])
        self.assertEqual(bytes(y[n:]),before[0][n:]);self.assertEqual(bytes(uv[n:]),before[1][n:])
        self.assertEqual(bytes(scratch)[-32:],bytes([173])*32)
        return result,bytes(y),bytes(uv),before,bytes(scratch)
    def test_new_modes_require_explicit_camera_choice_and_legacy_capability_ignores_them(self):
        old,new=self.libs
        for film in (33,67):
            s=self.state(new,film,profile=2,gain=8)
            self.assertFalse(new.stages(C.byref(s),0,1)&8)
            self.assertEqual(self.scene(new,s,workspace=False)[0],0)
        for mode in (4,5):
            s=self.state(new,profile=mode)
            self.assertTrue(new.stages(C.byref(s),0,1)&8)
            self.assertFalse(old.stages(C.byref(s),0,1)&8)
            self.assertEqual(self.scene(old,s,workspace=False)[0],0)
    def test_special_spill_matches_existing_renderer_byte_for_byte(self):
        old,new=self.libs
        for film in (33,67):
            for done in (0,1):
                for gain,spread,threshold in ((1,0,0),(4,3,5),(8,8,8)):
                    a=self.state(old,film,2,gain,spread,threshold);b=self.state(new,film,4,gain,spread,threshold)
                    self.assertEqual(self.scene(old,a,done=done,randomize=True)[:3],self.scene(new,b,done=done,randomize=True)[:3])
    def test_bloom_and_streak_work_on_every_film_family_and_custom_lut(self):
        lib=self.libs[1]
        for film in (1,33,66,67,68,72,100,289,290,291,298,299,305):
            for mode in (4,5):
                s=self.state(lib,film,mode);on=self.scene(lib,s,done=0)
                off=self.scene(lib,self.state(lib,film,mode,gain=0),done=0)
                self.assertEqual(on[0],0);self.assertTrue(on[1:3]!=off[1:3],(film,mode))
    def test_streak_is_horizontal_and_bloom_has_vertical_extent(self):
        lib=self.libs[1]
        for mode in (4,5):
            _,y,_,before,_=self.scene(lib,self.state(lib,profile=mode))
            pts=[(i%136,i//136) for i,(a,b) in enumerate(zip(y,before[0])) if a!=b]
            self.assertTrue(pts)
            dx=max(x for x,_ in pts)-min(x for x,_ in pts);dy=max(y for _,y in pts)-min(y for _,y in pts)
            if mode==5:self.assertGreater(dx,4*max(1,dy))
            else:self.assertGreater(dy,2)
    def test_off_no_highlights_and_completion_are_exact_noop(self):
        lib=self.libs[1]
        for mode in (4,5):
            for gain,done,source,workspace in ((0,1,True,False),(8,9,True,False),(8,1,False,True)):
                out=self.scene(lib,self.state(lib,profile=mode,gain=gain),done=done,source=source,workspace=workspace)
                self.assertEqual(out[0],0);self.assertEqual(out[1:3],out[3])
                if not workspace:self.assertEqual(out[4],bytes([173])*len(out[4]))
    def test_missing_workspace_fails_before_colour_or_pixel_mutation(self):
        lib=self.libs[1]
        for film in (1,33,67,100):
            out=self.scene(lib,self.state(lib,film),done=0,workspace=False)
            self.assertLess(out[0],0);self.assertEqual(out[1:3],out[3])
    def test_switching_from_enabled_stock_to_custom_film_clears_mode(self):
        lib=self.libs[1];s=self.state(lib,33,5,gain=7)
        self.assertEqual(lib.m10v_library_select_custom(C.byref(s),0,100,20,OK,None),0)
        self.assertLess(s.slots[0].halo_profile,4)
        self.assertFalse(lib.stages(C.byref(s),0,1)&8)
        # Editing strength alone must not opt a newly installed film in.
        self.assertEqual(lib.m10v_library_halation(C.byref(s),0,3,3,5,s.slots[0].halo_profile,OK,None),0)
        self.assertFalse(lib.stages(C.byref(s),0,1)&8)
        for next_id,next_bank in ((101,21),(100,22)):
            self.assertEqual(lib.m10v_library_halation(C.byref(s),0,7,3,5,5,OK,None),0)
            self.assertEqual(lib.m10v_library_select_custom(C.byref(s),0,next_id,next_bank,OK,None),0)
            self.assertLess(s.slots[0].halo_profile,4)

    def test_explicit_off_stays_off_when_rebuilding_without_capability(self):
        legacy,new=self.libs
        for film in (33,67):
            s=self.state(new,film,profile=6,gain=8)
            self.assertFalse(new.stages(C.byref(s),0,1)&8)
            self.assertFalse(legacy.stages(C.byref(s),0,1)&8)
            self.assertEqual(self.scene(legacy,s,workspace=False)[0],0)

    def test_settings_are_atomic_per_film_and_reset_is_off(self):
        lib=self.libs[1];s=self.state(lib,33);before=bytes(s);other=bytes(s.slots[1])
        self.assertEqual(lib.m10v_library_halation(C.byref(s),0,7,6,5,5,BAD,None),-2);self.assertEqual(bytes(s),before)
        self.assertEqual(lib.m10v_library_halation(C.byref(s),0,7,6,5,7,OK,None),-1);self.assertEqual(bytes(s),before)
        self.assertEqual(lib.m10v_library_halation(C.byref(s),0,7,6,5,5,OK,None),0);self.assertEqual(bytes(s.slots[1]),other)
        self.assertEqual(lib.m10v_library_reset(C.byref(s),0,OK,None),0);self.assertFalse(lib.stages(C.byref(s),0,1)&8)
if __name__=='__main__':unittest.main()
