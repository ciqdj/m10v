"""Exact blur primitive and bounded stock adapter; never an IIP pixel emulator."""
import ctypes as C
import json
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def oracle(values,w,h,passes,d):
    for _ in range(passes):
        b=[(values[y*w+max(0,x-d)]+2*values[y*w+x]+values[y*w+min(w-1,x+d)])>>2 for y in range(h) for x in range(w)]
        values=[(b[max(0,y-d)*w+x]+2*b[y*w+x]+b[min(h-1,y+d)*w+x])>>2 for y in range(h) for x in range(w)]
    return values

def hash32(x):
    x&=0xffffffff;x^=x>>16;x=x*0x7feb352d&0xffffffff
    x^=x>>15;x=x*0x846ca68b&0xffffffff;return x^(x>>16)

def noise_reference(gx,gy,seed,size):
    h=hash32(seed^(gx*0x9e3779b9)^(gy*0x85ebca6b))
    scale=1<<size;xx=gx>>size;yy=gy>>size;dx=gx&(scale-1);dy=gy&(scale-1)
    def corner(x,y):return (hash32(seed^(x*0x9e3779b9)^(y*0x85ebca6b))&255)-128
    n=(corner(xx,yy)*(scale-dx)*(scale-dy)+corner(xx+1,yy)*dx*(scale-dy)+corner(xx,yy+1)*(scale-dx)*dy+corner(xx+1,yy+1)*dx*dy)>>(size*2)
    return h,n+int(((h&255)-128)/3)

class SpatialHostTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'native/gr3/m10v_spatial_accel.c').is_file(), 'bounded spatial accelerator is not implemented')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        out=Path(self.tmp.name)/'spatial.dylib'
        subprocess.run([shutil.which('clang'),'-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'native/gr3/m10v_spatial_accel.c'),'-o',str(out)],check=True,capture_output=True)
        self.lib=C.CDLL(str(out))
        self.blur=self.lib.m10v_spatial_blur_u16
        self.blur.argtypes=[C.c_void_p,C.c_void_p]+[C.c_uint32]*5
        self.query=self.lib.m10v_spatial_grain_work_bytes
        self.query.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32)]

    def test_per_pass_rounding_full_u16_range_and_replicated_edges(self):
        for w,h in ((1,1),(2,7),(7,2),(17,13),(384,256)):
            for d in (1,2):
                rng=random.Random(w+h+d);v=[rng.randrange(65536) for _ in range(w*h)]
                v[0]=65535
                a=(C.c_uint16*(w*h+16))(*v,*([0xa55a]*16));b=(C.c_uint16*(w*h+16))(*([0x5aa5]*(w*h+16)))
                self.assertEqual(self.blur(a,b,w*h,w,h,3,d),0)
                self.assertEqual(list(a)[:w*h],oracle(v,w,h,3,d),(w,h,d))
                self.assertEqual(list(a)[w*h:],[0xa55a]*16);self.assertEqual(list(b)[w*h:],[0x5aa5]*16)

    def test_invalid_dimensions_alias_capacity_and_distance_do_not_write(self):
        a=(C.c_uint16*128)(*range(128));b=(C.c_uint16*128)(*range(128,256));before=bytes(a),bytes(b)
        for capacity,w,h,passes,d in ((127,16,8,3,1),(128,0,8,3,1),(128,16,8,10,1),(128,16,8,3,0),(128,16,8,3,3),(128,385,1,1,1)):
            self.assertEqual(self.blur(a,b,capacity,w,h,passes,d),-1)
            self.assertEqual((bytes(a),bytes(b)),before)
        self.assertEqual(self.blur(a,a,128,16,8,3,1),-1)
        self.assertEqual(self.blur(a,C.byref(a,2),127,8,8,3,1),-1)
        self.assertEqual((bytes(a),bytes(b)),before)

    def test_grain_work_capacity_includes_alignment_and_rejects_overflow(self):
        for w,h,address,want in ((6000,4000,0,24000000),(3360,2240,0,7526400),(6144,4096,0,25165824),(2,1,0x55000001,31)):
            out=C.c_uint32(0xabad1dea)
            self.assertEqual(self.query(w,h,address,C.byref(out)),0);self.assertEqual(out.value,want)
        for w,h,address in ((0,1,0),(6146,1,0),(2,4097,0),(2,1,0xfffffff1)):
            out=C.c_uint32(0xabad1dea)
            self.assertEqual(self.query(w,h,address,C.byref(out)),-1);self.assertEqual(out.value,0xabad1dea)

    def test_noise8_matches_frozen_hash_bilinear_and_signed_division(self):
        self.assertTrue(hasattr(self.lib,'m10v_spatial_grain_noise8'),'exact grain SIMD primitive is not implemented')
        f=self.lib.m10v_spatial_grain_noise8
        f.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p]
        for size in (0,1,2):
            for gy,seed in ((0,0),(1,42),(3999,0xffffffff)):
                for xs in (list(range(8)),list(range(5992,6000)),[0,1,16,200,1025,3000,5999,6000]):
                    gx=(C.c_uint32*8)(*xs);hh=(C.c_uint32*16)(*([0xdeadbeef]*16));nn=(C.c_int32*16)(*([-12345]*16))
                    self.assertEqual(f(gx,gy,seed,size,hh,nn),0)
                    want=[noise_reference(x,gy,seed,size) for x in xs]
                    self.assertEqual(list(hh)[:8],[v[0] for v in want]);self.assertEqual(list(nn)[:8],[v[1] for v in want])
                    self.assertEqual(list(hh)[8:],[0xdeadbeef]*8);self.assertEqual(list(nn)[8:],[-12345]*8)
        before=bytes(hh),bytes(nn),bytes(gx)
        self.assertEqual(f(gx,0,0,3,hh,nn),-1);self.assertEqual(f(gx,0,0,1,gx,nn),-1)
        self.assertEqual((bytes(hh),bytes(nn),bytes(gx)),before)

