"""Execute final BIN text routers; only native text rendering leaves are stopped."""
import os
import struct
import subprocess
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
from unicorn.arm_const import *

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = Path(os.environ.get('M10V_INTEGRATED_BIN', str(ROOT/'builds/gr3-integrated-device-test/fw/fwdc239b.bin')))
RTOS = os.environ.get('M10V_INTEGRATED_RTOS')
BASE, STOP = 0x53000000, 0x550ff000

@unittest.skipUnless(RTOS or CANDIDATE.exists(), 'final integrated firmware not available')
class IntegratedResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if RTOS:
            cls.code = Path(RTOS).read_bytes()
        else:
            script = """import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"""
            cls.code = subprocess.check_output(['node','--input-type=module','-e',script,str(CANDIDATE)],cwd=ROOT)

    def machine(self):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);size=(len(self.code)+4095)&~4095
        u.mem_map(BASE,size);u.mem_write(BASE,self.code);u.mem_protect(BASE,size,UC_PROT_READ|UC_PROT_EXEC)
        u.mem_map(0x55000000,0x100000)
        # Existing stock string table and descriptor; native private descriptors remain real.
        for language in range(21):u.mem_write(0x55002bac+language*4,struct.pack('<I',0x55010000))
        u.mem_write(0x55010000+785*4,struct.pack('<I',0x55020000))
        u.mem_write(0x55020000,struct.pack('<HHI',0x0106,0,0x55020008)+ 'STOCK\0'.encode('utf-16le'))
        u.reg_write(UC_ARM_REG_SP,0x550f0000);u.reg_write(UC_ARM_REG_R11,0x550e0000);u.reg_write(UC_ARM_REG_LR,STOP)
        return u

    def test_primary_secondary_ranges_and_language_guards(self):
        for primary in [True,False]:
            entry,render,reject=(0x533966d4,0x53396700,0x53396850) if primary else (0x533970ec,0x5339710c,0x533971e0)
            for language in [1,19,20,21,0xffffffff]:
                for resource in [785,786,810,910,911,912]:
                    with self.subTest(primary=primary,language=language,resource=resource):
                        u=self.machine();seen=[]
                        def stop(uc,address,size,data):
                            if address in [render,reject]:seen.append(address);uc.emu_stop()
                        u.hook_add(UC_HOOK_CODE,stop);u.reg_write(UC_ARM_REG_R0,language);u.reg_write(UC_ARM_REG_R7,resource)
                        u.emu_start(entry,STOP,count=400)
                        valid=language<=20 and resource<=911
                        self.assertEqual(seen,[render if valid else reject])
                        if not valid:continue
                        pointer=u.reg_read(UC_ARM_REG_R7 if primary else UC_ARM_REG_R3)
                        if resource==785:self.assertEqual(pointer,0x55020000)
                        elif resource==911:self.assertEqual(pointer,0x540b97ec)
                        else:self.assertTrue(0x540ba000<=pointer<BASE+len(self.code))
                        header=bytes(u.mem_read(pointer,8));count=header[0];text_at=struct.unpack_from('<I',header,4)[0]
                        text=bytes(u.mem_read(text_at,count*2)).decode('utf-16le').rstrip('\0')
                        self.assertTrue(text)
                        if resource==911:self.assertEqual(text,'65:24')
                        elif resource==810:self.assertNotEqual(text,'65:24')

    def test_real_aspect_label_returns_disjoint_resource(self):
        u=self.machine();u.reg_write(UC_ARM_REG_R1,4)
        u.emu_start(0x53292544,STOP,count=40)
        self.assertEqual(u.reg_read(UC_ARM_REG_R0),911)

if __name__=='__main__':unittest.main()
