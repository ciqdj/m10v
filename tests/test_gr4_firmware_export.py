"""Actual official-input -> packaged GR IV -> independently reopened export."""
import copy,hashlib,json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Gr4FirmwareExportTests(unittest.TestCase):
 def configuration(self,films):
  return {'slots':[{'film':f,'grain':1,'soft':0,'halo':{'gain':0,'spread':3,'threshold':5,'profile':2},'effects':{'grainSize':0,'leakGain':0,'leakPosition':0,'leakSpread':4,'leakVariation':0,'filmExposure':1 if f==67 else 0}} for f in films],'stamp':0,'format':0,'corner':0,'color':0,'hdf':0,'filmNameStamp':False}
 def test_full_official_gr4_exports_all_new_stocks_and_phoenix_ei120(self):
  from scripts.build_gr4_m10v_firmware import initial_state
  from gr4_editor.firmware import load_image
  from gr4_editor.slots import _metadata,canonical_base,BASE
  source=ROOT/'bin/fwdc248b-gr4-officical.bin';original=load_image(source)
  artwork=(ROOT/'native/gr3/m10v_icons.rgba').read_bytes()
  for films in ([73,74,75,76,77],[78,67,68,33,66]):
   with self.subTest(films=films),tempfile.TemporaryDirectory() as folder:
    d=Path(folder);configuration=self.configuration(films);config=d/'config.json';config.write_text(json.dumps({'configuration':configuration,'version_unlock':{'enabled':False}}));report_path=d/'report.json';output=d/'candidate.bin'
    result=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/build_gr4_m10v_firmware.py'),'--input',str(source),'--config',str(config),'--report',str(report_path),'--output',str(output)],cwd=ROOT,capture_output=True,text=True)
    self.assertEqual(result.returncode,0,result.stderr)
    report=json.loads(report_path.read_text());loaded=load_image(output);meta=_metadata(loaded.rtos);resources=report['resources'];runtime=report['runtime'];state=bytes.fromhex(meta['m10v']['initial_state_hex'])
    self.assertEqual(report['film_count'],78);self.assertEqual(runtime['film_count'],78);self.assertFalse(report['camera_tested']);self.assertEqual(state,initial_state(configuration));self.assertEqual([struct.unpack_from('<H',state,12+i*8)[0] for i in range(5)],films)
    self.assertEqual(canonical_base(loaded.rtos),original.rtos);self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),report['candidate_sha256'])
    code=loaded.rtos[runtime['base']-BASE:runtime['base']-BASE+runtime['code_bytes']];self.assertEqual(hashlib.sha256(code).hexdigest(),runtime['code_sha256'])
    self.assertEqual((resources['icon_first'],resources['icon_last']),(1024,1102));self.assertEqual(resources['film_icon_last'],1101);self.assertEqual(resources['grain_size_icon'],1102);self.assertEqual(len(resources['texts']),194)
    self.assertEqual(loaded.icon_bytes[resources['pixel_offset']:resources['pixel_offset']+len(artwork)],artwork)
    for i in range(79):
     descriptor=struct.unpack_from('<I',loaded.rtos,resources['icon_table']-BASE+4*(1024+i))[0];kind,width,height,zero,pointer=struct.unpack_from('<HHHHI',loaded.rtos,descriptor-BASE)
     self.assertEqual((kind,width,height,zero),(1,40,40,0));self.assertEqual(pointer*4,resources['pixel_offset']+6400*i)
    for stock in json.loads((ROOT/'web/gr3/newstocks-luts.json').read_text())['stocks']:self.assertIn(bytes(stock['values']),code)
    if 67 in films:self.assertEqual(state[56+films.index(67)*8+5],1)
if __name__=='__main__':unittest.main()