class SpatialArmTests(unittest.TestCase):
    def test_noise8_neon_preserves_exact_hash_and_signed_bilinear_output(self):
        from scripts.build_gr3_spatial_accel import build
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
        from unicorn import arm_const as A
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            report=build(tmp);code=(Path(tmp)/'m10v-spatial-arm.bin').read_bytes()
            u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(report['base'],(len(code)+4095)&~4095);u.mem_write(report['base'],code)
            u.mem_map(0x55000000,0x100000)
            u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
            xs=[0,1,7,16,33,1025,5999,6000]
            u.mem_write(0x55001000,struct.pack('<8I',*xs))
            for size in (0,1,2):
                for gy,seed in ((0,0),(1,42),(3999,0xffffffff)):
                    sp,stop=0x550fe000,0x550ff000
                    u.mem_write(0x55002000,b'\x5a'*64);u.mem_write(0x55003000,b'\xa5'*64)
                    u.mem_write(sp,struct.pack('<II',0x55002000,0x55003000))
                    for reg,val in ((A.UC_ARM_REG_R0,0x55001000),(A.UC_ARM_REG_R1,gy),(A.UC_ARM_REG_R2,seed),(A.UC_ARM_REG_R3,size),(A.UC_ARM_REG_SP,sp),(A.UC_ARM_REG_LR,stop)):u.reg_write(reg,val)
                    saved={getattr(A,f'UC_ARM_REG_D{i}'):0x1234000000000000+i for i in range(8,16)}
                    for reg,val in saved.items():u.reg_write(reg,val)
                    u.emu_start(report['symbols']['m10v_spatial_grain_noise8'],stop,count=100000)
                    self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop);self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),0)
                    want=[noise_reference(x,gy,seed,size) for x in xs]
                    self.assertEqual(list(struct.unpack('<8I',u.mem_read(0x55002000,32))),[v[0] for v in want])
                    self.assertEqual(list(struct.unpack('<8i',u.mem_read(0x55003000,32))),[v[1] for v in want])
                    self.assertEqual(bytes(u.mem_read(0x55002020,32)),b'\x5a'*32)
                    self.assertEqual(bytes(u.mem_read(0x55003020,32)),b'\xa5'*32)
                    self.assertEqual({reg:u.reg_read(reg) for reg in saved},saved)

    def test_stock_grain_execution_preflights_workspace_and_forwards_original_abi(self):
        self.assertTrue((ROOT/'scripts/build_gr3_spatial_accel.py').is_file())
        from scripts.build_gr3_spatial_accel import build
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
        from unicorn import arm_const as A
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            report=build(tmp)
            self.assertIn('m10v_spatial_stock_grain_execute',report['symbols'],'native grain ABI adapter is not implemented')
            code=(Path(tmp)/'m10v-spatial-arm.bin').read_bytes()
            u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(report['base'],(len(code)+4095)&~4095);u.mem_write(report['base'],code)
            u.mem_map(0x55000000,0x100000);u.mem_map(0x5367a000,0x2000)
            source,destination,context,workspace=0x55001000,0x55002000,0x55003000,0x550a0000
            for desc,plane in ((source,0x55080000),(destination,0x55090000)):
                u.mem_write(desc,struct.pack('<4I4H2I',1,plane,0,0,16,8,16,8,0,0))
            calls=[];native_result=[1]
            def grain(uc,pc,size,data):
                if pc!=0x5367ad3c:return
                sp=uc.reg_read(A.UC_ARM_REG_SP)
                work,size_pointer=struct.unpack('<II',uc.mem_read(sp,8))
                calls.append((tuple(uc.reg_read(r) for r in (A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3)),work,struct.unpack('<I',uc.mem_read(size_pointer,4))[0]))
                uc.reg_write(A.UC_ARM_REG_R0,native_result[0]);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE,grain)
            def call(capacity,work=workspace):
                sp,stop=0x550fe000,0x550ff000
                u.mem_write(sp,struct.pack('<II',work,capacity))
                for reg,val in ((A.UC_ARM_REG_R0,context),(A.UC_ARM_REG_R1,source),(A.UC_ARM_REG_R2,destination),(A.UC_ARM_REG_R3,2),(A.UC_ARM_REG_SP,sp),(A.UC_ARM_REG_LR,stop)):u.reg_write(reg,val)
                u.emu_start(report['symbols']['m10v_spatial_stock_grain_execute'],stop,count=100000)
                self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop)
                v=u.reg_read(A.UC_ARM_REG_R0);return v-(1<<32) if v>>31 else v
            self.assertEqual(call(127),-1);self.assertEqual(calls,[])
            self.assertEqual(call(128,0x55080000),-1);self.assertEqual(calls,[])
            u.mem_write(destination+4,struct.pack('<I',context))
            self.assertEqual(call(128),-1);self.assertEqual(calls,[])
            u.mem_write(destination+4,struct.pack('<I',0x55090000))
            self.assertEqual(call(128),0)
            self.assertEqual(calls,[((context,source,destination,2),workspace,128)])
            native_result[0]=0;self.assertEqual(call(128),-4)

    def test_neon_machine_code_matches_scalar_and_preserves_callee_saved_vfp(self):
        self.assertTrue((ROOT/'scripts/build_gr3_spatial_accel.py').is_file(),'spatial ARM builder is not implemented')
        from scripts.build_gr3_spatial_accel import build
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
        from unicorn import arm_const as A
        from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
        with tempfile.TemporaryDirectory() as tmp:
            report=build(tmp);code=(Path(tmp)/'m10v-spatial-arm.bin').read_bytes()
            instructions=list(Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(code,report['base']))
            self.assertTrue(any(i.mnemonic=='vaddl.u16' for i in instructions),'blur did not emit widening NEON arithmetic')
            self.assertFalse(report['firmware_emitted']);self.assertFalse(report['exact_full_isp'])
            for w,h,d in ((1,1,2),(18,7,1),(31,17,2),(384,256,2)):
                u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(report['base'],(len(code)+4095)&~4095);u.mem_write(report['base'],code)
                u.mem_map(0x55000000,0x100000)
                u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
                n=w*h;rng=random.Random(n);v=[rng.randrange(65536) for _ in range(n)]
                import struct
                u.mem_write(0x55000000,struct.pack('<'+'H'*n,*v)+b'\x5a'*32)
                u.mem_write(0x55040000,b'\xa5'*(2*n+32))
                sp=0x550fe000;stop=0x550ff000
                for i,val in enumerate((h,3,d)):u.mem_write(sp+i*4,struct.pack('<I',val))
                for reg,val in ((A.UC_ARM_REG_R0,0x55000000),(A.UC_ARM_REG_R1,0x55040000),(A.UC_ARM_REG_R2,n),(A.UC_ARM_REG_R3,w),(A.UC_ARM_REG_SP,sp),(A.UC_ARM_REG_LR,stop)):
                    u.reg_write(reg,val)
                saved={getattr(A,f'UC_ARM_REG_D{i}'):0x1234000000000000+i for i in range(8,16)}
                for reg,val in saved.items():u.reg_write(reg,val)
                u.emu_start(report['symbols']['m10v_spatial_blur_u16'],stop,count=50000000)
                self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop);self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),0)
                self.assertEqual(list(struct.unpack('<'+'H'*n,u.mem_read(0x55000000,n*2))),oracle(v,w,h,3,d))
                self.assertEqual(bytes(u.mem_read(0x55000000+n*2,32)),b'\x5a'*32)
                self.assertEqual(bytes(u.mem_read(0x55040000+n*2,32)),b'\xa5'*32)
                self.assertEqual({reg:u.reg_read(reg) for reg in saved},saved)

if __name__=='__main__':unittest.main()
