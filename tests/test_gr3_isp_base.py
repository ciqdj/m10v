"""Execute stock ISP Make, not a substitute implementation of the color path.

ROM/RAM anchors and constructor fixture independently cross-checked against
local gr3-film-mods/run_tuning.py and emu.py reverse-engineering experiments.
Stage1 (still) executes all stock main/sub-Make instructions, substituting OS
allocation/assertions, two OS helpers and SVC returns. Stage0 scope checks use
nine explicit sub-Make boundaries because its device services are unavailable.
Neither fixture executes ISP hardware.
"""
import os
import struct
import subprocess
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UcError
from unicorn import arm_const as A
from scripts.build_gr3_menu_patches import branch

ROOT=Path(__file__).resolve().parents[1]
BASE=0x53000000
CARRIERS=(12,18,19,20,21)
DEFAULTS={**{o:4 for o in (0x77d,0x77e,0x77f,0x780,0x781,0x782,0x784,0x787,0x792,0x793,0x794)},0x783:1,0x786:1,0x798:1}

class StockISP:
    def __init__(self, rom):
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        u.mem_map(BASE,(len(rom)+65535)&~65535);u.mem_write(BASE,bytes(rom))
        u.mem_map(0x55000000,0x1000000)
        u.mem_write(0x55000000,bytes(rom[0x107b540:0x107b540+0x3a080]))
        u.mem_map(0x60000000,0x4000000);u.mem_map(0x5ef00000,0x100000);u.mem_map(0x5e000000,4096)
        u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
        self.cursor=0x60000000;self.assertions=[]
        self.services={0x536b82d4,0x5313fbb8}
        u.hook_add(UC_HOOK_CODE,self.service)
        u.hook_add(UC_HOOK_INTR,lambda u,n,d:u.reg_write(A.UC_ARM_REG_R0,0))
    def alloc(self,n):
        at=self.cursor;self.cursor=(at+n+63)&~63;return at
    def w32(self,at,v):self.u.mem_write(at,struct.pack('<I',v))
    def service(self,u,at,size,data):
        if at in (0x536af2a8,0x536af31c):u.reg_write(A.UC_ARM_REG_R0,self.alloc(u.reg_read(A.UC_ARM_REG_R0)))
        elif at==0x536b93d0:
            if not u.reg_read(A.UC_ARM_REG_R0):self.assertions.append(u.reg_read(A.UC_ARM_REG_LR))
            u.reg_write(A.UC_ARM_REG_R0,0)
        elif at in self.services or at in (0x536af2e4,0x536af358):u.reg_write(A.UC_ARM_REG_R0,0)
        else:return
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
    def call(self,at,*args):
        u=self.u
        for r in range(13):u.reg_write(getattr(A,f'UC_ARM_REG_R{r}'),args[r] if r<len(args) else 0)
        u.reg_write(A.UC_ARM_REG_CPSR,0x13);u.reg_write(A.UC_ARM_REG_SP,0x5effff00);u.reg_write(A.UC_ARM_REG_LR,0x5e000000)
        try:u.emu_start(at,0x5e000000,count=5000000)
        except UcError as error:raise AssertionError(f"{error} PC={u.reg_read(A.UC_ARM_REG_PC):#x} LR={u.reg_read(A.UC_ARM_REG_LR):#x}") from error
        if u.reg_read(A.UC_ARM_REG_PC)!=0x5e000000:raise AssertionError('ISP did not return')
    def make(self,tone,stage=1,live=False,extra=None,actual_live=False):
        if stage==0:
            self.services.update((0x536decb4,0x536e4634,0x536e4de4,0x536e5070,0x536e7348,0x536eaf80,0x536ec3e0,0x536eb0b0,0x536e9d1c))
        o=self.alloc(0x400);cfg=self.alloc(0x1000);i=self.alloc(0x9000);s=self.alloc(0x80000)
        self.w32(o,0x53dbd8a0)
        self.call(0x536da1fc,o,cfg);self.call(0x536da62c,o,cfg)
        self.w32(o,0x53dbd938 if live else 0x53dbd8a0)
        self.u.mem_write(i+0x82ac,bytes([stage]));self.w32(i+0x82d0,s)
        st=s+(0x71248 if stage else 0)
        for off,v in {**DEFAULTS,**(extra or {}),0x77c:tone}.items():self.u.mem_write(st+off,bytes([v]))
        # Still Make exercises the same shared helpers with either object
        # identity; this is a gate regression, not a LiveView hardware fixture.
        self.call(0x536ddecc if actual_live else 0x536dd8f0,o,i)
        self.object=bytes(self.u.mem_read(o,0x400))
        return bytes(self.u.mem_read(i,0x9000)),bytes(self.u.mem_read(s,0x80000)),st

class ISPBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js="import {readFileSync} from 'node:fs';import {officialResources} from './node/gr3-stock-presets.mjs';const {decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.RTOS.offset,s.RTOS.offset+s.RTOS.size));"
        cls.rom=subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT)
    def patched(self):
        candidate=os.environ.get('M10V_ISP_BIN')
        if candidate:
            if not hasattr(self.__class__,'candidate_rom'):
                js="import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
                self.__class__.candidate_rom=subprocess.check_output(['node','--input-type=module','-e',js,candidate],cwd=ROOT)
            return self.candidate_rom
        if hasattr(self.__class__,'patched_rom'):return self.patched_rom
        if os.environ.get('M10V_ISP_STOCK'):return self.rom
        from scripts.build_gr3_isp_base import build_isp_base
        code,report=build_isp_base(0x540b6000)
        rom=bytearray(self.rom);rom+=bytes(0x10b6000+len(code)-len(rom));rom[0x10b6000:]=code
        for p in report['patches']:
            self.assertEqual(struct.unpack_from('<I',rom,p['address']-BASE)[0],p['expected'])
            struct.pack_into('<I',rom,p['address']-BASE,branch(p['address'],p['entry']))
        self.__class__.patched_rom=bytes(rom)
        return self.patched_rom
    def test_still_carriers_use_standard_isp_and_keep_shooting_tone(self):
        rom=self.patched()
        # Compare outputs at identical addresses, including in-place R2Y writes.
        for stage in (0,1):
            for extra in ({},{0x77d:1,0x77e:7,0x780:2,0x793:6,0x794:2,0x795:3,0x796:8,0x797:3}):
                ref=StockISP(self.rom);ri,rs,st=ref.make(11,stage,extra=extra)
                self.assertEqual(ref.assertions,[])
                for tone in CARRIERS:
                    with self.subTest(stage=stage,tone=tone,extra=extra):
                        e=StockISP(rom);out,si,at=e.make(tone,stage,extra=extra)
                        self.assertEqual(e.assertions,[]);self.assertEqual(out,ri)
                        self.assertEqual(e.object,ref.object)
                        # Only the original identity byte is intentionally different.
                        si=bytearray(si);self.assertEqual(e.u.mem_read(at+0x77c,1)[0],tone)
                        si[(0x71248 if stage else 0)+0x77c]=11
                        self.assertEqual(si,rs)
    def test_noncarriers_and_liveview_object_shared_helpers_remain_stock(self):
        rom=self.patched()
        for live,tones in ((False,(11,13,17,22)),):
            for tone in tones:
                with self.subTest(live=live,tone=tone):
                    r=StockISP(self.rom);a,b,_=r.make(tone,0 if live else 1,live)
                    e=StockISP(rom);c,d,_=e.make(tone,0 if live else 1,live)
                    self.assertEqual(r.assertions,[]);self.assertEqual(e.assertions,[])
                    self.assertEqual(c,a);self.assertEqual(d,b)

    def test_real_live_make_carriers_use_standard_color_parameters(self):
        # Real LiveView Make with capture-shaped stage1 metadata: stage0 needs
        # device-specific black-level/AWB calibration, not emulated here.
        rom=self.patched()
        for extra in ({},{0x77d:1,0x77e:7,0x780:2,0x793:6,0x794:2,0x795:3,0x796:8,0x797:3}):
            r=StockISP(self.rom);ref,si,_=r.make(11,1,True,extra,actual_live=True)
            self.assertEqual(r.assertions,[])
            for tone in CARRIERS:
                with self.subTest(tone=tone,extra=extra):
                    e=StockISP(rom);out,state,at=e.make(tone,1,True,extra,actual_live=True)
                    self.assertEqual(e.assertions,[]);self.assertEqual(out,ref)
                    state=bytearray(state);self.assertEqual(e.u.mem_read(at+0x77c,1)[0],tone)
                    state[0x71248+0x77c]=11;self.assertEqual(state,si)
                    obj=bytearray(e.object);self.assertEqual(obj[0x1a8],tone)
                    obj[0x1a8]=11;self.assertEqual(obj,r.object)

    def test_still_plan_local_process_uses_standard_and_other_callers_stay_stock(self):
        for values in ({0x793:4,0x794:4,0x796:3},{0x793:7,0x794:4,0x796:0}):
            def run(rom,tone,caller=True):
                e=StockISP(rom);cfg=e.alloc(0x100);si=e.alloc(0x1000)
                for off,value in {**values,0x77c:tone}.items():e.u.mem_write(si+off,bytes([value]))
                if caller:
                    e.u.reg_write(A.UC_ARM_REG_R0,cfg);e.u.reg_write(A.UC_ARM_REG_R1,si)
                    e.u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
                    e.u.emu_start(0x5351361c,0x53513620,count=10000)
                    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_PC),0x53513620)
                else:e.call(0x535131c0,cfg,si)
                self.assertEqual(e.u.mem_read(si+0x77c,1)[0],tone)
                return bytes(e.u.mem_read(cfg,0x100))
            standard=run(self.rom,11)
            for tone in CARRIERS:
                self.assertEqual(run(self.patched(),tone),standard)
                self.assertEqual(run(self.patched(),tone,False),run(self.rom,tone,False))
            for tone in (11,13,17,22):self.assertEqual(run(self.patched(),tone),run(self.rom,tone))

    def test_displaced_load_preserves_other_registers_and_condition_flags(self):
        from scripts.build_gr3_isp_base import HOOKS
        rom=self.patched()
        for address,word,result,_,name in HOOKS:
            for flags in (0x13,0xa80f0013,0x58000013):
                for live in (False,True,None):
                    for tone in (11,12,18,21,22,255):
                        e=StockISP(rom);o=e.alloc(0x400);si=e.alloc(0x1000);u=e.u
                        e.w32(o,0x53dbd940 if live is None else 0x53dbd938 if live else 0x53dbd8a0);u.mem_write(si+0x77c,bytes([tone]))
                        for r in range(13):u.reg_write(getattr(A,f'UC_ARM_REG_R{r}'),0x1000+r)
                        # Original live registers at each exact load instruction.
                        for reg,value in ({0:o,3:si} if name=='parameters' else {6:o,7:si} if name in ('color_table','color_flags') else {4:o+0x1e0,7:si} if name=='curve' else {1:si}).items():u.reg_write(getattr(A,f'UC_ARM_REG_R{reg}'),value)
                        u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
                        u.reg_write(A.UC_ARM_REG_LR,0x5e000000 if live is not False else 0x53513620)
                        u.reg_write(A.UC_ARM_REG_CPSR,flags)
                        registers=[getattr(A,f'UC_ARM_REG_R{r}') for r in range(13)]+[A.UC_ARM_REG_SP,A.UC_ARM_REG_LR,A.UC_ARM_REG_CPSR]
                        expected=[u.reg_read(r) for r in registers]
                        expected[result]=11 if live is not None and tone in CARRIERS and (name!='local_process' or not live) else tone
                        u.emu_start(address,address+4,count=1000)
                        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),address+4)
                        self.assertEqual([u.reg_read(r) for r in registers],expected,(name,flags,live,tone))
                        self.assertEqual(u.mem_read(si+0x77c,1)[0],tone)
