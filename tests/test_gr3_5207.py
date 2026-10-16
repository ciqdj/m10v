"""5207 pixel and journal contracts; these do not simulate camera hardware."""
import ctypes as C
import unittest
from tests.test_gr3_m10v_library import NativeFilmLibraryTests, STORE, State


class Film5207Tests(NativeFilmLibraryTests):
    def test_5207_selection_resets_effects_without_touching_other_slots(self):
        s=self.state(); saved=[]
        store=STORE(lambda _,p: saved.append(bytes(p.contents)) or 0)
        self.lib.m10v_library_texture(C.byref(s),0,3,3,store,None)
        self.lib.m10v_library_halation(C.byref(s),0,8,8,0,3,store,None)
        others=bytes(s.slots)[8:]
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,66,store,None),0)
        self.assertEqual(self.lib.m10v_library_name(66),b'5207')
        self.assertEqual((s.slots[0].grain,s.slots[0].soft,s.slots[0].halo_gain),(1,0,0))
        self.assertEqual(bytes(s.slots)[8:],others)
        self.assertEqual((s.version,s.size),(3,C.sizeof(State)))

    def test_5207_leak_and_grain_are_independent_seeded_and_padding_safe(self):
        s=self.state();ok=STORE(lambda _,p:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,66,ok,None),0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        outputs=[]
        for strength in [0,8]:
            self.assertEqual(self.lib.m10v_library_effects(C.byref(s),0,1,strength,ok,None),0)
            self.lib.m10v_library_texture(C.byref(s),0,0,0,ok,None)
            image,y,uv,scratch=self.image();self.assertEqual(self.render(image,s,scratch),0)
            outputs.append((bytes(y),bytes(uv)))
            self.assertEqual(bytes(y)[image.y_bytes:],bytes([173]*32))
            for row in range(image.height):self.assertEqual(bytes(y[row*image.stride+128:(row+1)*image.stride]),bytes([173]*8))
        self.assertNotEqual(outputs[0],outputs[1])
        # Left leak reaches the left edge more strongly than the right edge.
        self.assertGreater(outputs[1][0][0]-outputs[0][0][0],outputs[1][0][127]-outputs[0][0][127])
        self.lib.m10v_library_effects(C.byref(s),0,1,0,ok,None)
        self.lib.m10v_library_texture(C.byref(s),0,3,0,ok,None)
        result=[]
        for seed in [1,1,2]:
            image,y,uv,scratch=self.image();self.assertEqual(self.render(image,s,scratch,seed=seed),0);result.append(bytes(y))
        self.assertEqual(result[0],result[1]);self.assertNotEqual(result[0],result[2])
        self.assertGreater(len(set(result[0][:128])),3)

    def test_effect_update_failure_is_atomic_and_ranges_are_checked(self):
        s=self.state();ok=STORE(lambda _,p:0);bad=STORE(lambda _,p:-1)
        self.assertEqual(self.lib.m10v_library_select(C.byref(s),0,66,ok,None),0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        before=bytes(s)
        self.assertEqual(self.lib.m10v_library_effects(C.byref(s),0,1,8,bad,None),-2)
        self.assertEqual(bytes(s),before)

        self.assertLess(self.lib.m10v_library_effects(C.byref(s),0,0,3,ok,None),0)
        self.assertEqual(bytes(s),before)

    def test_grain_uses_same_reference_coordinates_at_two_resolutions(self):
        s=self.state();ok=STORE(lambda _,p:0)
        self.lib.m10v_library_select(C.byref(s),0,66,ok,None)
        self.lib.m10v_library_texture(C.byref(s),0,3,0,ok,None)
        results=[]
        for w,h in [(64,48),(128,96)]:
            image,y,uv,scratch=self.image(w,h);self.assertEqual(self.render(image,s,scratch,seed=5207),0)
            results.append((image,bytes(y)))
        a,small=results[0];b,large=results[1]
        self.assertEqual([small[y*a.stride+x] for y in range(48) for x in range(64)],
                         [large[2*y*b.stride+2*x] for y in range(48) for x in range(64)])

    def test_common_leak_does_not_recolor_pixels_outside_its_range(self):
        ok=STORE(lambda _,p:0)
        for film in [1,40]:
            s=self.state();self.lib.m10v_library_select(C.byref(s),0,film,ok,None)
            outputs=[]
            for gain in [0,8]:
                self.lib.m10v_library_effects(C.byref(s),0,1,gain,ok,None)
                im,y,uv,tmp=self.image(16,2)
                for row in range(2):
                    for x in range(0,16,2):
                        y[row*im.stride+x]=16;y[row*im.stride+x+1]=235
                        uv[row*im.stride+x]=16;uv[row*im.stride+x+1]=240
                self.assertEqual(self.render(im,s,tmp),0);outputs.append((bytes(y),bytes(uv)))
            self.assertNotEqual(outputs[0],outputs[1])
            for channel in range(2):
                self.assertEqual(outputs[0][channel][14:16],outputs[1][channel][14:16])

    def test_common_texture_works_for_every_film_and_reset_preserves_specials(self):
        ok=STORE(lambda _,p:0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        for film in range(1,67):
            with self.subTest(film=film):
                s=self.state();self.lib.m10v_library_select(C.byref(s),0,film,ok,None)
                self.lib.m10v_library_texture(C.byref(s),0,0,0,ok,None)
                im,y,uv,tmp=self.image();self.assertEqual(self.render(im,s,tmp),0);base=(bytes(y),bytes(uv))
                self.assertEqual(self.lib.m10v_library_effects(C.byref(s),0,1,8,ok,None),0)
                im,y,uv,tmp=self.image();self.assertEqual(self.render(im,s,tmp),0)
                self.assertNotEqual(base,(bytes(y),bytes(uv)))
                halo=bytes(s.slots[0])[4:]
                self.assertEqual(self.lib.m10v_library_effects(C.byref(s),0,5,0,ok,None),0)
                self.assertEqual(s.slots[0].film,film);self.assertEqual(s.effects[0][1],0)
                self.assertEqual(bytes(s.slots[0])[4:],halo)

    def test_5207_rejects_800t_halation_controls(self):
        s=self.state();ok=STORE(lambda _,p:0)
        self.lib.m10v_library_select(C.byref(s),0,66,ok,None)
        before=bytes(s)
        self.assertLess(self.lib.m10v_library_halation(C.byref(s),0,8,8,0,3,ok,None),0)
        self.assertEqual(bytes(s),before)


if __name__=='__main__':unittest.main()
