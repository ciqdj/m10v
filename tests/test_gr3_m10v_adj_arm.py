"""Execute genuine stock ADJ callback/count/index/setter against current build.
Only model services and hardware apply-all are substituted, never tone writes.
"""
import json
import os
import hashlib
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from scripts.build_gr3_m10v_library import build
from scripts.analyze_gr3_device_regression import machine, run
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT/'bin/fwdc239b-gr3-official.bin'

@unittest.skipUnless(OFFICIAL.exists(), 'official firmware unavailable')
class AdjArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        artifact = os.environ.get('M10V_TEST_FIRMWARE_DIR')
        cls.artifact = Path(artifact).resolve() if artifact else None
        cls.manifest = (json.loads((cls.artifact/'evidence/M10V-runtime-manifest.json').read_text())
                        if cls.artifact else build(cls.folder.name))
        script = """
import {readFileSync,writeFileSync} from 'node:fs';
import {buildNativeLibrary} from './node/gr3-m10v-native-build.mjs';
import {decodeFrameMap} from './node/gr3-frames.mjs';
const dir=process.argv[1], source=readFileSync('bin/fwdc239b-gr3-official.bin');
const candidate=process.argv[2]?readFileSync(process.argv[2]+'/fw/fwdc239b.bin'):buildNativeLibrary(source,readFileSync(dir+'/m10v-library-arm.bin'),JSON.parse(readFileSync(dir+'/m10v-library-arm.json'))).candidate;
const stock=decodeFrameMap(source).decoded;
let stockAt=0; while(stock.toString('ascii',stockAt,stockAt+4)!=='RTOS')stockAt+=16+stock.readUInt32LE(stockAt+12);
writeFileSync(dir+'/official-rtos.bin',stock.subarray(stockAt+16,stockAt+16+stock.readUInt32LE(stockAt+12)));
const d=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
let at=0; while(d.toString('ascii',at,at+4)!=='RTOS')at+=16+d.readUInt32LE(at+12);
writeFileSync(dir+'/rtos.bin',d.subarray(at+16,at+16+d.readUInt32LE(at+12)));
"""
        subprocess.run(['node','--input-type=module','-e',script,cls.folder.name,str(cls.artifact) if cls.artifact else ''],cwd=ROOT,check=True)
        cls.code = (Path(cls.folder.name)/'rtos.bin').read_bytes()
        cls.stock = (Path(cls.folder.name)/'official-rtos.bin').read_bytes()
        if cls.artifact:
            runtime=(cls.artifact/'evidence/M10V-runtime-arm.bin').read_bytes()
            if hashlib.sha256(runtime).hexdigest()!=cls.manifest['code_sha256']:
                raise AssertionError('artifact runtime hash differs from evidence manifest')
            at=cls.manifest['base']-0x53000000
            if cls.code[at:at+len(runtime)]!=runtime:
                raise AssertionError('final firmware runtime differs from evidence module')

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()

    def probe(self, index, group=0):
        u = machine(self.code)
        u.mem_write(0x55068200, bytes([18])+bytes(28)+bytes([group])+bytes(2))
        u.mem_write(0x55006004, struct.pack('<I',0x55007000))
        u.mem_write(0x550071c2,b'\x12')
        writes,backs=[],[]
        def services(uc,a,n,data):
            if a==0x5320ad88:result=0x55006000
            elif a==0x5320ba9c:result=0x55068200
            elif a==0x5320b31c:result=0x55006000
            elif a==0x532c26c0:
                writes.append(uc.reg_read(UC_ARM_REG_R1));return
            elif a==0x532750f8:result=0
            elif a==0x532bd6b4:result=21
            elif a==0x532bd6d4:result=0
            elif a==0x532bd61c:backs.append(uc.reg_read(UC_ARM_REG_R1));result=0
            else:return
            uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,services)
        u.reg_write(UC_ARM_REG_R0,0x55005000);u.reg_write(UC_ARM_REG_R1,index)
        run(u,0x531a0ba0)
        return writes,backs,bytes(u.mem_read(0x550071c2,1))[0]

    def test_adj_tail_and_reverse_browsing_never_commit_private_id(self):
        for group in range(15):
            for index in (11,12,13,12,11,0):
                with self.subTest(group=group,index=index):
                    writes,backs,tone=self.probe(index,group)
                    self.assertTrue(all(11<=v<=22 for v in writes), writes)
                    self.assertLess(tone,128)
                    if index==12:self.assertEqual((writes,backs,tone),([],[1],18))

    def test_detail_callback_uses_stock_table_even_with_stale_library_mode(self):
        for group in range(15):
            u=machine(self.code)
            def state_service(uc,address,size,data):
                if address==0x532bd6d4:
                    uc.reg_write(UC_ARM_REG_R0,0)
                    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE,state_service)
            u.mem_write(0x55068200,bytes([18])+bytes(28)+bytes([group])+bytes(2))
            u.reg_write(UC_ARM_REG_R0,0x55068200)
            self.assertEqual(run(u,0x532c2a9c),12)
            for index,expected in enumerate((11,12,13,14,15,16,22,17,18,19,20,21)):
                # Execute the actual detail callback BL and its shared index
                # helper, stopping before the downstream detail-table consumer.
                u.reg_write(UC_ARM_REG_R0,0x55068200)
                u.reg_write(UC_ARM_REG_R1,index)
                u.emu_start(0x531b0ce0,0x531b0cec,count=10000)
                self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x531b0cec)
                self.assertEqual(u.reg_read(UC_ARM_REG_R1),expected)

    def test_global_model_api_is_stock_in_every_private_page(self):
        stock=self.stock
        # Includes detail callback and generic forwarding consumer: private
        # list context must never change these shared APIs or their consumers.
        for address in (0x532c2a9c,0x532c2b7c,0x532c2c80,0x531b0ce0,
                        0x531aeb08,0x531aec60,0x53283ca4):
            off=address-0x53000000
            self.assertEqual(self.code[off:off+4],stock[off:off+4],hex(address))

