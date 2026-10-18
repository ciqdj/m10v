"""GR IV optional features with exact independent firmware preimages.

Shared semantic ISO choices; independent GR4 addresses and register ABI.
"""
import hashlib,json,math,struct
from pathlib import Path
BASE=0x53000000
ROOT=Path(__file__).resolve().parents[1]
PROFILE=json.loads((ROOT/'native/gr4/extensions-abi.json').read_text())
THRESHOLDS=(400,800,1600,3200,5000,6400,8000,10000,12800)
def normalize_extensions(value=None):
 value={} if value is None else value
 if not isinstance(value,dict) or set(value)-{'aspect','level','negativeGrain','rawNr'}:raise ValueError('Invalid GR4 extension configuration')
 out={k:value.get(k,False) for k in ['aspect','level','negativeGrain']}
 if any(type(v)is not bool for v in out.values()):raise ValueError('Invalid GR4 extension toggle')
 raw=value.get('rawNr',{'mode':'stock'})
 if not isinstance(raw,dict) or raw.get('mode') not in ('stock','off','threshold') or set(raw)-{'mode','iso'}:raise ValueError('Invalid RAW NR mode')
 if raw['mode']=='threshold':
  if type(raw.get('iso'))is not int or raw['iso'] not in THRESHOLDS:raise ValueError('Invalid RAW NR ISO threshold')
 elif 'iso' in raw:raise ValueError('RAW NR ISO only applies to threshold mode')
 out['rawNr']=dict(raw);return out

def apply_extensions(patch,extensions=None):
 e=normalize_extensions(extensions);rtos=patch.image;raw=e['rawNr'];abi=PROFILE['raw_nr']
 for k in ('negativeGrain',):
  if e[k] and not PROFILE['supported'][k]:raise ValueError('GR4 extension not yet verified: '+k)
 edits=[];aspect_report=None
 if e['aspect']:
  import sys
  if str(ROOT/'vendor/gr4') not in sys.path:sys.path.insert(0,str(ROOT/'vendor/gr4'))
  from gr4_editor.crops import read_crops
  crop_rows,crop_proof=read_crops(bytes(rtos))
  if crop_proof.get('native_readback')!='passed' or not crop_proof.get('raw_recut_complete') or not any(row.get('requested_ratio')=='65:24' for row in crop_rows):raise ValueError('GR4 aspect must first compile via prepare_gr4_crops + apply_filter_registry')
  aspect_report={'verified':True,'ratios':[row['requested_ratio'] for row in crop_rows],'raw_recut_complete':True,'camera_tested':False}
 if e['negativeGrain']:
  n=PROFILE['negative_grain'];a=n['list']-BASE
  if bytes(rtos[a:a+20]).hex()!=n['expected_list_hex'] or struct.unpack_from('<II',rtos,n['directory']-BASE)!=(n['list'],n['count']):raise ValueError('GR4 native Negative Film grain detail differs')
 def write(a,expected,replacement,reason):
  off=a-BASE
  if bytes(rtos[off:off+len(expected)])!=expected:raise ValueError('GR4 extension preimage differs: '+reason)
  edits.append((a,expected,replacement,reason))
 if raw['mode']!='stock':
  for table in abi['mode0_tables']:
   a=table['address'];data=bytes(rtos[a-BASE:a-BASE+2880])
   if hashlib.sha256(data).hexdigest()!=table['sha256']:raise ValueError('GR4 RAW NR table differs')
   if any(data[i*20]!=(i>=36) for i in range(144)):raise ValueError('GR4 RAW NR enable layout differs')
  for i,t in enumerate(abi['mode0_tables']):
   at=0x5437b640+abi['mode0_b_pointers']-0x55000000+i*4
   if struct.unpack_from('<I',rtos,at-BASE)[0]!=t['address']:raise ValueError('GR4 RAW NR table pointer differs')
 if raw['mode']=='off':
  for row in abi['off_sites']:write(row['address'],struct.pack('<I',row['expected']),struct.pack('<I',row['replacement']),row['reason'])
 elif raw['mode']=='threshold':
  first=round(8*(math.log2(raw['iso']/3.125)-1))
  for t in abi['mode0_tables']:
   for i in range(36,first):write(t['address']+i*20,b'\1',b'\0','RAW NR enable before ISO threshold')
 # Verify every preimage first. Failed validation leaves the candidate untouched.
 for a,before,after,reason in edits:
  if len(after)==4:patch.set_word(a,struct.unpack('<I',after)[0],reason)
  else:
   rtos[a-BASE:a-BASE+len(after)]=after
   patch.changes.append({'address':hex(a),'before':before.hex(),'after':after.hex(),'reason':reason})
 level_report=None
 if e['level']:
  from scripts.build_gr4_level import apply_level
  level_report=apply_level(patch)
 return {'schema':'m10v-gr4-extensions/v1','extensions':e,'aspect':aspect_report,'level':level_report,'camera_tested':False,'negative_grain':{'native_supported':True,'patch_count':0,'style':24,'grain_field':16},
  'raw_nr':{'configuration':raw,'patch_count':len(edits),'first_enabled_index':round(8*(math.log2(raw['iso']/3.125)-1)) if raw['mode']=='threshold' else None,'mode0_tables':abi['mode0_tables'],'jpeg_nr':'stock','live_view_nr':'stock'}}

def prepare_gr4_crops(rtos,enabled):
 """Arguments for slots.apply_filter_registry before M10V resource expansion.

 GR4 already has native 4:3. Its original four aspect identities are retained
 and 65:24 uses a new immutable custom identity, preserving old photographs.
 """
 if type(enabled)is not bool:raise ValueError('GR4 aspect toggle must be boolean')
 if hashlib.sha256(rtos).hexdigest()!=PROFILE['rtos_sha256']:raise ValueError('GR4 aspect requires exact official RTOS')
 if not enabled:return {}
 import sys
 vendor=str(ROOT/'vendor/gr4')
 if vendor not in sys.path:sys.path.insert(0,vendor)
 from gr4_editor.crops import read_crops
 from gr4_editor.crop_compiler import prepare_crops
 original,inspection=read_crops(rtos)
 if inspection.get('native_readback')!='passed':raise ValueError('GR4 original crop readback failed')
 desired=original+[{'id':'m10v-65-24','name':'65:24','kind':'custom','identity':None,'requested_ratio':'65:24','editable':True}]
 # Use the native planner now to prove geometry and all native identity rules.
 plan,_=prepare_crops(rtos,{},desired,original)
 return {'crops':plan['crops'],'prior_crops':original}
