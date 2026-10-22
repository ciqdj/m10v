"""Stock-specific HARMAN controls, pixel isolation and independent texture."""
import ctypes as C
import unittest
from tests.test_gr3_m10v_library import NativeFilmLibraryTests,STORE,State

class HarmanFilmTests(NativeFilmLibraryTests):
    def test_phoenix_ei120_is_atomic_persistent_and_changes_rendered_pixels(self):
        s=self.state();ok=STORE(lambda _,p:0);bad=STORE(lambda _,p:-1)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,67,ok,None),0)
        self.lib.m10v_library_texture(C.byref(s),0,0,0,ok,None)
        self.lib.m10v_library_halation(C.byref(s),0,0,3,5,2,ok,None)
        before=bytes(s)
        self.assertEqual(self.effects(s,6,1,bad),-2);self.assertEqual(bytes(s),before)
        im,y,uv,tmp=self.image();self.assertEqual(self.render(im,s,tmp),0);normal=(bytes(y),bytes(uv))
        self.assertEqual(self.effects(s,6,1),0);self.assertEqual(s.effects[0][5],1)
        im,y,uv,tmp=self.image();self.assertEqual(self.render(im,s,tmp),0)
        self.assertNotEqual((bytes(y),bytes(uv)),normal)
        self.assertEqual(bytes(y)[im.y_bytes:],bytes([173]*32))
        self.assertEqual(self.effects(s,5,0),0);self.assertEqual(s.effects[0][5],1)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,67,ok,None),0)
        self.assertEqual(s.effects[0][5],1)
        self.assertLess(self.effects(s,6,2),0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,68,ok,None),0)
        self.assertEqual(s.effects[0][5],0)

    def effects(self,s,field,value,store=None):
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        return self.lib.m10v_library_effects(C.byref(s),0,field,value,store or STORE(lambda _,p:0),None)

    def test_new_stocks_select_with_independent_defaults(self):
        for film,grain,size,gain in [(67,0,0,0),(68,0,1,0)]:
            s=self.state();ok=STORE(lambda _,p:0)
            self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,film,ok,None),0)
            self.assertEqual((s.slots[0].grain,s.effects[0][0],s.slots[0].halo_gain),(grain,size,gain))
            self.assertEqual((s.version,s.size),(4,104))

    def test_red_exposure_is_atomic_and_reset_preserves_special_exposure(self):
        s=self.state();ok=STORE(lambda _,p:0);bad=STORE(lambda _,p:-1)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,68,ok,None),0)
        before=bytes(s);self.assertEqual(self.effects(s,6,2,bad),-2);self.assertEqual(bytes(s),before)
        self.assertEqual(self.effects(s,6,2),0);self.assertEqual(s.effects[0][5],2)
        self.effects(s,1,8);self.assertEqual(self.effects(s,5,0),0)
        self.assertEqual((s.effects[0][1],s.effects[0][5]),(0,2))
        self.assertLess(self.effects(s,6,3),0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,34,ok,None),0)
        self.assertEqual(s.effects[0][5],0);self.assertLess(self.effects(s,6,1),0)

    def test_each_red_exposure_changes_color_and_does_not_enable_halo(self):
        s=self.state();ok=STORE(lambda _,p:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,68,ok,None),0)
        self.lib.m10v_library_texture(C.byref(s),0,0,0,ok,None)
        outputs=[]
        for exposure in [0,1,2]:
            self.assertEqual(self.effects(s,6,exposure),0)
            im,y,uv,tmp=self.image();self.assertEqual(self.render(im,s,tmp),0);outputs.append((bytes(y),bytes(uv)))
            self.assertEqual(bytes(y)[im.y_bytes:],bytes([173]*32))
        self.assertEqual(len(set(outputs)),3)
        self.assertLess(self.lib.m10v_library_halation(C.byref(s),0,8,3,5,2,ok,None),0)

    def test_phoenix_halo_is_spatial_and_independent_of_800t(self):
        s=self.state();ok=STORE(lambda _,p:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,67,ok,None),0)
        self.lib.m10v_library_texture(C.byref(s),0,0,0,ok,None)
        images=[]
        for gain in [0,8]:
            self.assertEqual(self.lib.m10v_library_halation(C.byref(s),0,gain,4,0,2,ok,None),0)
            im,y,uv,tmp=self.image()
            for row in range(46,51):
                for x in range(62,68):y[row*im.stride+x]=255
            self.assertEqual(self.render(im,s,tmp),0);images.append(bytes(y))
        self.assertNotEqual(*images)
        self.assertGreater(images[1][48*im.stride+58],images[0][48*im.stride+58])

if __name__=='__main__':unittest.main()