# Reuse the genuine view/std::function/controller fixture, replacing historical
# fixed binary with a freshly compiled and packaged current-source candidate.
from tests import test_gr3_m10v_redraw_arm as redraw

@unittest.skipUnless(OFFICIAL.exists(), 'official firmware unavailable')
class CurrentMenuArmTests(redraw.FixedNativeRedrawArmTests):
    # This subclass builds its own candidate; historical decoded fixtures are
    # not required. Override the base class's inherited skip marker.
    __unittest_skip__ = not OFFICIAL.exists()
    __unittest_skip_why__ = 'official firmware unavailable'
    visible_film_count = 47
    choose_slot_index = 3
    slot_five_film_index = 0
    slot_one_film_index = 15

    def test_reopening_legacy_stock_focuses_its_actual_row_after_curated_stocks(self):
        self.call('m10v_library_init',0x55009000)
        initial=bytes(self.u.mem_read(0x55009000,104))
        for film,want in [(34,15),(50,31),(65,46)]:
            with self.subTest(film=film):
                payload=bytearray(initial);struct.pack_into('<H',payload,20,film)
                struct.pack_into('<I',payload,100,zlib.crc32(payload[:100]))
                self.files={'M10V5B.bin':bytes(payload)}
                self.u.mem_write(redraw.MODEL+0x1d,b'\x01')
                self.call(0x531ac074,redraw.CONTROLLER)
                self.focus(0);self.call('m10v_menu_confirm',redraw.CONTROLLER)
                self.assertEqual(self.call(0x53394820,redraw.VIEW),want)

    def test_curated_first_and_last_rows_confirm_into_real_stock_slot(self):
        for index,film,tone in ((0,33,213),(1,66,288),(2,67,289),(3,68,290),(4,69,344),(13,78,353),(14,289,354),(15,34,256),(46,65,287)):
            with self.subTest(index=index):
                self.files.clear()
                self.u.mem_write(redraw.MODEL+0x1d,b'\x01')
                self.call(0x531ac074,redraw.CONTROLLER)
                self.focus(0);self.call('m10v_menu_confirm',redraw.CONTROLLER)
                self.assertEqual(self.call('m10v_menu_index',redraw.MODEL,index),tone)
                self.focus(index)
                self.assertFalse(self.files)
                self.assertLess(self.tone,128)
                self.call('m10v_menu_confirm',redraw.CONTROLLER)
                payload=self.files['M10V5B.bin']
                self.assertEqual(struct.unpack_from('<H',payload,20)[0],film)
                self.assertEqual(self.tone,18)
                self.assertEqual(self.u.mem_read(redraw.MODEL+0x1d,1),b'\x01')

    def test_hidden_old_ids_focus_800t_without_rewriting_valid_journal(self):
        self.call('m10v_library_init',0x55009000)
        initial=bytes(self.u.mem_read(0x55009000,104))
        for film in range(1,66):
            with self.subTest(film=film):
                payload=bytearray(initial)
                struct.pack_into('<H',payload,20,film)
                struct.pack_into('<I',payload,100,zlib.crc32(payload[:100]))
                self.files={'M10V5B.bin':bytes(payload)}
                before=dict(self.files)
                self.u.mem_write(redraw.MODEL+0x1d,b'\x01')
                self.call(0x531ac074,redraw.CONTROLLER)
                self.focus(0);self.call('m10v_menu_confirm',redraw.CONTROLLER)
                self.assertEqual(self.call(0x53394820,redraw.VIEW),film-19 if film>=34 else 0)
                self.assertEqual(self.files,before)
                self.assertEqual(self.tone,18)

    def boundaries(self,u,address,size,data):
        if address==0x535847d8:
            # The optional SD diagnostic channel has no device manager in this
            # view fixture. Execute logger itself; substitute only this leaf.
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().boundaries(u,address,size,data)

    @classmethod
    def setUpClass(cls):
        AdjArmTests.setUpClass.__func__(cls)
        cls.firmware = cls.code

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()
