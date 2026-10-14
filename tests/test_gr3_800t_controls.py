"""Execute stock/patched ARM pass-through; slider state must not change."""
import json,os,struct,unittest,hashlib
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_PC
from scripts.analyze_gr3_800t_mapping import RTOS_SHA256
ROOT=Path(__file__).resolve().parents[1]

class CameraControlPipelineTests(unittest.TestCase):
    def run_pipeline(self,tone=18,stage=0,patched=True):
        path=Path(os.environ.get('GR3_RTOS_PATH','/tmp/m10v-800t-analysis/rtos.bin'))
        if not path.exists():self.skipTest('locked original RTOS required')
        original=path.read_bytes();self.assertEqual(hashlib.sha256(original).hexdigest(),RTOS_SHA256)
        rtos=bytearray(original)
        if patched:
            contract=json.loads((ROOT/'node/gr3-800t-controls.json').read_text())
            for patch in contract['pipelinePatches']:
                at=patch['address']-0x53000000
                self.assertEqual(rtos[at:at+4].hex(),patch['expected'])
                rtos[at:at+4]=bytes.fromhex(patch['replacement'])
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        u.mem_map(0x53000000,(len(rtos)+4095)&~4095);u.mem_write(0x53000000,bytes(rtos))
        u.mem_map(0x55000000,0x100000);u.mem_map(0x56000000,4096);u.mem_map(0x58000000,65536)
        info=0x55001000;si=0x55002000+(0x71248 if stage else 0)
        u.mem_write(info+0x2ac,bytes((stage,)));u.mem_write(info+0x2d0,struct.pack('<I',0x55002000))
        state=bytearray(0x800);state[0x77c]=tone
        for off,value in ((0x77d,8),(0x77e,1),(0x77f,6),(0x780,3),(0x781,7),
                          (0x782,2),(0x784,5),(0x793,4),(0x794,4)):
            state[off]=value
        u.mem_write(si,bytes(state))
        u.reg_write(UC_ARM_REG_R0,0x56000000);u.reg_write(UC_ARM_REG_R1,info)
        u.reg_write(UC_ARM_REG_SP,0x5800fff0);u.reg_write(UC_ARM_REG_LR,0x53000000)
        u.emu_start(0x536db7dc,0x53000000,count=2000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x53000000)
        return bytes(u.mem_read(0x56000000,0x200)),bytes(u.mem_read(si,0x800)),bytes(state)

    def test_bleach_pipeline_keeps_original_color_sliders_and_state(self):
        patched=os.environ.get('M10V_TEST_STOCK_CONTROLS')!='1'
        for stage in (0,1):
            output,after,before=self.run_pipeline(stage=stage,patched=patched)
            for off,value in zip((0x1e0,0x1e2,0x1e4,0x1e8,0x1ee),(8,1,6,7,5)):
                self.assertEqual(struct.unpack_from('<H',output,off)[0],value)
            for off in (0x77d,0x77e,0x77f,0x781,0x784):self.assertEqual(after[off],before[off])
            self.assertEqual(struct.unpack_from('<H',output,0x1e6)[0],3)
            self.assertEqual(struct.unpack_from('<H',output,0x1ea)[0],2)

    def test_other_tones_keep_stock_pipeline_behavior(self):
        for tone in (11,12,13,14,15,16,17,19,20,21,22):
            for stage in (0,1):
                self.assertEqual(self.run_pipeline(tone,stage,True)[:2],self.run_pipeline(tone,stage,False)[:2])
