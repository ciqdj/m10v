import ctypes as C,hashlib,json,random,tempfile,unittest
from pathlib import Path
from scripts.build_gr3_halation import build
from scripts.verify_gr3_halation_arm import build_call_seam,run_arm
from tests import test_gr3_halation_core as host
class ArmHalationTests(unittest.TestCase):
    fixture=host.HalationTests.fixture
    @classmethod
    def setUpClass(cls):
        host.HalationTests.setUpClass.__func__(cls);cls.armdir=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.armdir.cleanup)
        cls.manifest=build(Path(cls.armdir.name));cls.code=(Path(cls.armdir.name)/'halation-arm.bin').read_bytes()
        cls.seam=build_call_seam()
    def test_arm_matches_host_for_both_strengths_and_orders(self):
        rng=random.Random(800)
        for w,h,pad in [(2,1,0),(32,17,8),(130,63,14)]:
            for strength in (0,1,2):
                for fmt in (1,2):
                    im,y,c,s,n=self.fixture(w,h,pad,fmt)
                    for row in range(h):
                        for x in range(w):y[row*im.y_stride+x]=rng.randrange(256);c[row*im.chroma_stride+x]=rng.randrange(32,224)
                    before_y,before_c=bytes(y),bytes(c)
                    expected_status=self.fn(C.byref(im),strength,s,n)
                    actual=run_arm(self.code,self.seam,before_y,before_c,w,h,im.y_stride,im.chroma_stride,fmt,strength,n)
                    self.assertEqual(actual['status'],expected_status);self.assertEqual(actual['y'],bytes(y));self.assertEqual(actual['chroma'],bytes(c))
                    self.assertTrue(actual['calleeSaved']);self.assertTrue(actual['seamRegistersPreserved']);self.assertTrue(actual['flagsPreserved']);self.assertTrue(actual['stackRestored'])
    def test_arm_invalid_paths_match_host_and_preserve_input(self):
        for fmt,strength,short in [(3,1,False),(1,3,False),(1,1,True)]:
            im,y,c,s,n=self.fixture();before_y,before_c=bytes(y),bytes(c)
            actual=run_arm(self.code,self.seam,before_y,before_c,128,96,128,128,fmt,strength,n-1 if short else n)
            self.assertNotEqual(actual['status'],0);self.assertEqual(actual['y'],before_y);self.assertEqual(actual['chroma'],before_c)
            self.assertTrue(actual['seamRegistersPreserved']);self.assertTrue(actual['flagsPreserved'])

    def test_arm_matches_host_for_camera_controls_and_aligned_odd_grid_queue(self):
        for control in (0x80040444,0x80048440,0x80008888,0x80086862):
            im,y,c,s,n=self.fixture(514,6,2)
            y[2*im.y_stride+256]=250;before_y,before_c=bytes(y),bytes(c)
            self.assertEqual(self.fn(C.byref(im),control,s,n),0)
            actual=run_arm(self.code,self.seam,before_y,before_c,514,6,im.y_stride,im.chroma_stride,1,control,n)
            self.assertEqual(actual['status'],0);self.assertEqual(actual['y'],bytes(y));self.assertEqual(actual['chroma'],bytes(c))
            self.assertTrue(actual['flagsPreserved']);self.assertTrue(actual['stackRestored'])
    def test_arm_matches_host_for_smooth_rolled_off_lamp(self):
        import math
        im,y,c,s,n=self.fixture(64,48)
        for row in range(48):
            for x in range(64):
                y[row*64+x]=round(150+97*math.exp(-((x-32)**2+(row-24)**2)/(2*9**2)))
        before_y,before_c=bytes(y),bytes(c)
        self.assertEqual(self.fn(C.byref(im),2,s,n),0)
        self.assertGreater(max(bytes(c)[1:im.chroma_bytes:2]),130)
        actual=run_arm(self.code,self.seam,before_y,before_c,64,48,64,64,1,2,n)
        self.assertEqual(actual['status'],0)
        self.assertEqual(actual['y'],bytes(y));self.assertEqual(actual['chroma'],bytes(c))
        self.assertTrue(actual['seamRegistersPreserved']);self.assertTrue(actual['flagsPreserved'])
    def test_arm_camera_emitter_filter_matches_host_with_cable_and_point_lamp(self):
        im,y,c,s,n=self.fixture(96,72)
        for x in range(8,72):y[(8+x//2)*96+x]=250
        y[56*96+80]=255
        for x in range(16,64):y[60*96+x]=255
        control=0x80000000|3|(3<<4)|(5<<8)|(3<<16)
        before_y,before_c=bytes(y),bytes(c)
        self.assertEqual(self.fn(C.byref(im),control,s,n),0)
        self.assertEqual(c[28*96+40+1],128)
        self.assertGreater(c[56*96+82+1],128)
        self.assertGreater(c[62*96+40+1],128)
        actual=run_arm(self.code,self.seam,before_y,before_c,96,72,96,96,1,control,n)
        self.assertEqual(actual['status'],0)
        self.assertEqual(actual['y'],bytes(y));self.assertEqual(actual['chroma'],bytes(c))
        self.assertTrue(actual['calleeSaved']);self.assertTrue(actual['flagsPreserved'])
        self.assertTrue(actual['seamRegistersPreserved']);self.assertTrue(actual['stackRestored'])

    def test_manifest_code_hash_and_budget(self):
        self.assertEqual(hashlib.sha256(self.code).hexdigest(),self.manifest['codeSha256'])
        self.assertLessEqual(len(self.code),4096);self.assertFalse(self.manifest['cameraLayoutProved'])
