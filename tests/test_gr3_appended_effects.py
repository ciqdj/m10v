"""Appended tone identities must retain HDF and native grain traversal."""
import inspect
import os
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests import test_gr3_digital_hdf as hdf
from tests import test_gr3_native_grain_hooks as grain
from scripts.build_gr3_m10v_library import build


class AppendedHdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        artifact=os.environ.get('M10V_APPENDED_CANDIDATE')
        if artifact:
            cls.manifest=json.loads((Path(artifact)/'gr3/manifest.json').read_text())
            cls.runtime=(Path(artifact)/'evidence/runtime.bin').read_bytes()
        else:
            cls.manifest=build(cls.tmp.name,sd_library=True,appended_slots=True,hdf_enabled=True)
            cls.runtime=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
    machine=hdf.HdfExecutionTests.machine
    call=hdf.HdfExecutionTests.call
    produce=hdf.HdfExecutionTests.produce
    gate=hdf.HdfExecutionTests.gate
    settings=hdf.HdfExecutionTests.settings

    def test_each_appended_film_keeps_hdf_strength_in_both_native_stages(self):
        for tone in (25,26,27,28,29):
            for strength in (1,2,3):
                e=self.machine(strength);e['u'].mem_write(e['si']+0x77c,bytes([tone]))
                self.produce(e);self.gate(e)
                self.assertEqual(self.settings(e,False)[1],4+strength)
                self.assertEqual(self.settings(e,True)[1],4+strength)
                self.assertEqual(e['loads'],1)


class AppendedGrainGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact=os.environ.get('M10V_APPENDED_CANDIDATE')
        if artifact:
            js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
            cls.rom=subprocess.check_output(['node','--input-type=module','-e',js,str(Path(artifact)/'gr3/fwdc239b.bin')],cwd=grain.ROOT)
            cls.delivered=True
            return
        cls.delivered=False
        cls.rom=(grain.ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        cls.exports=dict(zip(grain.HELPERS,(0x541b0000,0x541b0200)))
        options={'appended_slots':True} if 'appended_slots' in inspect.signature(grain.build).parameters else {}
        with tempfile.TemporaryDirectory() as d:cls.code,cls.manifest=grain.build(d,0x541a0000,cls.exports,cls.rom,**options)
    def fixture(self):
        return grain.StockISP(self.rom) if self.delivered else grain.NativeGrainHookTests.fixture(self)
    init=grain.NativeGrainHookTests.init
    run_at=grain.NativeGrainHookTests.run_at
    snapshot=grain.NativeGrainHookTests.snapshot

    def test_only_new_film_tones_force_grain_traversal_without_changing_arm_state(self):
        for tone in (0,11,12,18,19,20,21,22,24,25,26,27,28,29,30,255):
            e=self.fixture();request=e.alloc(64);si=e.alloc(0x800)
            e.u.mem_write(request,bytes([0x5a])*64);e.u.mem_write(si+0x77c,bytes([tone]))
            self.init(e,[]);e.u.reg_write(grain.A.UC_ARM_REG_R4,request);e.u.reg_write(grain.A.UC_ARM_REG_R5,si)
            before=self.snapshot(e);self.run_at(e,0x53513620)
            self.assertEqual(self.snapshot(e),before)
            expected=bytearray([0x5a]*64)
            if tone in (25,26,27,28,29):expected[0x24]=1
            self.assertEqual(bytes(e.u.mem_read(request,64)),bytes(expected))

if __name__=='__main__':unittest.main()
