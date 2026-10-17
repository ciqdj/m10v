"""Byte-exact nearfield filtering and deterministic hot-path work budget."""
import ctypes as C
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image, Slot

ROOT = Path(__file__).resolve().parents[1]


class HalationLinePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        source = (ROOT / 'native/gr3/halation_energy.h').read_text()
        signature = 'uint32_t gate,int red_sensitive) {'
        # Count actual original-pixel evaluations without adding production hooks.
        source = source.replace(signature, signature + '\n++pixel_evaluations;', 1)
        reference = source
        start = reference.index('{', reference.index('static void energy_line(')) + 1
        end = reference.index('\n}', start)
        reference = reference[:start] + """
    for(uint32_t x=0;x<im->width;++x)
        line[x]=(uint16_t)((energy_pixel(im,energy_edge(x,im->width,-distance),row,gate,1)+
            2*energy_pixel(im,x,row,gate,1)+energy_pixel(im,energy_edge(x,im->width,distance),row,gate,1))>>2);""" + reference[end:]
        effect_probe = """
void effect(m10v_library_image *im,const m10v_slot *slot,unsigned char *scratch,unsigned gw,unsigned gh,unsigned shift) {
 m10v_800t_effects(im,slot,scratch,gw,gh,shift);
}
"""
        reference_path = Path(cls.tmp.name) / 'reference.c'
        reference_path.write_text('#include "m10v_library.h"\nstatic unsigned pixel_evaluations;\n' + reference + effect_probe)
        reference_dylib = reference_path.with_suffix('.dylib')
        subprocess.run([shutil.which('clang'), '-O2', '-dynamiclib', '-I', str(ROOT/'native/gr3'), str(reference_path), '-o', str(reference_dylib)], check=True, capture_output=True)
        cls.reference = C.CDLL(str(reference_dylib))
        wrapper = '#include "m10v_library.h"\nstatic unsigned pixel_evaluations;\n' + source + '''
unsigned probe(const m10v_library_image *im,unsigned short *out,unsigned row,unsigned gate,int distance) {
 pixel_evaluations=0; energy_line(im,out,row,gate,distance); return pixel_evaluations;
}
'''
        wrapper += effect_probe
        path = Path(cls.tmp.name) / 'line.c'
        path.write_text(wrapper)
        dylib = path.with_suffix('.dylib')
        subprocess.run([shutil.which('clang'), '-O2', '-dynamiclib', '-I', str(ROOT/'native/gr3'), str(path), '-o', str(dylib)], check=True, capture_output=True)
        cls.lib = C.CDLL(str(dylib))
        for lib in (cls.lib, cls.reference):
            lib.effect.argtypes = [C.POINTER(Image), C.POINTER(Slot), C.POINTER(C.c_uint8), C.c_uint32, C.c_uint32, C.c_uint32]
        cls.lib.probe.argtypes = [C.POINTER(Image), C.POINTER(C.c_uint16), C.c_uint32, C.c_uint32, C.c_int]

    def run_line(self, width, distance, gate, seed):
        rng = random.Random(seed)
        stride = width + 8
        y = (C.c_uint8 * (stride*3))(*(rng.randrange(256) for _ in range(stride*3)))
        uv = (C.c_uint8 * (stride*3))(*(rng.randrange(256) for _ in range(stride*3)))
        image = Image(y, uv, len(y), len(uv), width, 3, stride)
        out = (C.c_uint16 * width)()
        before = bytes(y), bytes(uv)
        calls = self.lib.probe(C.byref(image), out, 1, gate, distance)
        def energy(x):
            light = y[stride+x]
            red = min(255, light + ((359*(uv[stride+(x&~1)+1]-128))>>8)-24)
            return max(0, max(light, red)-gate)**2*8
        expected = [(energy(max(0,x-distance))+2*energy(x)+energy(min(width-1,x+distance)))>>2 for x in range(width)]
        self.assertEqual(list(out), expected)
        self.assertEqual((bytes(y),bytes(uv)),before)
        return calls

    def test_nearfield_matches_reference_at_edges_and_partial_distance_lanes(self):
        for width in (2,4,6,14,30,128,6000):
            for distance in (1,2,4):
                for gate in (176,200,240):
                    with self.subTest(width=width,distance=distance,gate=gate):
                        self.run_line(width,distance,gate,width+distance+gate)

    def test_complete_800t_effects_match_original_bytes_and_padding(self):
        for width,height in ((2,1),(6,7),(30,17),(386,259),(6000,4000)):
            shift=0
            while ((width+(1<<shift)-1)>>shift)>384 or ((height+(1<<shift)-1)>>shift)>256:
                shift+=1
            gw=(width+(1<<shift)-1)>>shift;gh=(height+(1<<shift)-1)>>shift
            stride=width+8;size=stride*height
            rng=random.Random(width+height)
            luminance=(bytes(range(256))*((size+255)//256))[:size]
            chroma=(rng.randbytes(512)*((size+511)//512))[:size]
            for gain,soft,spread,threshold in ((0,3,0,0),(1,0,0,8),(8,3,8,0),(4,0,3,3)):
                slot=Slot(33,0,soft,gain,spread,threshold,2)
                results=[]
                for lib in (self.reference,self.lib):
                    y=(C.c_uint8*size).from_buffer_copy(luminance)
                    uv=(C.c_uint8*size).from_buffer_copy(chroma)
                    scratch=(C.c_uint8*(6*gw*gh+32))()
                    C.memset(scratch,173,len(scratch))
                    image=Image(y,uv,size,size,width,height,stride)
                    lib.effect(C.byref(image),C.byref(slot),scratch,gw,gh,shift)
                    self.assertEqual(bytes(scratch)[-32:],bytes([173])*32)
                    results.append((bytes(y),bytes(uv)))
                with self.subTest(width=width,height=height,gain=gain,soft=soft,spread=spread,threshold=threshold):
                    self.assertEqual(results[0],results[1])
                    for row in range(height):
                        at=row*stride+width
                        self.assertEqual(results[1][0][at:at+8],luminance[at:at+8])
                        self.assertEqual(results[1][1][at:at+8],chroma[at:at+8])

    def test_nearfield_evaluates_each_pixel_once_plus_lane_boundaries(self):
        for distance in (1,2,4):
            with self.subTest(distance=distance):
                self.assertLessEqual(self.run_line(6000,distance,200,54),6000+2*distance)


if __name__ == '__main__':
    unittest.main()
