"""Host ABI tests. CBCR/CRCB here are explicit test formats, not camera evidence."""
import ctypes as C
import shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Image(C.Structure):
    _fields_=[('y',C.POINTER(C.c_uint8)),('chroma',C.POINTER(C.c_uint8))]+[(n,C.c_uint32) for n in ('y_bytes','chroma_bytes','width','height','y_stride','chroma_stride','format')]
class HalationTests(unittest.TestCase):
    @staticmethod
    def controls(gain=4,radius=4,threshold=4,grain=0,profile=4):
        return 0x80000000|gain|(radius<<4)|(threshold<<8)|(grain<<12)|(profile<<16)
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.folder.cleanup)
        out=Path(cls.folder.name)/'core.dylib'
        subprocess.run([shutil.which('clang') or 'clang','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'native/gr3/halation_core.c'),'-o',str(out)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(out));cls.fn=cls.lib.m10v_halation
        cls.fn.argtypes=[C.POINTER(Image),C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32];cls.fn.restype=C.c_int
    def fixture(self,width=128,height=96,padding=0,fmt=1):
        stride=width+padding;n=stride*height
        y=(C.c_uint8*(n+64))();c=(C.c_uint8*(n+64))()
        C.memset(y,24,n);C.memset(C.addressof(y)+n,173,64)
        C.memset(c,128,n);C.memset(C.addressof(c)+n,197,64)
        im=Image(y,c,n,n,width,height,stride,stride,fmt)
        step=1
        while (width+step-1)//step>384 or (height+step-1)//step>256:step*=2
        size=(6*((width+step-1)//step)*((height+step-1)//step)+3)&~3;scratch=(C.c_uint8*(size+64))(*([91]*(size+64)))
        return im,y,c,scratch,size
    def test_point_source_red_halo_and_core_protection(self):
        im,y,c,s,n=self.fixture();at=48*im.y_stride+64;y[at]=255
        self.assertEqual(self.fn(C.byref(im),1,s,n),0)
        neighbor=48*im.y_stride+66
        self.assertGreater(y[neighbor],24);self.assertLess(c[neighbor],128);self.assertGreater(c[neighbor+1],128)
        self.assertEqual(y[at],255);self.assertEqual(bytes(c[at:at+2]),b'\x80\x80')
        self.assertEqual(bytes(y)[im.y_bytes:],bytes([173]*64));self.assertEqual(bytes(c)[im.chroma_bytes:],bytes([197]*64))
        self.assertEqual(bytes(s)[n:],bytes([91]*64))

    def test_bright_sky_does_not_tint_roof_boundary(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(128):
            for x in range(512):y[row*512+x]=245
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        self.assertEqual(bytes(c),bytes([128])*im.chroma_bytes+bytes([197])*64)

    def test_green_foliage_highlights_are_not_white_lamp_sources(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(384):
            for x in range(1,512,2):c[row*512+x]=88
        for row in range(160,224,8):
            for x in range(220,300,8):y[row*512+x]=250
        before=bytes(c)
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        self.assertEqual(bytes(c),before)

    def test_camera_controls_gain_zero_disables_halo_without_disabling_grain(self):
        im,y,c,s,n=self.fixture();y[48*128+64]=255
        before=(bytes(y),bytes(c))
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=0),s,n),0)
        self.assertEqual((bytes(y),bytes(c)),before)
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=0,grain=4),s,n),0)
        self.assertNotEqual(bytes(y),before[0]);self.assertEqual(bytes(c),before[1])

    def test_camera_gain_threshold_and_radius_change_real_pixels(self):
        energies=[];radii=[]
        for gain in (2,6):
            im,y,c,s,n=self.fixture();y[48*128+64]=255
            self.assertEqual(self.fn(C.byref(im),self.controls(gain=gain),s,n),0)
            energies.append(sum(v-128 for v in bytes(c)[1:im.chroma_bytes:2]))
        self.assertGreater(energies[1],energies[0])
        for radius in (0,8):
            im,y,c,s,n=self.fixture();y[48*128+64]=255
            self.assertEqual(self.fn(C.byref(im),self.controls(gain=6,radius=radius),s,n),0)
            active=[x for x in range(0,128,2) if c[48*128+x+1]>128]
            self.assertTrue(active);radii.append(max(active)-min(active))
        self.assertGreater(radii[1],radii[0])
        outputs=[]
        for threshold in (0,8):
            im,y,c,s,n=self.fixture();y[48*128+64]=235
            self.assertEqual(self.fn(C.byref(im),self.controls(threshold=threshold),s,n),0)
            outputs.append(bytes(c))
        self.assertNotEqual(outputs[0],outputs[1])
        self.assertEqual(outputs[1],bytes([128])*im.chroma_bytes+bytes([197])*64)

    def test_grain_preserves_chroma_padding_and_white_black_endpoints(self):
        im,y,c,s,n=self.fixture(130,63,14)
        y[0]=0;y[2]=255;before_y=bytes(y);before_c=bytes(c)
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=0,grain=8),s,n),0)
        self.assertEqual(bytes(c),before_c);self.assertEqual(y[0],0);self.assertEqual(y[2],255)
        differences=[]
        for row in range(63):
            for x in range(130):differences.append(y[row*144+x]-before_y[row*144+x])
            self.assertEqual(bytes(y[row*144+130:row*144+144]),before_y[row*144+130:row*144+144])
        self.assertGreater(max(differences),0);self.assertLess(min(differences),0)
        self.assertLess(abs(sum(differences)/len(differences)),0.5)
    def test_strong_is_stronger_and_order_is_explicit(self):
        results=[]
        for strength,fmt in [(1,1),(2,1),(2,2)]:
            im,y,c,s,n=self.fixture(fmt=fmt);y[48*128+64]=255
            self.assertEqual(self.fn(C.byref(im),strength,s,n),0);results.append((bytes(y),bytes(c)))
        at=48*128+66
        self.assertGreater(results[1][1][at+1],results[0][1][at+1])
        self.assertEqual(results[1][0],results[2][0])
        self.assertEqual(results[1][1][0::2],results[2][1][1::2])
        self.assertEqual(results[1][1][1::2],results[2][1][0::2])
    def test_strong_preserves_diffuse_white_interior_without_large_spill(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(100,280):
            for x in range(100,412):y[row*512+x]=235
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        # At a flat panel far from its edges there is no concentrated emitter.
        # Even just outside, broad diffuse area must not max-pool as a full lamp.
        self.assertLessEqual(c[180*512+98+1]-128,10)

    def test_strong_visible_orange_fringe_on_midtone_background(self):
        im,y,c,s,n=self.fixture(128,96)
        C.memset(y,150,im.y_bytes)
        for row in range(45,51):
            for x in range(60,68):y[row*128+x]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        at=48*128+68;red=c[at+1]-128
        self.assertGreaterEqual(red,35)
        # Orange-red scattered light should lift luminance along with Cr.
        self.assertGreaterEqual(y[at]-150,red//2)
        self.assertEqual(y[48*128+64],255)

    def test_strong_smooth_rolled_off_lamp_spills_into_bright_shoulder(self):
        # A broad lamp after JPEG highlight rolloff: no adjacent 16/64-level
        # contrast, and its brightest value is 247 rather than clipped 255.
        # Rejecting all smooth emitters loses the user's ceiling-light halo.
        import math
        im,y,c,s,n=self.fixture(512,384)
        for row in range(384):
            for x in range(512):
                radius2=(x-256)**2+(row-192)**2
                y[row*512+x]=round(150+97*math.exp(-radius2/(2*60**2)))
        before=bytes(y)
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        rim=[c[i+1]-128 for i in range(0,im.y_bytes,2) if 216<=before[i]<=235]
        self.assertGreaterEqual(max(rim),3)
        # Require a surrounding fringe on all sides of the light, rather
        # than only a few noise-triggered colored pixels at its center.
        for row,x in ((192,224),(192,288),(160,256),(224,256)):
            self.assertGreaterEqual(c[row*512+x+1]-128,2)

    def test_strong_white_center_stays_neutral_on_broad_lamp(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(128,256):
            for x in range(192,320):y[row*512+x]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        at=192*512+256
        self.assertEqual(y[at],255)
        self.assertEqual(bytes(c[at:at+2]),b'\x80\x80')
        self.assertGreater(c[192*512+320+1],128)

    def test_natural_halo_retains_point_light_without_excessive_energy(self):
        im,y,c,s,n=self.fixture(512,384)
        y[192*512+256]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        red=[v-128 for v in bytes(c)[1:im.chroma_bytes:2]]
        # Bound the energy while retaining a visible point-light fringe.
        # The previous hardware-tested strong setting was excessively red.
        self.assertGreater(sum(red),400);self.assertLess(sum(red),1500)
        self.assertGreaterEqual(sum(v>0 for v in red),80)
        self.assertEqual(y[192*512+256],255)
        self.assertEqual(c[192*512+257],128)

    def test_camera_natural_rejects_reflective_cable_and_keeps_lamp(self):
        im,y,c,s,n=self.fixture(512,384)
        # A bright thin cable is not a compact lamp, even on a black sky.
        for x in range(40,320):y[80*512+x]=247
        y[220*512+400]=255
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        cable=[c[row*512+x+1]-128 for row in range(72,89) for x in range(80,280,2)]
        self.assertLessEqual(max(cable),1)
        self.assertGreater(c[220*512+402+1],128)
        self.assertEqual(c[220*512+400+1],128)

    def test_camera_default_keeps_hot_narrow_light_strips(self):
        for vertical in (False,True):
            for offset in (0,1):
                im,y,c,s,n=self.fixture(512,384)
                for position in range(80,300):
                    for thickness in (0,1):
                        x,row=(256+offset+thickness,position) if vertical else (position,192+offset+thickness)
                        y[row*512+x]=255
                self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
                x,row=(260+offset,180) if vertical else (180,196+offset)
                self.assertGreaterEqual(c[row*512+(x&~1)+1]-128,8)

    def test_camera_natural_rejects_diagonal_cable_interior(self):
        im,y,c,s,n=self.fixture(512,384)
        for x in range(48,320):y[(40+x//2)*512+x]=250
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        values=[c[(40+x//2+dy)*512+x+1]-128 for x in range(100,260,2) for dy in range(-6,7)]
        self.assertLessEqual(max(values),1)

    def test_camera_natural_rejects_broad_bright_deck(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(180,192):
            for x in range(40,472):y[row*512+x]=253
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        values=[c[row*512+x+1]-128 for row in range(174,199) for x in range(100,400,2)]
        self.assertLessEqual(max(values),1)

    def test_camera_default_saturated_broad_sources_stay_neutral(self):
        for bounds in ((40,472,180,192),(40,472,100,300),(0,512,0,200)):
            im,y,c,s,n=self.fixture(512,384)
            left,right,top,bottom=bounds
            for row in range(top,bottom):
                for x in range(left,right):y[row*512+x]=255
            before=bytes(c)
            self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
            self.assertEqual(bytes(c),before)

    def test_camera_natural_rejects_cable_endpoints(self):
        im,y,c,s,n=self.fixture(512,384)
        for x in range(40,320):y[80*512+x]=247
        before=bytes(c)
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        self.assertEqual(bytes(c),before)

    def test_camera_natural_rejects_large_bright_wall_corners(self):
        im,y,c,s,n=self.fixture(512,384)
        for row in range(100,300):
            for x in range(40,472):y[row*512+x]=253
        before=bytes(c)
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        self.assertEqual(bytes(c),before)

    def test_camera_natural_keeps_lamp_cropped_at_image_corner(self):
        im,y,c,s,n=self.fixture(512,384);y[0]=255
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        self.assertGreater(c[5],128);self.assertEqual(c[1],128)

    def test_camera_default_ignores_small_reflection_without_hot_core(self):
        im,y,c,s,n=self.fixture();y[48*128+64]=242
        before=bytes(c)
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        self.assertEqual(bytes(c),before)

    def test_camera_default_lamp_has_visible_near_red_without_far_wash(self):
        im,y,c,s,n=self.fixture(512,384);y[192*512+256]=255
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        self.assertGreaterEqual(c[192*512+258+1]-128,8)
        self.assertLessEqual(c[192*512+270+1]-128,1)
        self.assertEqual(c[192*512+256+1],128)

    def test_camera_natural_point_halo_fades_without_large_far_tail(self):
        im,y,c,s,n=self.fixture(512,384);y[192*512+256]=255
        self.assertEqual(self.fn(C.byref(im),self.controls(gain=3,radius=3,threshold=5,profile=3),s,n),0)
        near=c[192*512+258+1]-128
        far=c[192*512+270+1]-128
        self.assertGreaterEqual(near,2);self.assertLessEqual(far,1)

    def test_dark_uniform_white_and_off_remain_unchanged(self):
        for value,strength in [(24,1),(255,2),(24,0)]:
            im,y,c,s,n=self.fixture()
            for i in range(im.y_bytes):y[i]=value
            if strength==0:y[48*128+64]=255
            before=(bytes(y),bytes(c));self.assertEqual(self.fn(C.byref(im),strength,s,n),0)
            self.assertEqual((bytes(y),bytes(c)),before)
    def test_padding_and_edges(self):
        im,y,c,s,n=self.fixture(width=130,height=63,padding=14);y[0]=255;y[62*144+128]=255
        before_y=bytes(y);before_c=bytes(c)
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        for row in range(63):
            self.assertEqual(bytes(y[row*144+130:row*144+144]),before_y[row*144+130:row*144+144])
            self.assertEqual(bytes(c[row*144+130:row*144+144]),before_c[row*144+130:row*144+144])
    def test_invalid_and_short_scratch_do_not_write_anything(self):
        for field,value in [('format',3),('width',129),('y_stride',127),('chroma_stride',129),('height',0),('width',2**32-2),('y_bytes',1),('chroma_bytes',1),('width',6146)]:
            im,y,c,s,n=self.fixture();setattr(im,field,value);before=(bytes(y),bytes(c),bytes(s))
            self.assertNotEqual(self.fn(C.byref(im),1,s,n),0);self.assertEqual((bytes(y),bytes(c),bytes(s)),before)
        im,y,c,s,n=self.fixture();before=(bytes(y),bytes(c),bytes(s))
        self.assertNotEqual(self.fn(C.byref(im),1,s,n-1),0);self.assertEqual((bytes(y),bytes(c),bytes(s)),before)
        self.assertNotEqual(self.fn(C.byref(im),3,s,n),0)
    def test_aliases_and_null_are_rejected_without_writes(self):
        im,y,c,s,n=self.fixture();before=bytes(y);im.chroma=im.y
        self.assertNotEqual(self.fn(C.byref(im),1,s,n),0);self.assertEqual(bytes(y),before)
        im,y,c,s,n=self.fixture();before=(bytes(y),bytes(c))
        self.assertNotEqual(self.fn(C.byref(im),1,im.y,n),0);self.assertEqual((bytes(y),bytes(c)),before)
        self.assertNotEqual(self.fn(None,1,s,n),0)

    def test_unaligned_scratch_is_rejected_without_pixel_or_scratch_writes(self):
        im,y,c,s,n=self.fixture(32,17);y[8*32+16]=255
        before=(bytes(y),bytes(c),bytes(s))
        unaligned=C.cast(C.byref(s,1),C.POINTER(C.c_uint8))
        self.assertNotEqual(self.fn(C.byref(im),2,unaligned,n),0)
        self.assertEqual((bytes(y),bytes(c),bytes(s)),before)
    def test_minimum_even_image_and_horizontal_light(self):
        im,y,c,s,n=self.fixture(2,1);self.assertEqual(self.fn(C.byref(im),1,s,n),0)
        im,y,c,s,n=self.fixture()
        for x in range(16,112):y[48*128+x]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        self.assertGreater(c[46*128+64+1],128);self.assertEqual(y[48*128+64],255)

    def test_halo_has_no_coarse_grid_seams(self):
        im,y,c,s,n=self.fixture(6144,96);y[48*6144+3072]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        values=[c[32*6144+x+1] for x in range(3020,3130,2)]
        # Higher amplitude permits a two-level uint8 rounding step; the
        # interpolated profile still must not develop coarse cell jumps.
        self.assertLessEqual(max(abs(a-b) for a,b in zip(values,values[1:])),2)
    def test_scratch_cannot_alias_last_row_padding(self):
        im,y,c,s,n=self.fixture(2,1,14);before=(bytes(y),bytes(c))
        alias=C.cast(C.byref(y,2),C.POINTER(C.c_uint8))
        self.assertNotEqual(self.fn(C.byref(im),1,alias,n),0)
        self.assertEqual((bytes(y),bytes(c)),before)
    def test_relative_radius_scales_between_resolutions(self):
        radii=[]
        for width,height in [(512,384),(1024,768)]:
            im,y,c,s,n=self.fixture(width,height);center=width//2;row=height//2
            for yy in range(row,row+width//512):
                for xx in range(center,center+width//512):y[yy*width+xx]=255
            self.assertEqual(self.fn(C.byref(im),2,s,n),0)
            active=[x for x in range(0,width,2) if c[row*width+x+1]>128]
            self.assertTrue(active)
            radii.append((max(active)-min(active))/width)
        self.assertLess(abs(radii[0]-radii[1]),0.01)

    def test_maximum_dimensions_execute_with_bounded_scratch(self):
        im,y,c,s,n=self.fixture(6144,4096)
        self.assertLessEqual(n,589824)
        center=2048*6144+3072;y[center]=255
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        self.assertGreater(c[center+32+1],128)
        self.assertEqual(y[center],255)
        self.assertEqual(bytes(y)[im.y_bytes:],bytes([173]*64))
        self.assertEqual(bytes(c)[im.chroma_bytes:],bytes([197]*64))
        self.assertEqual(bytes(s)[n:],bytes([91]*64))
