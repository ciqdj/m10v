#!/usr/bin/env python3
"""Read the emitted GR4 BIN independently of the build's in-memory buffers."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/gr4'))
from gr4_editor.firmware import load_image
from gr4_editor.slots import canonical_base,_metadata
BASE=0x53000000
def sha(data):return hashlib.sha256(data).hexdigest()
def verify(candidate,receipt):
 image=load_image(candidate);r=json.loads(receipt.read_text());native=_metadata(image.rtos)['m10v']
 original=load_image(ROOT/'bin/fwdc248b-gr4-officical.bin')
 assert sha(image.candidate)==r['candidate_sha256'] and len(image.candidate)==r['candidate_bytes'],'package identity'
 assert canonical_base(image.rtos)==original.rtos,'original RTOS recovery'
 runtime=r['runtime'];start=runtime['base']-BASE
 assert sha(image.rtos[start:start+runtime['code_bytes']])==runtime['code_sha256'],'packaged runtime'
 assert native['initial_state_hex']==runtime['initial_state_hex'],'state metadata'
 resources=r['resources'];pixels=(ROOT/'native/gr3/m10v_icons.rgba').read_bytes()+(ROOT/'native/gr4/grain_size_icon.rgba').read_bytes()
 for i in range(69):
  pointer=struct.unpack_from('<I',image.rtos,resources['icon_table']-BASE+(1024+i)*4)[0]
  kind,width,height,zero,index=struct.unpack_from('<HHHHI',image.rtos,pointer-BASE)
  assert (kind,width,height,zero)==(1,40,40,0),'native icon descriptor'
  assert image.icon_bytes[index*4:index*4+6400]==pixels[i*6400:(i+1)*6400],'native icon pixels'
 for pointer,text in zip(resources['descriptors'],resources['texts']):
  size,kind,zero,value=struct.unpack_from('<BBHI',image.rtos,pointer-BASE)
  encoded=(text+'\0').encode('utf-16-le')
  assert (size*2,kind,zero)==(len(encoded),1,0),'native text descriptor'
  assert image.rtos[value-BASE:value-BASE+len(encoded)]==encoded,'native text content'
 extensions=native['extensions']
 if extensions.get('level'):
  level=extensions['level'];at=level['base']-BASE
  assert sha(image.rtos[at:at+level['bytes']])==level['sha256'],'packaged level module'
  hook=level['hook'];assert struct.unpack_from('<I',image.rtos,hook['address']-BASE)[0]==hook['replacement'],'level callback'
 return {'schema':'m10v-gr4-independent-candidate-readback/v1','candidate_sha256':sha(image.candidate),
  'candidate_bytes':len(image.candidate),'canonical_source_recovered':True,'runtime_code_sha256':runtime['code_sha256'],
  'text_descriptors_verified':len(resources['texts']),'icon_pixels_verified':69,'extensions':r['extensions'],
  'camera_tested':False,'passed':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 result=verify(a.candidate,a.receipt);a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
