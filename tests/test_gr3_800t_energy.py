"""Regression contract for production 800T; effects exercise the actual C renderer."""
import ctypes as C
import unittest
from tests import test_gr3_m10v_library as harness
STORE=harness.STORE

class EnergyTests(unittest.TestCase):
    setUpClass=classmethod(harness.NativeFilmLibraryTests.setUpClass.__func__)
    state=harness.NativeFilmLibraryTests.state
    image=harness.NativeFilmLibraryTests.image
    render=harness.NativeFilmLibraryTests.render

    def run_image(self, gain=4, radius=3, threshold=5, soft=0, width=256, height=192, scene=None):
        state=self.state();ok=STORE(lambda *_:0)
        self.lib.m10v_library_select(C.byref(state),0,33,ok,None)
        self.lib.m10v_library_halation(C.byref(state),0,gain,radius,threshold,2,ok,None)
        self.lib.m10v_library_texture(C.byref(state),0,0,soft,ok,None)
        im,y,c,s=self.image(width,height,padding=0)
        s=(C.c_uint8*(6*384*256+32))()
        if scene:scene(y,c,width,height)
        self.assertEqual(self.render(im,state,s),0)
        return bytes(y[:im.y_bytes]),bytes(c[:im.chroma_bytes])

    def test_cyan_scan_grade_is_visible_in_neutral_midtones_not_white_core(self):
        y,c=self.run_image(gain=0)
        self.assertGreaterEqual(c[0],132)
        self.assertLessEqual(c[1],122)
        def white(y,c,w,h):
            for i in range(w*h):y[i]=255
        y,c=self.run_image(gain=0,scene=white)
        self.assertEqual(c[:2],bytes([128,128]))

    def test_native_resolution_lamp_has_visible_broad_red_fringe(self):
        # Same coarse grid as6000x4000, efficient contiguous planes for full size.
        from unittest.mock import patch
        def image(width,height,padding=0):
            n=width*height;y=(C.c_uint8*n)();c=(C.c_uint8*n)()
            C.memset(y,64,n);C.memset(c,128,n)
            return harness.Image(y,c,n,n,width,height,width),y,c,None
        def lamp(y,c,w,h):
            for row in range(h//2-8,h//2+8):
                for x in range(w//2-8,w//2+8):y[row*w+x]=235
        with patch.object(self,'image',image):
            off=self.run_image(gain=0,width=6000,height=4000,scene=lamp)[1]
            on=self.run_image(gain=3,width=6000,height=4000,scene=lamp)[1]
        at=2000*6000+3000+8+16+1
        self.assertGreaterEqual(on[at]-off[at],3,'broad red fringe quantized away at native resolution')
        self.assertEqual(on[:2],off[:2],'dark background must not become a halo source')

    def test_five_parameter_transaction_is_atomic_on_store_failure(self):
        self.assertTrue(hasattr(self.lib,'m10v_library_detail'), 'missing atomic five-field transaction')
        fn=self.lib.m10v_library_detail
        fn.argtypes=[C.POINTER(harness.State)]+[C.c_uint32]*6+[STORE,C.c_void_p]
        state=self.state();before=bytes(state);bad=STORE(lambda *_:-1);ok=STORE(lambda *_:0)
        self.assertEqual(fn(C.byref(state),4,7,6,5,2,3,bad,None),-2)
        self.assertEqual(bytes(state),before)
        self.assertEqual(fn(C.byref(state),4,7,6,5,2,3,ok,None),0)
        v=state.slots[4]
        self.assertEqual([v.halo_gain,v.halo_spread,v.halo_threshold,v.grain,v.soft,v.halo_profile],[7,6,5,2,3,2])
        self.assertEqual(bytes(state)[12:44],before[12:44]);self.assertEqual(state.sequence,1)
        before=bytes(state)
        for args in [(5,0,0,0,0,0),(4,9,0,0,0,0),(4,0,0,0,4,0),(4,0,0,0,0,4)]:
            self.assertEqual(fn(C.byref(state),*args,ok,None),-1);self.assertEqual(bytes(state),before)

    @staticmethod
    def panel(y,c,w,h):
        for yy in range(h//3,2*h//3):
            for x in range(w//3,2*w//3):y[yy*w+x]=255

    def test_broad_light_has_halo_outside_and_neutral_white_center(self):
        off=self.run_image(gain=0,scene=self.panel)
        on=self.run_image(scene=self.panel)
        edge=(96*256+172)|1
        self.assertGreater(on[1][edge],off[1][edge], 'broad lamps must not be rejected by shape')
        center=96*256+128
        self.assertEqual(on[1][center:center+2],off[1][center:center+2])

    def test_nine_radius_positions_have_distinct_pixel_responses(self):
        responses=[self.run_image(radius=i,scene=self.panel)[1] for i in range(9)]
        self.assertEqual(len(set(responses)),9,'each native slider position must change diffusion')

    def test_weak_highlight_tail_not_expanded_into_dense_red(self):
        def scene(y,c,w,h):
            for row in range(20,h-20,8):
                for x in range(20,w-20,8):y[row*w+x]=220
        off=self.run_image(gain=0,scene=scene)
        on=self.run_image(threshold=5,scene=scene)
        self.assertLessEqual(max(b-a for a,b in zip(off[1][1::2],on[1][1::2])),1)

    def test_diffusion_cannot_create_new_halation_seeds(self):
        # Chroma halo must not depend on soft diffusion changing luminance.
        def scene(y,c,w,h):
            for row in range(90,102):
                for x in range(120,136):y[row*w+x]=244
        diffs=[]
        for soft in (0,3):
            off=self.run_image(gain=0,soft=soft,scene=scene)[1]
            on=self.run_image(soft=soft,scene=scene)[1]
            diffs.append([b-a for a,b in zip(off,on)])
        self.assertLessEqual(max(abs(a-b) for a,b in zip(*diffs)),2)

    def test_highlight_energy_survives_every_subcell_translation(self):
        totals=[]
        for offset in range(4):
            def scene(y,c,w,h):
                for row in range(92,100):
                    for x in range(500+offset,508+offset):y[row*w+x]=255
            off=self.run_image(gain=0,width=1024,height=192,scene=scene)[1]
            on=self.run_image(width=1024,height=192,scene=scene)[1]
            totals.append(sum(max(0,b-a) for a,b in zip(off[1::2],on[1::2])))
        self.assertGreater(min(totals),0)
        self.assertLess(max(totals)/min(totals),1.35)

    def test_small_hot_lamp_keeps_fine_near_fringe(self):
        def scene(y,c,w,h):y[96*w+256]=255
        off=self.run_image(gain=0,width=512,height=192,scene=scene)[1]
        on=self.run_image(gain=4,width=512,height=192,scene=scene)[1]
        self.assertGreater(max(on[i]-off[i] for i in range(95*512+252,98*512+262) if i%2),0)

    def test_threshold_reduces_energy_and_gain_increases_energy(self):
        def energy(gain,threshold):
            off=self.run_image(gain=0,scene=self.panel)[1]
            on=self.run_image(gain=gain,threshold=threshold,scene=self.panel)[1]
            return sum(max(0,b-a) for a,b in zip(off[1::2],on[1::2]))
        gates=[energy(4,t) for t in range(9)]
        gains=[energy(g,5) for g in range(9)]
        self.assertEqual(gates,sorted(gates,reverse=True));self.assertEqual(gains,sorted(gains))
        self.assertEqual(gains[0],0);self.assertGreater(gains[-1],gains[1])

    def test_halo_preserves_canaries_and_rejects_short_scratch_with_retired_soft_values(self):
        for gain,soft in [(4,0),(4,3)]:
            state=self.state();ok=STORE(lambda *_:0)
            self.lib.m10v_library_select(C.byref(state),0,33,ok,None)
            self.lib.m10v_library_halation(C.byref(state),0,gain,3,5,2,ok,None)
            self.lib.m10v_library_texture(C.byref(state),0,0,soft,ok,None)
            im,y,c,_=self.image(130,63,padding=14);n=6*130*63
            s=(C.c_uint8*(n+32))(*([91]*(n+32)));before=(bytes(y),bytes(c),bytes(s))
            self.assertEqual(self.lib.m10v_library_render(C.byref(im),C.byref(state),0,None,0,s,n-1),-1)
            self.assertEqual((bytes(y),bytes(c),bytes(s)),before)
            y[30*144+60]=255
            self.assertEqual(self.lib.m10v_library_render(C.byref(im),C.byref(state),0,None,0,s,n),0)
            self.assertEqual(bytes(s)[n:],bytes([91]*32))
            self.assertEqual(bytes(y)[im.y_bytes:],bytes([173]*32))
            self.assertEqual(bytes(c)[im.chroma_bytes:],bytes([197]*32))
            for row in range(63):
                self.assertEqual(bytes(y)[row*144+130:(row+1)*144],before[0][row*144+130:(row+1)*144])
                self.assertEqual(bytes(c)[row*144+130:(row+1)*144],before[1][row*144+130:(row+1)*144])

if __name__=='__main__':unittest.main()
