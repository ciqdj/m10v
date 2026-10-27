"""Host proofs for the bounded post-ISP anime spatial pass (full-height Y/CbCr)."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Image(C.Structure):
    _fields_ = [("y", C.c_void_p), ("chroma", C.c_void_p)] + [(n, C.c_uint32) for n in ("y_bytes", "chroma_bytes", "width", "height", "stride")]

class AnimeSpatial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        source = Path(cls.tmp.name) / "wrapper.c"
        source.write_text('#include "native/gr3/m10v_anime.h"\nuint32_t workspace(uint32_t w,uint32_t m){return m10v_anime_workspace(w,m);}\nint render(m10v_library_image *i,uint32_t m,void*s,uint32_t n){return m10v_anime_render(i,m,s,n);}\nint render420(m10v_library_image *i,uint32_t m,void*s,uint32_t n){return m10v_anime_render420(i,m,s,n);}\n')
        lib = Path(cls.tmp.name) / "anime.so"
        subprocess.run(["clang", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", str(ROOT), str(source), "-o", str(lib)], check=True)
        cls.lib = C.CDLL(str(lib))
        cls.lib.render.argtypes = [C.c_void_p, C.c_uint32, C.c_void_p, C.c_uint32]
        cls.lib.render420.argtypes = cls.lib.render.argtypes
        cls.lib.workspace.argtypes = [C.c_uint32, C.c_uint32]
        cls.lib.workspace.restype = C.c_uint32

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def frame(self, w=10, h=5, stride=14):
        size = stride*h
        y = (C.c_ubyte*(size+32))(*([213]*(size+32)))
        c = (C.c_ubyte*(size+32))(*([219]*(size+32)))
        for r in range(h):
            for x in range(w):
                y[16+r*stride+x] = 45+x*13+(r%2)*7
                c[16+r*stride+x] = 111+x*3+(r%2)*5
        return Image(C.addressof(y)+16,C.addressof(c)+16,size,size,w,h,stride), y,c

    def run_mode(self, mode, w=10, h=5, stride=14):
        im,y,c = self.frame(w,h,stride)
        before = bytes(y),bytes(c)
        n=self.lib.workspace(w,mode)
        scratch=(C.c_ubyte*(n+32))(*([199]*(n+32)))
        self.assertEqual(self.lib.render(C.byref(im), mode,C.addressof(scratch)+16,n),0)
        self.assertEqual(bytes(scratch)[:16],bytes([199])*16)
        self.assertEqual(bytes(scratch)[16+n:],bytes([199])*16)
        for out,old in zip((y,c),before):
            self.assertEqual(bytes(out)[:16],old[:16])
            self.assertEqual(bytes(out)[16+stride*h:],old[16+stride*h:])
            for r in range(h):
                self.assertEqual(bytes(out)[16+r*stride+w:16+(r+1)*stride],old[16+r*stride+w:16+(r+1)*stride])
        return bytes(y),bytes(c)

    def test_freestanding_arm_has_no_runtime_helpers(self):
        source=Path(self.tmp.name)/"wrapper.c"
        assembly=Path(self.tmp.name)/"arm.s"
        subprocess.run(["clang","-target","armv7-none-eabi","-mcpu=cortex-a9","-marm",
                        "-ffreestanding","-fno-builtin","-O2","-I",str(ROOT),
                        "-S",str(source),"-o",str(assembly)],check=True)
        text=assembly.read_text()
        for symbol in ("__aeabi", "memcpy", "memset", "malloc", "free"):
            self.assertNotIn(symbol,text)

    def test_420_off_and_rejection_atomicity(self):
        self.assertEqual(self.lib.render420(1,0,1,0xffffffff),0)
        self.assertEqual(self.lib.render420(None,0,None,0),0)
        for case in ("oddheight","shortchroma","alias","shortscratch"):
            im,y,c=self.frame(10,6,14)
            im.chroma_bytes=42
            if case=="oddheight": im.height=5
            if case=="shortchroma": im.chroma_bytes=41
            if case=="alias": im.chroma=im.y+14
            s=(C.c_ubyte*60)()
            before=bytes(y),bytes(c),bytes(s)
            self.assertEqual(self.lib.render420(C.byref(im),3,s,59 if case=="shortscratch" else 60),-1)
            self.assertEqual((bytes(y),bytes(c),bytes(s)),before)

    def test_420_true_spatial_reference_and_guards(self):
        def quant(v,bits): return min(255,((v+(1<<(bits-1)))>>bits)<<bits)
        def smooth(v,*neighbors):
            return (4*v+sum(n if abs(n-v)<=24 else v for n in neighbors)+4)>>3
        for mode in (1,2,3):
            w,h,stride=10,8,14
            im,y,c=self.frame(w,h,stride)
            im.chroma_bytes=stride*(h//2)
            # Both horizontal and vertical boundaries, plus small local variation.
            for row in range(h):
                for x in range(w):
                    y[16+row*stride+x]=(50 if x<5 else 165)+(15 if row<4 else 50)+(row+x)%7
            for row in range(h//2):
                for x in range(w): c[16+row*stride+x]=82+row*12+(x//2)*9+(x%2)*45
            originals=(bytes(y),bytes(c)); expected=[bytearray(v) for v in originals]
            for plane,rows in enumerate((h,h//2)):
                original=originals[plane]
                for row in range(rows):
                    for x in range(w):
                        at=16+row*stride+x
                        step=2 if plane else 1
                        left=at-step if x>=step else at
                        right=at+step if x+step<w else at
                        up=16+max(0,row-1)*stride+x
                        down=16+min(rows-1,row+1)*stride+x
                        edge=abs(original[left]-original[right])+abs(original[up]-original[down])
                        if mode==1 and not plane:
                            expected[plane][at]=(original[at]*(256-min(96,max(0,edge-24)>>1)))>>8
                        if mode==2: expected[plane][at]=quant(original[at],5)
                        if mode==3:
                            value=quant(smooth(original[at],original[left],original[right],original[up],original[down]),4)
                            expected[plane][at]=value if plane else (value*(256-min(24,max(0,edge-20)>>3)))>>8
            n=self.lib.workspace(w,mode)
            scratch=(C.c_ubyte*(n+32))(*([199]*(n+32)))
            self.assertEqual(self.lib.render420(C.byref(im),mode,C.addressof(scratch)+16,n),0)
            self.assertEqual(bytes(y),bytes(expected[0]))
            self.assertEqual(bytes(c),bytes(expected[1]))
            self.assertEqual(bytes(scratch)[:16],bytes([199])*16)
            self.assertEqual(bytes(scratch)[16+n:],bytes([199])*16)

    def test_off_poison_no_access(self):
        self.assertEqual(self.lib.render(1,0,1,0xffffffff),0)
        self.assertEqual(self.lib.render(None,0,None,0),0)
        self.assertEqual(self.lib.workspace(0xffffffff,0),0)

    def test_workspace_bound(self):
        for w in (2,8,1920,6000,6144):
            for m in (1,2,3):
                self.assertLessEqual(self.lib.workspace(w,m),8*w+64)
        for w in (0,1,3,6146,0xffffffff):
            self.assertEqual(self.lib.workspace(w,1),0)
        self.assertEqual(self.lib.workspace(10,4),0)

    def test_modes_distinct_deterministic_and_guards(self):
        results=[self.run_mode(m) for m in (1,2,3)]
        self.assertEqual(len(set(results)),3)
        for m,result in enumerate(results,1):
            self.assertEqual(result,self.run_mode(m))

    def test_tiny_valid(self):
        for m in (1,2,3):
            self.run_mode(m,2,1,4)
            self.run_mode(m,2,2,2)

    def test_reject_before_writes(self):
        for case in ('mode','short','null','odd','zeroheight','shortplane','planes','scratch_y','scratch_chroma','scratch_struct','plane_struct','wrap'):
            im,y,c=self.frame()
            n=self.lib.workspace(im.width,3)
            s=(C.c_ubyte*n)()
            ptr=C.addressof(s); mode=3; count=n
            if case=='mode': mode=4
            if case=='short': count=n-1
            if case=='null': ptr=0
            if case=='odd': im.width=9
            if case=='zeroheight': im.height=0
            if case=='shortplane': im.chroma_bytes-=1
            if case=='planes': im.chroma=im.y+2
            if case=='scratch_y': ptr=im.y
            if case=='scratch_chroma': ptr=im.chroma
            if case=='scratch_struct': ptr=C.addressof(im)
            if case=='plane_struct': im.y=C.addressof(im)
            if case=='wrap': im.y=C.c_void_p(-16).value
            before=bytes(y),bytes(c),bytes(im),bytes(s)
            self.assertEqual(self.lib.render(C.byref(im),mode,ptr,count),-1,case)
            self.assertEqual((bytes(y),bytes(c),bytes(im),bytes(s)),before,case)

    def test_ink_flat_and_edge(self):
        im,y,c=self.frame(6,3,8)
        for r in range(3):
            for x in range(6): y[16+r*8+x]=60 if x<3 else 200
        oldc=bytes(c); s=(C.c_ubyte*self.lib.workspace(6,1))()
        self.assertEqual(self.lib.render(C.byref(im),1,s,len(s)),0)
        self.assertEqual(y[16],60)
        self.assertEqual(y[16+5],200)
        self.assertLess(y[16+2],60)
        self.assertLess(y[16+3],200)
        self.assertEqual(bytes(c),oldc)

    def test_poster_quantizes_both_full_height_planes(self):
        im,y,c=self.frame(); oldy=bytes(y); oldc=bytes(c)
        s=(C.c_ubyte*self.lib.workspace(10,2))()
        self.assertEqual(self.lib.render(C.byref(im),2,s,len(s)),0)
        for r in range(5):
            for x in range(10):
                at=16+r*14+x
                for out,old in ((y,oldy),(c,oldc)):
                    self.assertEqual(out[at],min(255,((old[at]+16)>>5)<<5))

    def test_matches_original_frame_reference(self):
        def delta(a,b): return abs(a-b)
        def quant(a,bits): return min(255,((a+(1<<(bits-1)))>>bits)<<bits)
        def smooth(center,*neighbors):
            return (4*center+sum(v if abs(v-center)<=24 else center for v in neighbors)+4)>>3
        for mode in (1,3):
            im,y,c=self.frame(12,9,16)
            # Nonperiodic rows expose accidental reads of already edited rows.
            for row in range(9):
                for x in range(12):
                    y[16+row*16+x]=(row*17+x*x*3+49)%256
                    c[16+row*16+x]=(row*11+x*13+87)%256
            oy,oc=bytes(y),bytes(c)
            expected_y,expected_c=bytearray(oy),bytearray(oc)
            for row in range(9):
                for x in range(12):
                    at=16+row*16+x
                    left=16+row*16+max(0,x-1)
                    right=16+row*16+min(11,x+1)
                    up=16+max(0,row-1)*16+x
                    down=16+min(8,row+1)*16+x
                    edge=delta(oy[left],oy[right])+delta(oy[up],oy[down])
                    if mode==1:
                        ink=min(96,max(0,edge-24)>>1)
                        expected_y[at]=(oy[at]*(256-ink))>>8
                    else:
                        value=quant(smooth(oy[at],oy[left],oy[right],oy[up],oy[down]),4)
                        contour=min(24,max(0,edge-20)>>3)
                        expected_y[at]=(value*(256-contour))>>8
                        cl=at-2 if x>=2 else at
                        cr=at+2 if x+2<12 else at
                        expected_c[at]=quant(smooth(oc[at],oc[cl],oc[cr],oc[up],oc[down]),4)
            s=(C.c_ubyte*self.lib.workspace(12,mode))()
            self.assertEqual(self.lib.render(C.byref(im),mode,s,len(s)),0)
            self.assertEqual(bytes(y),bytes(expected_y))
            self.assertEqual(bytes(c),bytes(expected_c))

    def test_handpaint_preserves_original_neighbors(self):
        im,y,c=self.frame(6,3,8)
        for r in range(3):
            for x in range(6): y[16+r*8+x]=100
        y[16+8+2]=116
        s=(C.c_ubyte*self.lib.workspace(6,3))()
        self.assertEqual(self.lib.render(C.byref(im),3,s,len(s)),0)
        self.assertEqual(y[16+8+2],112)
        # Original vertical neighborhoods are symmetric despite in-place traversal.
        self.assertEqual(y[16+2],y[16+16+2])

if __name__=='__main__': unittest.main()
