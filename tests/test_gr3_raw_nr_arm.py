"""Execute official GR III RAW NR instructions and planned replacements (offline)."""
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_CPSR

ROOT=Path(__file__).resolve().parents[1]

class RawNrArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script="""import {readFileSync} from 'node:fs';import {officialResources} from './node/gr3-stock-presets.mjs';import {planRawNr} from './node/gr3-raw-nr.mjs';const b=readFileSync('bin/fwdc239b-gr3-official.bin'),{decoded,sections}=officialResources(b),r=decoded.subarray(sections.RTOS.offset);console.log(JSON.stringify(planRawNr(b,{mode:'off'}).map(p=>({...p,stock:r.subarray(p.offset,p.offset+4).toString('hex')}))));"""
        cls.edits=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT))

    def instruction(self,code,zero,register,value):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x1000);u.mem_write(0x1000,code)
        u.reg_write(UC_ARM_REG_CPSR,0x10|(int(zero)<<30));u.reg_write(register,value)
        u.emu_start(0x1000,0x1004,count=1)
        return u

    def test_still_unit_and_parameter_flags_become_zero_for_all_debug_states(self):
        for edit,register in zip(self.edits[:2],[UC_ARM_REG_R6,UC_ARM_REG_R7]):
            self.assertEqual(edit['stock'],edit['expectedHex'])
            for zero in [False,True]:
                for value in [0,1]:
                    with self.subTest(address=hex(edit['offset']+0x53000000),debug_zero=zero,initial=value):
                        stock=self.instruction(bytes.fromhex(edit['stock']),zero,register,value)
                        self.assertEqual(stock.reg_read(register),value^1 if zero else value)
                        patched=self.instruction(bytes.fromhex(edit['replacementHex']),zero,register,value)
                        self.assertEqual(patched.reg_read(register),0)

    def test_alternate_capture_mask_clears_only_nr_bit_and_preserves_condition(self):
        edit=self.edits[2];self.assertEqual(edit['stock'],edit['expectedHex'])
        for zero in [False,True]:
            for base_mask in [1,3]:
                u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x1000)
                u.mem_write(0x1000,bytes.fromhex(edit['replacementHex']))
                u.reg_write(UC_ARM_REG_CPSR,0x10|(int(zero)<<30));u.reg_write(UC_ARM_REG_R3,base_mask);u.reg_write(UC_ARM_REG_R4,0x11)
                u.emu_start(0x1000,0x1004,count=1)
                self.assertEqual(u.reg_read(UC_ARM_REG_R4),0x11 if zero else base_mask|0x10)
                self.assertEqual(u.reg_read(UC_ARM_REG_R4)&8,0)

if __name__=='__main__':unittest.main()
