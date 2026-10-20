"""Phoenix orange/red spill contracts against the real saved-image renderer."""
import ctypes as C
import unittest
from tests import test_gr3_m10v_library as harness


class PhoenixHalationTests(unittest.TestCase):
    setUpClass=classmethod(harness.NativeFilmLibraryTests.setUpClass.__func__)
    state=harness.NativeFilmLibraryTests.state
    render=harness.NativeFilmLibraryTests.render

    def run_scene(self,gain=3,spread=3,threshold=5,width=256,height=192,film=67,source=True,source_light=255,scratch_bytes=6*384*256+32):
        state=self.state();ok=harness.STORE(lambda *_:0)
        self.lib.m10v_library_select(C.byref(state),0,film,ok,None)
        self.lib.m10v_library_halation(C.byref(state),0,gain,spread,threshold,2,ok,None)
        self.lib.m10v_library_texture(C.byref(state),0,0,0,ok,None)
        stride=width+8;size=stride*height
        y=(C.c_uint8*(size+32))();uv=(C.c_uint8*(size+32))()
        C.memset(y,64,len(y));C.memset(uv,128,len(uv))
        if source:
            # Two bright pixels are a whole shared-chroma pair and a sub-cell
            # source at native resolution; the emitter must survive step16.
            center=(height//2)*stride+(width//2&~1)
            y[center]=source_light;y[center+1]=source_light
        image=harness.Image(y,uv,size,size,width,height,stride)
        scratch=(C.c_uint8*scratch_bytes)();C.memset(scratch,173,len(scratch))
        self.assertEqual(self.render(image,state,scratch),0)
        self.assertEqual(bytes(scratch)[-32:],bytes([173])*32)
        self.assertEqual(bytes(y)[size:],bytes([64])*32)
        self.assertEqual(bytes(uv)[size:],bytes([128])*32)
        for row in range(height):
            self.assertEqual(bytes(y[row*stride+width:(row+1)*stride]),bytes([64])*8)
            self.assertEqual(bytes(uv[row*stride+width:(row+1)*stride]),bytes([128])*8)
        return bytes(y[:size]),bytes(uv[:size]),stride,bytes(scratch)

    def test_halo_adds_orange_red_chroma_after_film_colour(self):
        off=self.run_scene(gain=0);on=self.run_scene()
        cb=[b-a for a,b in zip(off[1][::2],on[1][::2])]
        cr=[b-a for a,b in zip(off[1][1::2],on[1][1::2])]
        self.assertLess(min(cb),0)
        self.assertGreater(max(cr),0)
        self.assertLessEqual(max(cb),0)
        self.assertGreaterEqual(min(cr),0)
        self.assertGreater(sum(cr),-sum(cb),'warm fringe should have more red than blue suppression')

    def test_native_two_pixel_lamp_retains_visible_warm_fringe(self):
        off=self.run_scene(gain=0,width=6000,height=4000)
        on=self.run_scene(gain=4,width=6000,height=4000)
        stride=on[2];row=2000
        # The halo survives integration and quantization outside the hot pair.
        cr=[on[1][yy*stride+x+1]-off[1][yy*stride+x+1]
            for yy in range(row-32,row+33) for x in range(2968,3034,2)
            if not (yy==row and x==3000)]
        self.assertGreaterEqual(max(cr),2)
        self.assertEqual(on[1][:2],off[1][:2])

    def test_zero_gain_is_exact_colour_path_and_does_not_touch_scratch(self):
        # Below the optional 64 KiB colour-cache capacity, a disabled halo
        # needs no workspace. A larger caller-owned buffer may cache colour.
        off=self.run_scene(gain=0,scratch_bytes=65532)
        self.assertEqual(off[3],bytes([173])*len(off[3]))
        cached=self.run_scene(gain=0)
        self.assertEqual(off[:2],cached[:2])
        self.assertNotEqual(cached[3][:65536],bytes([173])*65536)
        self.assertEqual(cached[3][65536:],bytes([173])*(len(cached[3])-65536))
        self.assertEqual(off[:2],self.run_scene(gain=0,spread=8,threshold=0)[:2])
        # Compare against the actual film-colour function with no halo stage,
        # rather than comparing two calls through the same disabled branch.
        width,height,stride=256,192,264;size=stride*height
        y=(C.c_uint8*size)();uv=(C.c_uint8*size)()
        C.memset(y,64,size);C.memset(uv,128,size)
        center=96*stride+128;y[center]=255;y[center+1]=255
        image=harness.Image(y,uv,size,size,width,height,stride)
        state=self.state();ok=harness.STORE(lambda *_:0)
        self.lib.m10v_library_select(C.byref(state),0,67,ok,None)
        fn=self.lib.m10v_5207_texture_q8
        fn.argtypes=[C.POINTER(harness.Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32]
        fn(C.byref(image),C.byref(state.effects[0]),0,123,2)
        self.assertEqual(off[:2],(bytes(y),bytes(uv)))

    def test_non_highlights_do_not_gain_global_tint_or_brightness(self):
        self.assertEqual(self.run_scene(gain=8,source=False)[:2],self.run_scene(gain=0,source=False)[:2])

    def test_colour_transform_cannot_create_new_highlight_sources(self):
        off=self.run_scene(gain=0,source_light=200)
        on=self.run_scene(gain=8,source_light=200)
        self.assertEqual(on[:2],off[:2])

    def test_higher_source_threshold_never_increases_the_spill(self):
        outputs=[self.run_scene(gain=4,threshold=t) for t in (0,3,5,8)]
        red=[sum(out[1][1::2]) for out in outputs]
        self.assertTrue(all(b<=a for a,b in zip(red,red[1:])))
        self.assertLess(red[-1],red[0])

    def test_hot_core_is_protected_and_gain_is_monotone(self):
        outputs=[self.run_scene(gain=g) for g in (0,1,2,4,8)]
        center=96*outputs[0][2]+128
        for out in outputs[1:]:
            self.assertEqual(out[0][center:center+2],outputs[0][0][center:center+2])
            self.assertEqual(out[1][center:center+2],outputs[0][1][center:center+2])
        for a,b in zip(outputs,outputs[1:]):
            self.assertTrue(all(y>=x for x,y in zip(a[0],b[0])))
            self.assertTrue(all(y<=x for x,y in zip(a[1][::2],b[1][::2])))
            self.assertTrue(all(y>=x for x,y in zip(a[1][1::2],b[1][1::2])))

    def test_default_spill_is_weaker_than_800t(self):
        phoenix=[self.run_scene(gain=g,film=67) for g in (0,2)]
        tungsten=[self.run_scene(gain=g,film=33) for g in (0,3)]
        warm=lambda pair:sum(max(0,b-a) for a,b in zip(pair[0][1][1::2],pair[1][1][1::2]))
        self.assertGreater(warm(phoenix),0)
        self.assertLess(warm(phoenix),warm(tungsten))


if __name__=='__main__':unittest.main()
