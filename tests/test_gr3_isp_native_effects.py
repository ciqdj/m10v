"""Borrowed stock Granulation RAM edits; no hardware pixel simulator."""
import ctypes as C
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Config(C.Structure):
    _fields_=[('mask',C.c_uint32),('value',C.c_int16*4)]
class NativeEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        so=Path(cls.temp.name)/'effects.dylib'
        subprocess.run(['clang','-shared','-Wall','-Wextra','-Werror','-O2',str(ROOT/'native/gr3/m10v_isp_native_effects.c'),'-o',str(so)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(so))
        cls.lib.m10v_isp_native_effects_settings.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(Config)]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_settings_selective_transaction_and_scale_preserved(self):
        src=(C.c_int16*6)(-1,2,3,1,0x1234,0x5678);dst=(C.c_int16*6)(*([91]*6))
        cfg=Config(6,(C.c_int16*4)(0,-3,2,0))
        self.assertEqual(self.lib.m10v_isp_native_effects_settings(dst,src,C.byref(cfg)),0)
        self.assertEqual(list(dst),[-1,-3,2,1,0x1234,0x5678])
        cfg.value[2]=4
        self.assertEqual(self.lib.m10v_isp_native_effects_settings(dst,src,C.byref(cfg)),-1)
        self.assertEqual(list(dst),[-1,-3,2,1,0x1234,0x5678])
    def test_cpu_field_and_noise_size_exports_are_removed(self):
        self.assertFalse(hasattr(self.lib,'m10v_isp_native_effects_noise_shape'))
        self.assertFalse(hasattr(self.lib,'m10v_isp_native_effects_field'))

class NativeEffectsArmTests(unittest.TestCase):
    """Native ARM pointer layouts, no stock service or hardware double."""
    @classmethod
    def setUpClass(cls):
        import struct
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
        from unicorn import arm_const as A
        cls.A=A;cls.struct=struct;cls.temp=tempfile.TemporaryDirectory()
        obj=Path(cls.temp.name)/'effects.o';elf=obj.with_suffix('.elf')
        subprocess.run(['clang','--target=armv7-none-eabi','-mcpu=cortex-a9','-marm','-mfloat-abi=soft','-O2','-ffreestanding','-fno-builtin','-Wall','-Wextra','-Werror','-c',str(ROOT/'native/gr3/m10v_isp_native_effects.c'),'-o',str(obj)],check=True,capture_output=True)
        subprocess.run(['ld.lld','--entry=m10v_isp_native_effects_settings','-Ttext=0x54160000',str(obj),'-o',str(elf)],check=True,capture_output=True)
        data=elf.read_bytes();cls.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        cls.u.mem_map(0x54150000,0x40000);cls.u.mem_map(0x55000000,0x100000)
        ph=struct.unpack_from('<I',data,28)[0];psz,pnum=struct.unpack_from('<HH',data,42)
        for i in range(pnum):
            kind,off,va,_,sz,_,_,_=struct.unpack_from('<8I',data,ph+i*psz)
            if kind==1 and sz:
                if not 0x54150000<=va<0x54190000:cls.u.mem_map(va&~4095,((va&4095)+sz+4095)&~4095)
                cls.u.mem_write(va,data[off:off+sz])
        sh=struct.unpack_from('<I',data,32)[0];ss,sn=struct.unpack_from('<HH',data,46)
        rows=[struct.unpack_from('<10I',data,sh+i*ss) for i in range(sn)];cls.symbols={}
        for row in rows:
            if row[1]!=2:continue
            strings=rows[row[6]];names=data[strings[4]:strings[4]+strings[5]]
            for pos in range(row[4],row[4]+row[5],16):
                n,va,_,_,_,section=struct.unpack_from('<IIIBBH',data,pos)
                name=names[n:].split(b'\0',1)[0].decode()
                if name.startswith('m10v_isp_'):cls.symbols[name]=va
                if section==0 and name:raise AssertionError('unresolved ARM runtime '+name)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def invoke(self,*args):
        A=self.A;u=self.u
        for i,v in enumerate(args):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
        u.reg_write(A.UC_ARM_REG_SP,0x550f0000);u.reg_write(A.UC_ARM_REG_LR,0x550ff000)
        u.emu_start(self.symbols['m10v_isp_native_effects_grain_tables_owned'],0x550ff000,count=50000)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x550ff000)
        return u.reg_read(A.UC_ARM_REG_R0)
    def fixture(self):
        st=self.struct;u=self.u;graph=0x55001000;d=[0x55002000,0x55003000,0x55004000];src=[0x55006000,0x55007000,0x55008000]
        u.mem_write(graph,bytes(0x120));u.mem_write(graph,st.pack('<I',0x54034ce0))
        for offset,val in [(0x5c,d[0]),(0x64,d[0]),(0x6c,d[1]),(0x70,d[1]),(0x60,d[2]),(0x68,d[2])]:u.mem_write(graph+offset,st.pack('<I',val))
        u.mem_write(graph+0x74,st.pack('<6I',*([256]*6)))
        for i in range(3):
            u.mem_write(d[i],bytes([0xa5])*512);u.mem_write(src[i],st.pack('<256h',*[(x+i)%256 for x in range(256)]))
        return graph,d,src
    def test_borrowed_tables_preserve_entire_graph_and_original_destinations(self):
        g,d,s=self.fixture();before=bytes(self.u.mem_read(g,0x120))
        self.assertEqual(self.invoke(g,*s),0)
        self.assertEqual(bytes(self.u.mem_read(g,0x120)),before)
        for dst,src in zip(d,s):self.assertEqual(self.u.mem_read(dst,512),self.u.mem_read(src,512))
    def test_invalid_last_table_and_alias_are_transactional(self):
        g,d,s=self.fixture();before=[bytes(self.u.mem_read(x,512)) for x in d]
        self.u.mem_write(s[2]+510,self.struct.pack('<h',256))
        self.assertEqual(self.invoke(g,*s),0xffffffff)
        self.assertEqual([bytes(self.u.mem_read(x,512)) for x in d],before)
        self.fixture();self.assertEqual(self.invoke(g,d[0],s[1],s[2]),0xffffffff)
        self.assertEqual([bytes(self.u.mem_read(x,512)) for x in d],before)
    def test_original_topology_or_table_length_mismatch_is_rejected(self):
        g,d,s=self.fixture();self.u.mem_write(g+0x88,self.struct.pack('<I',255))
        self.assertEqual(self.invoke(g,*s),0xffffffff)
        self.assertTrue(all(bytes(self.u.mem_read(x,512))==bytes([0xa5])*512 for x in d))

if __name__=='__main__':unittest.main()
