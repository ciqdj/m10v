"""GR IIIx keeps film/settings/HDF while custom GR III focal hooks are absent."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.build_gr3_m10v_library import build
ROOT=Path(__file__).resolve().parents[1]
class ZoomModelGateTests(unittest.TestCase):
    def test_disabled_zoom_keeps_existing_menus_and_independent_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            m=build(directory,sd_library=True,custom_zoom=False,hdf_enabled=True)
            self.assertIs(m['zoom']['enabled'],False)
            self.assertEqual(len(m['settings_menu']['rows']),3)
            self.assertNotIn(0x0200f105,m['settings_menu']['private_routes'])
            self.assertEqual(len(m['hdf_menu']['rows']),4)
            script="""import{readFileSync}from'node:fs';
import{zoomPatches}from'./node/gr3-zoom.mjs';
import{settingsPatches,checkSettings}from'./node/gr3-settings-menu.mjs';
import{hdfMenuPatches}from'./node/gr3-digital-hdf.mjs';
const dir=process.argv[1],m=JSON.parse(readFileSync(dir+'/m10v-library-arm.json')),b=readFileSync(dir+'/m10v-library-arm.bin');
if(zoomPatches(b,m).length)throw Error('GR III focal hook escaped model gate');
checkSettings(b,m);const p=[...settingsPatches(m),...hdfMenuPatches(b,m)];
if(p.some(x=>x.replacement===0x0200f105))throw Error('custom focal route visible');
const bad=structuredClone(m);delete bad.zoom.enabled;
let rejected=false;try{zoomPatches(b,bad);}catch{rejected=true;}if(!rejected)throw Error('missing explicit gate accepted');
console.log('disabled zoom preserves three settings rows and fourth HDF row');"""
            subprocess.run(['node','--input-type=module','-e',script,directory],cwd=ROOT,check=True,capture_output=True)
    def test_default_gr3_merges_crop_entry_and_keeps_four_hdf_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            m=build(directory,sd_library=True,hdf_enabled=True)
            self.assertIs(m['zoom']['enabled'],True)
            self.assertEqual(len(m['settings_menu']['rows']),3)
            self.assertEqual(len(m['hdf_menu']['rows']),4)
            script="""import{readFileSync}from'node:fs';
import{zoomPatches}from'./node/gr3-zoom.mjs';
import{checkSettings}from'./node/gr3-settings-menu.mjs';
import{hdfMenuPatches}from'./node/gr3-digital-hdf.mjs';
const dir=process.argv[1],m=JSON.parse(readFileSync(dir+'/m10v-library-arm.json')),b=readFileSync(dir+'/m10v-library-arm.bin');
if(zoomPatches(b,m).length!==17)throw Error('missing GR III focal hooks');checkSettings(b,m);const p=hdfMenuPatches(b,m);if(p.find(x=>x.address===0x53b37018)?.replacement!==0x0200f105)throw Error('original crop entry not merged');"""
            subprocess.run(['node','--input-type=module','-e',script,directory],cwd=ROOT,check=True,capture_output=True)

    def test_cli_model_gate_flag_is_available(self):
        result=subprocess.run(['python3','scripts/build_gr3_m10v_library.py','--help'],cwd=ROOT,check=True,capture_output=True,text=True)
        self.assertIn('--no-custom-zoom',result.stdout)
if __name__=='__main__':unittest.main()
