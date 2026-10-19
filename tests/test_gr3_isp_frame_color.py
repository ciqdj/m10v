import struct,tempfile,unittest
from pathlib import Path
from unicorn import UC_PROT_READ,UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_R0
from tests.test_gr3_isp_base import StockISP,ROOT
from scripts.build_gr3_isp_frame_color import build

class FrameColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        with tempfile.TemporaryDirectory() as d:cls.code,cls.manifest=build(d)

    def fixture(self):
        e=StockISP(self.rom);e.make(11)
        # The fixture's last allocation is SI; object+info allocation is fixed.
        obj=0x60000000;info=obj+0x400+0x1000
        gamma=struct.unpack('<I',e.u.mem_read(obj+0x17c,4))[0]
        at=self.manifest['base'];e.u.mem_map(at,65536);e.u.mem_write(at,self.code)
        e.u.mem_protect(at,65536,UC_PROT_READ|UC_PROT_EXEC)
        identity=[8192,0,0,0,8192,0,0,0,8192];post=[512,0,0,0,512,0,0,0,512]
        curves=[min(i*64,16383) for i in range(256)]
        return e,obj,info,gamma,identity,post,curves

    def invoke(self,e,info,gamma,m,p,curves):
        target=e.alloc(36+1536)
        e.u.mem_write(target,struct.pack('<18h768H',*(m+p+curves*3)))
        e.call(self.manifest['symbols']['m10v_isp_frame_apply'],gamma,info,target,0)
        return e.u.reg_read(UC_ARM_REG_R0)

    def test_compiled_writer_changes_only_frame_banks_and_preserves_cached_object(self):
        e,obj,info,gamma,m,p,c=self.fixture()
        original=bytes(e.u.mem_read(gamma,0x3240));before=bytes(e.u.mem_read(info,0x9000))
        c=[i*48 for i in range(256)]
        self.assertEqual(self.invoke(e,info,gamma,m,p,c),1)
        after=bytes(e.u.mem_read(info,0x9000));diff=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
        self.assertGreater(len(diff),0)
        self.assertTrue(all(0x2688<=i<0x5088 for i in diff))
        self.assertEqual(bytes(e.u.mem_read(gamma,0x3240)),original)
        e.call(0x536dd8f0,obj,info)
        self.assertEqual(bytes(e.u.mem_read(info,0x9000)),before)

    def test_rejection_is_atomic_for_nonmonotone_or_overflow_parameters(self):
        for bad in ('curve','matrix','post'):
            e,obj,info,gamma,m,p,c=self.fixture();before=bytes(e.u.mem_read(info,0x9000))
            if bad=='curve':c[80]=0
            elif bad=='matrix':m=[32767,-32768,0,-32768,32767,0,0,0,32767]
            else:p=[32767]*9
            self.assertEqual(self.invoke(e,info,gamma,m,p,c),0,bad)
            self.assertEqual(bytes(e.u.mem_read(info,0x9000)),before)

    def test_relative_matrix_composes_after_native_matrix_and_preserves_register_flags(self):
        e,obj,info,gamma,m,p,c=self.fixture()
        native=[v&4095 for v in struct.unpack('<9H',e.u.mem_read(info+0x140,18))]
        native=[v-4096 if v>=2048 else v for v in native]
        m=[8192,256,0,0,8192,128,0,0,8192]
        self.assertEqual(self.invoke(e,info,gamma,m,p,c),1)
        actual=[v&4095 for v in struct.unpack('<9H',e.u.mem_read(info+0x140,18))]
        actual=[v-4096 if v>=2048 else v for v in actual]
        expected=[(sum(m[r*3+k]*native[k*3+col] for k in range(3))+4096)>>13 for r in range(3) for col in range(3)]
        self.assertEqual(actual,expected)
