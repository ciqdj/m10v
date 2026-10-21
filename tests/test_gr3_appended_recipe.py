"""New tone identities through the genuine stock Still Make callback."""
import tempfile
import os,json,subprocess
from pathlib import Path
import unittest
from tests import test_gr3_native_recipe_handoff as native
from scripts.build_gr3_isp_recipe_color import build


class AppendedRecipeTests(unittest.TestCase):
    fixture=native.NativeRecipeHandoffTests.fixture
    snapshot=native.NativeRecipeHandoffTests.snapshot
    callback=native.NativeRecipeHandoffTests.callback
    status=native.NativeRecipeHandoffTests.status

    @classmethod
    def setUpClass(cls):
        cls.rom=(native.ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        artifact=os.environ.get('M10V_APPENDED_CANDIDATE')
        if artifact:
            full=json.loads((Path(artifact)/'gr3/manifest.json').read_text());cls.manifest=full['capture_lifecycle']['snapshot']
            script="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
            cls.candidate=subprocess.check_output(['node','--input-type=module','-e',script,str(Path(artifact)/'gr3/fwdc239b.bin')],cwd=native.ROOT)
            return
        with tempfile.TemporaryDirectory() as d:
            cls.libbase,cls.libcode,cls.libsymbols=native.library_fragment(d)
            owner={'storage':{'color_offset':0x4a08,'color_bytes':1716,'extended_recipe_bytes':0x50f0},
                   'patches':[{'address':0x53523e0c}]}
            cls.code,cls.manifest=build(d,cls.rom,cls.libsymbols,owner,observer=False,
                                      native_color=True,appended_slots=True)
        candidate=bytearray(cls.rom)
        from scripts.build_gr3_isp_base import build_isp_base
        from scripts.build_gr3_menu_patches import branch
        import struct
        base_code,base_report=build_isp_base(0x54140000,appended_slots=True)
        candidate.extend(bytes(0x1140000+len(base_code)-len(candidate)))
        candidate[0x1140000:0x1140000+len(base_code)]=base_code
        for p in base_report['patches']:struct.pack_into('<I',candidate,p['address']-native.BASE,branch(p['address'],p['entry']))
        for at,code in ((cls.libbase,cls.libcode),(cls.manifest['base'],cls.code)):
            end=at-native.BASE+len(code)
            if end>len(candidate):candidate.extend(bytes(end-len(candidate)))
            candidate[at-native.BASE:end]=code
        for p in cls.manifest['patches']:
            candidate[p['address']-native.BASE:p['address']-native.BASE+4]=bytes.fromhex(p['replacement_hex'])
        cls.candidate=bytes(candidate)

    def test_all_five_appended_tones_receive_their_own_frozen_recipe(self):
        for tone in (25,26,27,28,29):
            for stage in (0,1):
                e,r,o,i,c,si=self.fixture(tone,stage)
                initial=native.state((33,35,67,68,69))
                result,source=self.snapshot(e,r,initial);self.assertEqual(result,1)
                e.u.mem_write(source,native.state((65,)*5,sequence=9))
                self.callback(e,o,i,c)
                self.assertEqual(self.status(e,r),2)
                out=e.alloc(104)
                e.call(self.manifest['exports']['m10v_isp_frame_recipe_state'],r,out)
                self.assertEqual(bytes(e.u.mem_read(out,104)),initial)
                e.call(self.manifest['exports']['m10v_isp_frame_recipe_completed'],r,si,tone,out)
                self.assertEqual(e.u.reg_read(native.A.UC_ARM_REG_R0),1)

    def test_restored_factory_presets_do_not_enter_the_film_renderer(self):
        for tone in (11,12,13,14,15,16,17,18,19,20,21,22):
            e,r,o,i,c,si=self.fixture(tone)
            self.assertEqual(self.snapshot(e,r,native.state((67,)*5))[0],1)
            self.callback(e,o,i,c)
            self.assertEqual(self.status(e,r),1)


if __name__=='__main__':unittest.main()
