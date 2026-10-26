"""Real 2.20 updater instructions; version services substituted, no flash IO."""
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import unittest
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP

ROOT=Path(__file__).resolve().parents[1]

class Gr3220UpdateGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=os.environ.get('M10V_GR3_220_FIXTURE')
        if not fixture:raise unittest.SkipTest('set M10V_GR3_220_FIXTURE to exact official 2.20')
        data=Path(fixture).read_bytes()
        assert hashlib.sha256(data).hexdigest()=='5c53760b3b564c87239dbf7f5c94d0f6fd91accd156ec4ba672ebfd6b861793e'
        js="""import{readFileSync}from'node:fs';import{readOfficialSection}from'./node/firmware.mjs';process.stdout.write(readOfficialSection(readFileSync(process.argv[1]),process.argv[2]));"""
        cls.official220=data
        cls.cpu220=subprocess.check_output(['node','--input-type=module','-e',js,fixture,'CPU'],cwd=ROOT)
        cls.rom=subprocess.check_output(['node','--input-type=module','-e',js,fixture,'RTOS'],cwd=ROOT)
        # Exact instructions independently located in official 2.20 (not 2.10 addresses).
        assert cls.rom[0x628664:0x62866c]==bytes.fromhex('000055e11700003a')
        js="""import{readFileSync}from'node:fs';import{applyGr3UpdateCompatibility}from'./node/gr3-version-unlock.mjs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const s=readFileSync('bin/fwdc239b-gr3-official.bin'),r=applyGr3UpdateCompatibility(s,{imported_sha256:process.argv[1]});process.stdout.write(process.argv[2]==='decoded'?decodeFrameMap(r.candidate).decoded:r.candidate);"""
        args=['node','--input-type=module','-e',js,hashlib.sha256(data).hexdigest()]
        cls.candidate=subprocess.check_output(args,cwd=ROOT)
        cls.decoded=subprocess.check_output(args+['decoded'],cwd=ROOT)
        final=os.environ.get('M10V_GR3_220_CANDIDATE')
        if final:
            cls.candidate=Path(final).read_bytes()
            js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';process.stdout.write(decodeFrameMap(readFileSync(process.argv[1])).decoded);"
            cls.decoded=subprocess.check_output(['node','--input-type=module','-e',js,final],cwd=ROOT)
        cls.stock=(ROOT/'bin/fwdc239b-gr3-official.bin').read_bytes()
        at=0;sections={}
        while at<len(cls.decoded)-4:
            name=cls.decoded[at:at+8].split(b'\0')[0].decode('ascii')
            length=struct.unpack_from('<I',cls.decoded,at+12)[0]
            if name=='RES':length=6595272
            sections[name]=(at+16,length);at+=16+length
        cls.rtos_offset,cls.rtos_size=sections['RTOS'];cls.cpu_offset,_=sections['CPU']
        assert cls.candidate[0x38:0x3c]==cls.candidate[0x50:0x54]==bytes.fromhex('0214151c')

    def machine(self,rom,current,legacy=False):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,(len(rom)+65535)&~65535);u.mem_write(0x53000000,rom)
        u.mem_map(0x55000000,0x100000)
        getters=(0x53547bac,0x53547bf0) if legacy else (0x53547c9c,0x53547ce0)
        diagnostic=0x536b82d4 if legacy else 0x536b83c4
        def hook(u,pc,size,data):
            if pc in (*getters,diagnostic):
                u.reg_write(UC_ARM_REG_R0,current if pc in getters else 0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,hook);return u

    def gate(self,u,header,cpu,kind,entry):
        obj=0x55001000;buf=0x55010000;p=0x55002000
        for at,value in ((obj+8,0x55003000),(obj+0x1c,p),(obj+0x20,p),(obj+0x24,p),(p+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buf)):
            u.mem_write(at,struct.pack('<I',value))
        u.mem_write(buf,header[:128]);u.mem_write(buf+0x90,bytes(cpu[0x90:0x94]))
        u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x550ff000);u.reg_write(UC_ARM_REG_LR,0x550ffff0)
        u.emu_start(entry,0x550ffff0,count=2000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550ffff0)
        return u.reg_read(UC_ARM_REG_R0)

    def test_real_220_gate_rejects_old_export_and_accepts_fixed_export(self):
        cpu=self.decoded[self.cpu_offset:self.cpu_offset+131072]
        old_cpu=bytearray(cpu);old_cpu[0x90:0x94]=bytes.fromhex('020a151b')
        for kind in (0,1,2,3,4,6):
            with self.subTest(kind=kind):
                self.assertEqual(self.gate(self.machine(self.rom,0x0214141c),self.stock,old_cpu,kind,0x536285d0),0)
                self.assertEqual(self.gate(self.machine(self.rom,0x0214141c),self.candidate,cpu,kind,0x536285d0),1)
                self.assertEqual(self.gate(self.machine(self.rom,0x0214151c),self.candidate,cpu,kind,0x536285d0),1)
                self.assertEqual(self.gate(self.machine(self.rom,0x0214151d),self.candidate,cpu,kind,0x536285d0),0)

    def test_final_updater_accepts_official_restore(self):
        rom=self.decoded[self.rtos_offset:self.rtos_offset+self.rtos_size]
        cpu=bytearray(131072);cpu[0x90:0x94]=bytes.fromhex('020a151b')
        for kind in (0,1,2,3,4,6):
            with self.subTest(kind=kind):
                self.assertEqual(self.gate(self.machine(rom,0x0214151c,True),self.stock,cpu,kind,0x536284e0),1)
                self.assertEqual(self.gate(self.machine(rom,0x0214151c,True),self.official220,self.cpu220,kind,0x536284e0),1)

    def test_real_220_cpu_validator_checks_final_payload(self):
        payload=self.decoded[self.cpu_offset:self.cpu_offset+131072]
        for mode,want in [('final',1),('bad_checksum',0),('wrong_model',0)]:
            with self.subTest(mode=mode):
                data=bytearray(payload)
                if mode=='bad_checksum':data[0x93]^=1
                if mode=='wrong_model':struct.pack_into('<I',data,0x80,609)
                u=self.machine(self.rom,0x0214141c)
                obj=0x55001000;buf=0x55010000
                u.mem_write(buf,bytes(data));u.mem_write(obj+0xc,struct.pack('<I',buf));u.mem_write(obj+0x14,struct.pack('<I',588))
                u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x550ff000);u.reg_write(UC_ARM_REG_LR,0x550ffff0)
                u.emu_start(0x536291b8,0x550ffff0,count=2000000)
                self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550ffff0)
                self.assertEqual(u.reg_read(UC_ARM_REG_R0),want)

if __name__=='__main__':unittest.main()
