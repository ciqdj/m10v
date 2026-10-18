"""Execute the official GR III updater comparisons and CPU validation.

Only current DSP/CPU version getters and diagnostic output are substituted.
The updater, parsers, project/marker wrapper and additive checksum run as ARM.
This does not execute flash writes or the complete on-camera update state.
"""
import hashlib
import struct
import subprocess
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC)

ROOT=Path(__file__).resolve().parents[1]

class UpdaterVersionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js="import{readFileSync}from'node:fs';import{readOfficialSection}from'./node/firmware.mjs';process.stdout.write(readOfficialSection(readFileSync('bin/fwdc239b-gr3-official.bin'),process.argv[1]));"
        cls.rom=subprocess.check_output(['node','--input-type=module','-e',js,'RTOS'],cwd=ROOT)
        cls.cpu=subprocess.check_output(['node','--input-type=module','-e',js,'CPU'],cwd=ROOT)
        if hashlib.sha256(cls.rom).hexdigest()!='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67':
            raise AssertionError('unsupported official updater instruction image')

    def machine(self,current_dsp=0x020a1528,current_cpu=0x020a151b):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        u.mem_map(0x53000000,(len(self.rom)+65535)&~65535);u.mem_write(0x53000000,self.rom)
        u.mem_map(0x55000000,0x100000)
        comparisons=[]
        def service(u,pc,size,data):
            if pc in (0x53628574,0x536285d4,0x53628628,0x53628640):comparisons.append(pc)
            if pc in (0x53547bac,0x53547bf0,0x536b82d4):
                u.reg_write(UC_ARM_REG_R0,current_dsp if pc==0x53547bac else current_cpu if pc==0x53547bf0 else 0)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,service)
        return u,comparisons

    def call(self,u,entry,obj):
        u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x550ff000);u.reg_write(UC_ARM_REG_LR,0x550ffff0)
        u.emu_start(entry,0x550ffff0,count=2000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550ffff0)
        return u.reg_read(UC_ARM_REG_R0)

    def test_component_versions_compare_unsigned_and_equality_passes_observed_gate(self):
        # Synthetic current values exercise independence; these are NOT known
        # anniversary service firmware versions. Expected results are literals.
        cases=[
            (0,-1,1,0),(0,0,-1,1),(0,1,-1,1),
            (1,-1,1,0),(1,0,-1,1),(1,1,-1,1),
            (2,-1,0,0),(2,0,-1,0),(2,0,0,1),(2,1,-1,0),(2,-1,1,0),(2,1,1,1),
            (3,0,0,1),(3,0,-1,0),(3,-1,1,0),
            (4,0,0,1),(4,1,-1,0),(4,1,1,1),
            (6,1,-1,0),(6,-1,0,1),
        ]
        for kind,dsp_delta,cpu_delta,want in cases:
            with self.subTest(type=kind,dsp_delta=dsp_delta,cpu_delta=cpu_delta):
                u,comparisons=self.machine();obj=0x55001000;buffer=0x55010000;parser=0x55002000
                for at,value in ((obj+8,0x55003000),(obj+0x1c,parser),(obj+0x20,parser),
                                 (obj+0x24,parser),(parser+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buffer)):
                    u.mem_write(at,struct.pack('<I',value))
                u.mem_write(buffer+0x38,(0x020a1528+dsp_delta).to_bytes(4,'big'))
                u.mem_write(buffer+0x50,(0x020a151b+cpu_delta).to_bytes(4,'big'))
                u.mem_write(buffer+0x90,(0x020a151b+cpu_delta).to_bytes(4,'big'))
                self.assertEqual(self.call(u,0x536284e0,obj),want)
                self.assertIn(0x53628628 if kind in (0,1) else 0x53628574 if kind==6 else 0x536285d4,comparisons)
                if kind in (2,3,4) and dsp_delta>=0:self.assertIn(0x53628640,comparisons)

    def test_cpu_payload_version_requires_real_checksum_and_matching_project(self):
        for mode,want in (('official',1),('version_only',0),('repaired',1),('wrong_project',0)):
            with self.subTest(mode=mode):
                data=bytearray(self.cpu)
                if mode in ('version_only','repaired'):data[0x90:0x94]=bytes.fromhex('020a1528')
                if mode=='repaired':
                    struct.pack_into('>I',data,0x7c,0)
                    struct.pack_into('>I',data,0x7c,-sum(struct.unpack('>32768I',data))&0xffffffff)
                if mode=='wrong_project':struct.pack_into('<I',data,0x80,609)
                u,_=self.machine();obj=0x55001000;buffer=0x55010000;u.mem_write(buffer,bytes(data))
                u.mem_write(obj+0xc,struct.pack('<I',buffer));u.mem_write(obj+0x14,struct.pack('<I',588))
                self.assertEqual(self.call(u,0x536290c8,obj),want)

    def test_dsp_package_header_does_not_raise_real_startup_model_reported_version(self):
        # Execute the real startup version fragment, both constant getters,
        # model setter/swap, NEON memcpy and current-version model getter.
        # The message queue and full camera boot are outside this fixture.
        for header in (0x020a151b,0x020affff):
            with self.subTest(rtos_header=hex(header)):
                u,_=self.machine()
                u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000)
                u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
                u.mem_write(0x53002038,header.to_bytes(4,'big'))
                frame=0x550ff800;source=frame-0x7c
                u.reg_write(UC_ARM_REG_SP,0x550ff000)
                u.reg_write(UC_ARM_REG_FP,frame)
                u.emu_start(0x5356034c,0x5356036c,count=100)
                self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x5356036c)
                self.assertEqual(struct.unpack('<I',bytes(u.mem_read(source+8,4)))[0],0x020a151b)
                obj=0x55001000;old_model=0x55010000;new_model=0x55012000
                u.mem_write(obj,struct.pack('<III',old_model,new_model,0))
                u.reg_write(UC_ARM_REG_R1,source)
                self.assertEqual(self.call(u,0x53551f74,obj),1)
                self.assertEqual(struct.unpack('<I',bytes(u.mem_read(obj,4)))[0],new_model)
                self.assertEqual(self.call(u,0x53550d98,obj),0x020a151b)

    def test_dsp_package_ceiling_keeps_stock_rejection_for_a_higher_cpu(self):
        for kind in (2,6):
            for current_cpu,want in ((0x020a151b,1),(0x020a151c,0)):
                with self.subTest(type=kind,current_cpu=hex(current_cpu)):
                    u,_=self.machine(current_dsp=0x020afeff,current_cpu=current_cpu)
                    obj=0x55001000;buffer=0x55010000;parser=0x55002000
                    for at,value in ((obj+8,0x55003000),(obj+0x1c,parser),(obj+0x20,parser),
                                     (obj+0x24,parser),(parser+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buffer)):
                        u.mem_write(at,struct.pack('<I',value))
                    u.mem_write(buffer+0x38,bytes.fromhex('020affff'))
                    u.mem_write(buffer+0x50,bytes.fromhex('020a151b'))
                    u.mem_write(buffer+0x90,bytes.fromhex('020a151b'))
                    self.assertEqual(self.call(u,0x536284e0,obj),want)

    def test_bridge_version_transition_and_inner_cpu_gate(self):
        # Synthetic service versions, not anniversary measurements. This tests
        # only the stock comparison, not installation or a CPU runtime patch.
        cases = [
            ('first_package_both_ceilings', 2, 0x020a1528, 0x020a1528, 0x020affff, 0x020affff, 0x020affff, 1),
            ('outer_only_cpu_raise_is_insufficient', 6, 0x020a1528, 0x020a1528, 0x020affff, 0x020affff, 0x020a151b, 0),
            ('second_stock_package_cpu_still_high', 2, 0x020a151b, 0x020a15ff, 0x020a151b, 0x020a151b, 0x020a151b, 0),
            ('second_stock_package_both_runtime_baseline', 2, 0x020a151b, 0x020a151b, 0x020a151b, 0x020a151b, 0x020a151b, 1),
        ]
        for name,kind,dsp,cpu,outer_dsp,outer_cpu,inner_cpu,want in cases:
            with self.subTest(case=name):
                u,_=self.machine(current_dsp=dsp,current_cpu=cpu)
                obj=0x55001000;buffer=0x55010000;parser=0x55002000
                for at,value in ((obj+8,0x55003000),(obj+0x1c,parser),(obj+0x20,parser),
                                 (obj+0x24,parser),(parser+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buffer)):
                    u.mem_write(at,struct.pack('<I',value))
                for offset,value in ((0x38,outer_dsp),(0x50,outer_cpu),(0x90,inner_cpu)):
                    u.mem_write(buffer+offset,value.to_bytes(4,'big'))
                self.assertEqual(self.call(u,0x536284e0,obj),want)

if __name__=='__main__':unittest.main()
