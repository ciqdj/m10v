"""Execute appended slots and stock preservation against the linked candidate.

Expected tone/index values come from the official order, not the new mapper.
OS notification and filesystem boundaries are substituted; stock setters,
enumeration, detail lookup and the M10V journal code execute on ARM.
"""
import inspect
import os
import hashlib
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from scripts.build_gr3_m10v_library import build
from scripts.analyze_gr3_device_regression import machine, run
from tests import test_gr3_m10v_library_arm as arm_fixture

ROOT = Path(__file__).resolve().parents[1]


class AppendedSlotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        artifact=os.environ.get('M10V_APPENDED_CANDIDATE')
        if artifact:
            folder=Path(artifact);cls.manifest=json.loads((folder/'gr3/manifest.json').read_text())
            cls.code=(folder/'evidence/runtime.bin').read_bytes()
            receipt=json.loads((folder/'gr3/receipt.json').read_text())
            assert hashlib.sha256((folder/'gr3/fwdc239b.bin').read_bytes()).hexdigest()==receipt['candidate_sha256']
            assert hashlib.sha256(cls.code).hexdigest()==cls.manifest['code_sha256']
        else:
            cls.manifest = build(cls.tmp.name, sd_library=True, appended_slots=True)
            cls.code = (Path(cls.tmp.name) / 'm10v-library-arm.bin').read_bytes()
        script = """
import {readFileSync,writeFileSync} from 'node:fs';
import {buildNativeLibrary} from './node/gr3-m10v-native-build.mjs';
import {officialResources} from './node/gr3-stock-presets.mjs';
import {decodeFrameMap} from './node/gr3-frames.mjs';
const p=process.argv[1],s=readFileSync('bin/fwdc239b-gr3-official.bin');
const r=process.argv[2]?{candidate:readFileSync(process.argv[2]+'/gr3/fwdc239b.bin'),receipt:JSON.parse(readFileSync(process.argv[2]+'/gr3/receipt.json'))}:buildNativeLibrary(s,readFileSync(p+'/m10v-library-arm.bin'),JSON.parse(readFileSync(p+'/m10v-library-arm.json')));
const {decoded:d}=decodeFrameMap(r.candidate,r.candidate.readUInt32LE(r.candidate.length-8));
const {sections}=officialResources(s);const a=sections.RTOS.offset;
writeFileSync(p+'/rtos.bin',d.subarray(a,a+sections.RTOS.size+r.receipt.rtos_growth));
"""
        subprocess.run(['node', '--input-type=module', '-e', script, cls.tmp.name,artifact or ''], cwd=ROOT, check=True)
        cls.rom = (Path(cls.tmp.name) / 'rtos.bin').read_bytes()
        at=cls.manifest['base']-0x53000000
        assert cls.rom[at:at+len(cls.code)]==cls.code

    def global_call(self, address, *args, context=0, bank=0):
        u = machine(self.rom)
        u.mem_write(0x55068200 + 0x1b, bytes([context]))
        def services(uc, a, size, data):
            if a == 0x532bd6d4: value = bank
            elif a == 0x5320ad88: value = 0x55006000
            elif a == 0x5320b7fc: value = 0x55007000
            elif a == 0x536b93d0:
                self.assertNotEqual(uc.reg_read(UC_ARM_REG_R0), 0, 'stock assertion rejected an appended slot')
                value = 0
            else: return
            uc.reg_write(UC_ARM_REG_R0, value)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, services)
        for r, v in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args): u.reg_write(r, v)
        return run(u, address)

    def test_menu_and_adj_append_five_after_all_twelve_stock_choices_in_every_bank(self):
        expected = [11,12,13,14,15,16,22,17,18,19,20,21,25,26,27,28,29]
        for bank in range(3):
            self.assertEqual(self.global_call(0x532c2a9c, 0x55068200, bank=bank), 17)
            for index, tone in enumerate(expected):
                self.assertEqual(self.global_call(0x532c2c80, 0x55068200, index, bank=bank), tone)
                self.assertEqual(self.global_call(0x532c2f08, 0x55068200, tone, bank=bank), index)

    def test_movie_and_raw_development_do_not_gain_unimplemented_private_choices(self):
        for context, count in ((1,10),(2,12)):
            for bank in range(3):
                self.assertEqual(self.global_call(0x532c2a9c, 0x55068200, context=context, bank=bank), count)

    machine = arm_fixture.FilmLibraryArmTests.machine
    call = arm_fixture.FilmLibraryArmTests.call

    def test_original_presets_do_not_resolve_to_m10v_names_or_icons(self):
        u = self.machine()
        for tone in (12,18,19,20,21):
            self.forwarded.clear()
            self.call(u, 'm10v_menu_name', 0, tone)
            self.assertIn(0x10, self.forwarded)
            self.forwarded.clear()
            self.call(u, 'm10v_menu_icon', 0, tone)
            self.assertIn(0x30, self.forwarded)

    def test_visible_menu_keeps_custom_one_and_two_before_the_five_films(self):
        u=self.machine()
        self.assertEqual(self.call(u,'m10v_menu_count',0x55068200)+2,20)
        self.assertEqual([self.call(u,'m10v_menu_index',0x55068200,i) for i in range(12,20)],
                         [23,24,25,26,27,28,29,128])

    def test_real_adj_callback_maps_visible_rows_to_the_correct_tone_or_custom_bank(self):
        for row, wanted_tone, wanted_bank in ((1,12,0),(12,None,1),(13,None,2),
                (14,25,0),(15,26,0),(16,27,0),(17,28,0),(18,29,0)):
            u=machine(self.rom);tones=[];banks=[]
            u.mem_write(0x55006004,struct.pack('<I',0x55007000))
            u.mem_write(0x550071c2,b'\x12')
            def services(uc,a,n,data):
                if a==0x5320ad88:value=0x55006000
                elif a==0x5320ba9c:value=0x55068200
                elif a==0x5320b31c:value=0x55006000
                elif a==0x532c26c0:tones.append(uc.reg_read(UC_ARM_REG_R1));return
                elif a==0x532750f8:value=0
                elif a==0x532bd6b4:value=21
                elif a==0x532bd6d4:value=0
                elif a==0x532bd61c:banks.append(uc.reg_read(UC_ARM_REG_R1));value=0
                else:return
                uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE,services)
            u.reg_write(UC_ARM_REG_R0,0x55005000);u.reg_write(UC_ARM_REG_R1,row)
            run(u,0x531a0ba0)
            self.assertEqual(tones,[] if wanted_tone is None else [wanted_tone])
            self.assertEqual(banks,[wanted_bank])
            self.assertEqual(bytes(u.mem_read(0x550071c2,1)),b'\x12' if wanted_tone is None else bytes([wanted_tone]))

    def test_menu_and_adj_selection_marks_follow_custom_banks_and_all_five_films(self):
        for bank in range(3):
            for row in range(20):
                actual=self.global_call(self.manifest['symbols']['m10v_tone_menu_menu_matches'],0,27,row,bank)
                self.assertEqual(actual,int(row==({0:16,1:12,2:13}[bank])))

    def test_new_slots_reuse_existing_journal_without_exposing_stock_parameter_writes(self):
        u = self.machine()
        for slot, tone in enumerate((25,26,27,28,29)):
            ui = 0x55007000
            for bank in range(3):
                u.mem_write(ui+0x198, bytes([tone,bank,12+slot,0,0,0,0,0]))
                table = self.call(u, 'm10v_detail_table', ui)
                self.assertNotEqual(table, 0x53b3488c)
                pointer, count = struct.unpack('<II', u.mem_read(table+(bank*12+12+slot)*8,8))
                entries = bytes(u.mem_read(pointer,count*2))
                self.assertTrue(count)
                self.assertTrue(all(v>=18 for v in entries[1::2]))
                self.assertEqual(self.call(u,'m10v_detail_control',2,ui,(3<<8)|3),1)
                self.assertEqual(self.call(u,'m10v_detail_control',1,ui,3),3)

    def test_ab_selector_can_pair_a_factory_preset_with_an_appended_film(self):
        source=Path(self.tmp.name)/'ab.c'
        source.write_text('#define M10V_APPENDED_SLOTS 1\n#include "m10v_ab.h"\n'
            'int main(void){m10v_ab a={0};'
            'if(m10v_ab_tone(1)!=12||m10v_ab_slot(1)!=5)return 1;'
            'if(m10v_ab_tone(12)!=25||m10v_ab_tone(16)!=29)return 2;'
            'if(m10v_ab_slot(12)!=0||m10v_ab_slot(16)!=4)return 3;'
            'if(m10v_ab_start(&a,1,16,1,0,33))return 4;'
            'return m10v_ab_key(&a,0x37,1)==17?0:5;}')
        program=Path(self.tmp.name)/'ab'
        subprocess.run(['cc','-I',str(ROOT/'native/gr3'),str(source),'-o',str(program)],check=True)
        self.assertEqual(subprocess.run([str(program)]).returncode,0)


if __name__ == '__main__': unittest.main()
