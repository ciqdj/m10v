#!/usr/bin/env python3
"""GR IV native preset/recipe customization with exact original recovery."""
import argparse,base64,hashlib,json,struct,sys,tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/gr4'))
from gr4_editor.firmware import load_image,repack_image
from gr4_editor.filter_reader import read_filters,_native_lookup
from gr4_editor.slots import (apply_filter_registry,_Patch,_metadata,_finish,_canonical_restore,canonical_base,prepare_update_policy,BASE,TEXT_CATALOG,ICON_CATALOG,DEFAULT_ENTRIES,PARAMETER_IDS,_branch,_mov,_target)
from gr4_editor.firmware import _Memory
from scripts.build_gr4_m10v_firmware import OFFICIAL_SHA,prepare_package_policy
FIELDS=['saturation','hue','high_low_key','contrast','highlight_contrast','shadow_contrast','sharpness','shading','clarity']
RECIPE_STYLES={'builtin-0b':11,'builtin-16':24,'builtin-11':17,'builtin-15':23}
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def rows_for(source):
 need(sha(source.candidate)==OFFICIAL_SHA,'exact official GR IV source required');return read_filters(source)
def catalog(source):
 rows=rows_for(source);native=[r for r in rows if 11<=r['identity']['style_id']<=30]
 counts={}
 for row in native:
  icon=row['identity']['icon_id'];counts[icon]=counts.get(icon,0)+1
 return [{'slot':r['identity']['style_id'],'name':r['name'],'factoryName':r['name'],'canRename':True,'nameMax':80,
          'canIcon':True,'iconPixelsBase64':base64.b64encode(bytes.fromhex(r['resources']['icon']['hex'])).decode(),
          'affectedLanguages':list(range(21)),'parameters':[p['id'] for p in r['parameters'] if p.get('native_field_supported')]} for r in native]
def recipe_icon(recipe):
 mode=recipe.get('iconMode','original')
 need(mode in ('original','preset','custom'),'invalid recipe icon mode')
 if mode=='original':return None
 if mode=='custom':
  icon=recipe.get('customIcon');need(isinstance(icon,dict) and set(icon)<={'schema','width','height','format','pixelsBase64','sourceName'} and icon.get('schema')=='grlife-camera-icon/v1' and icon.get('width')==40 and icon.get('height')==40 and icon.get('format')=='rgba8','custom icon must be40x40 RGBA8')
  try:raw=base64.b64decode(icon['pixelsBase64'],validate=True)
  except Exception as e:raise ValueError('invalid custom icon encoding') from e
  need(len(raw)==6400,'custom icon must contain6400bytes');return raw
 need(recipe.get('source')=='community_reference','preset icon requires registered community recipe')
 runtime=ROOT/'.runtime/grlife-current';sys.path.insert(0,str(runtime))
 from reconstruction.firmware_store.preset_registry import preset_slots,preset_icon_rgba
 need(recipe['slotId'] in preset_slots(recipe.get('id')),'community recipe identity does not match slot')
 return preset_icon_rgba(recipe['id'])

def validate_selection(value):
 need(isinstance(value,dict) and not(set(value)-{'variant','features','recipes','filmIds','filmLibrary','filmTexture','stockPresets','negativeGrainMenu','rawNr'}),'selection contains unknown fields');features=value.get('features');need(isinstance(features,list) and features and len(set(features))==len(features) and all(f in ['recipes','presets','aspect','level','negativeGrain','rawNr'] for f in features),'GR IV custom workflow supports recipes, presets and verified native extensions; film/timestamp use the film library')
 recipes=value.get('recipes',[]);presets=value.get('stockPresets',[])
 need(isinstance(recipes,list) and len(recipes)<=6 and isinstance(presets,list) and len(presets)<=20,'invalid customization list')
 need('recipes' not in features or bool(recipes),'configure at least one recipe');need(not recipes or 'recipes' in features,'enable recipes');need(not presets or 'presets' in features,'enable presets')
 seen=set()
 for r in recipes:
  need(isinstance(r,dict) and r.get('slotId') in [*RECIPE_STYLES,'custom1','custom2'] and r['slotId'] not in seen,'invalid or duplicate recipe slot');seen.add(r['slotId'])
  p=r.get('parameters');need(isinstance(p,dict) and set(p)==set(FIELDS) and all(type(v)is int and -4<=v<=4 for v in p.values()),'nine parameters must be integers -4..4')
  name=r.get('cameraName');need(isinstance(name,str) and name.strip()==name and 1<=len(name)<=80 and all(32<=ord(c)<=126 for c in name),'invalid camera name')
  recipe_icon(r)
 ids=set()
 for r in presets:
  need(isinstance(r,dict) and set(r)<={'slot','name','iconPixelsBase64'} and type(r.get('slot'))is int and 11<=r['slot']<=30 and r['slot'] not in ids,'invalid or duplicate native preset');ids.add(r['slot'])
  need(r['slot'] not in [RECIPE_STYLES.get(x['slotId']) for x in recipes],'native preset position already used by a recipe')
  if 'name' in r:need(isinstance(r['name'],str) and r['name'].strip()==r['name'] and 1<=len(r['name'])<=80 and all(32<=ord(c)<=126 for c in r['name']),'invalid preset name')
  if 'iconPixelsBase64' in r:
   try:raw=base64.b64decode(r['iconPixelsBase64'],validate=True)
   except Exception as e:raise ValueError('invalid icon encoding') from e
   need(len(raw)==6400,'icon must be 40x40 RGBA')
 return value

def compile_custom(source,selection):
 validate_selection(selection);originals=rows_for(source);by_style={r['identity']['style_id']:r for r in originals};desired=deepcopy(originals)
 native_edits=deepcopy(selection.get('stockPresets',[]));defaults=[];custom_ids=[]
 for recipe in selection.get('recipes',[]):
  style=RECIPE_STYLES.get(recipe['slotId']);icon=recipe_icon(recipe);values=[recipe['parameters'][key]+4 for key in FIELDS]
  if style is not None:
   supported={p['id'] for p in by_style[style]['parameters'] if p.get('native_field_supported')};need(set(PARAMETER_IDS)<=supported,'recipe base does not expose all nine parameters')
   native_edits.append({'slot':style,'name':recipe['cameraName'],**({'iconPixelsBase64':base64.b64encode(icon).decode()} if icon is not None else {})});defaults.append((style,values))
  else:
   row=deepcopy(by_style[11]);row.update(id='m10v-'+recipe['slotId'],kind='custom',name=recipe['cameraName'],enabled=True,editable=True,identity={},template_id=11,menu_order=len(desired),calibration=None,xmp=None,pending_color_conversion=False)
   for p in row['parameters']:
    if p['id'] in PARAMETER_IDS:p.update(value=values[PARAMETER_IDS.index(p['id'])],default=values[PARAMETER_IDS.index(p['id'])],enabled=True)
   if icon is not None:row['icon_rgba']={'hex':icon.hex()}
   desired.append(row);custom_ids.append(row['id'])
 from scripts.build_gr4_extensions import prepare_gr4_crops
 rtos,icons,report=apply_filter_registry(source.rtos,source.icon_bytes,desired,originals,**prepare_gr4_crops(source.rtos,'aspect' in selection['features']))
 meta=_metadata(rtos);length=struct.unpack_from('<I',rtos,len(rtos)-8)[0];patch=_Patch(rtos[:-16-length]);pixels=bytearray(icons);applied=[]
 resource_ids={};next_text=860;next_icon=900
 for item in native_edits:
  style=item['slot'];identity=by_style[style]['identity'];resource_ids[style]={}
  if 'name' in item:
   raw=(item['name']+'\0').encode('utf-16-le');text=patch.append(raw,4);descriptor=patch.append(struct.pack('<BBHI',len(raw)//2,1,0,text),4)
   for language in range(21):
    address=patch.word(TEXT_CATALOG+language*4)+next_text*4;need(patch.word(address)==0,'native name resource would overwrite an existing entry');patch.set_word(address,descriptor,'M10V native preset name')
   resource_ids[style]['text']=next_text;next_text+=1
  if 'iconPixelsBase64' in item:
   raw=base64.b64decode(item['iconPixelsBase64']);pixels.extend(bytes(-len(pixels)&3));offset=len(pixels);pixels.extend(raw)
   need(patch.word(ICON_CATALOG+next_icon*4)==0,'native icon resource would overwrite an existing entry')
   descriptor=patch.append(struct.pack('<HHHHI',1,40,40,0,offset//4),16);patch.set_word(ICON_CATALOG+next_icon*4,descriptor,'M10V native preset icon');resource_ids[style]['icon']=next_icon;next_icon+=1
  applied.append(item)
 # Route per-style resource identities instead of overwriting shared native
 # Standard/HDR descriptors. Original aliases remain byte-exact for other styles.
 for kind,entry in [('text',0x5337f824),('icon',0x53380fac)]:
  prior=patch.word(entry);need(prior&0xff000000==0xea000000,'registry resource entry is not an audited branch');previous=_target(entry,prior)
  words=[];origin=(BASE+len(patch.image)+15)&~15
  if kind=='icon':words += [0xe3520000,_branch(origin+4,previous,condition=1)]
  for style,ids in resource_ids.items():
   if kind in ids:words += [0xe3510000|style,_mov(0,ids[kind],condition=0),0x012fff1e]
  if words:
   words.append(_branch(origin+len(words)*4,previous));patch.append(words,16);patch.set_word(entry,_branch(entry,origin),'M10V independent native '+kind+' identity')
 if next_icon>900:
  patch.set_word(0x5323dbb4,_mov(3,next_icon-1),'M10V custom native icon upper bound')
  patch.set_word(0x5323e40c,_mov(2,next_icon-1),'M10V custom native icon upper bound')
 if next_text>860:
  for site in (0x535734f4,0x53572ae0):
   helper=_target(site,patch.word(site));need(patch.word(helper)==0xe52d3004,'native text bound helper differs');patch.set_word(helper+4,_mov(3,895),'M10V custom native text upper bound')
 for field,entry in enumerate(DEFAULT_ENTRIES):
  previous=_target(entry,patch.word(entry));words=[];origin=(BASE+len(patch.image)+15)&~15
  for style,values in defaults:
   at=origin+len(words)*4
   words += [0xe3510000|style,_branch(at+4,at+28,condition=1),0xe5d0c01f,0xe35c0000,_branch(at+16,previous,condition=1),0xe3a00000|values[field],0xe12fff1e]
  if words:
   words.append(_branch(origin+len(words)*4,previous));patch.append(words,16);patch.set_word(entry,_branch(entry,origin),'M10V native recipe reset default')
 extensions={'aspect':'aspect' in selection['features'],'level':'level' in selection['features'],'negativeGrain':'negativeGrain' in selection['features'],'rawNr':selection.get('rawNr',{'mode':'stock'}) if 'rawNr' in selection['features'] else {'mode':'stock'}}
 if any(extensions[k] for k in ['aspect','level','negativeGrain']) or extensions['rawNr']!={'mode':'stock'}:
  from scripts.build_gr4_extensions import apply_extensions
  extension_report=apply_extensions(patch,extensions)
 else:extension_report={'features':[]}
 meta['compiler_base_restore']=_canonical_restore(source.rtos,patch.image);meta['m10v_customization']={'selection':selection,'native_defaults':defaults,'camera_tested':False}
 rtos=_finish(patch.image,meta);rtos,policy=prepare_package_policy(rtos,source.rtos)
 need(canonical_base(rtos)==source.rtos,'custom canonical recovery failed')
 inspected=read_filters(SimpleNamespace(rtos=rtos,icon_bytes=bytes(pixels),editable=True));actual={r['identity']['style_id']:r for r in inspected};memory=_Memory(rtos)
 for edit in applied:
  if 'name' in edit:need(actual[edit['slot']]['name']==edit['name'],'native name readback differs')
  if 'iconPixelsBase64' in edit:need(actual[edit['slot']]['resources']['icon']['hex']==base64.b64decode(edit['iconPixelsBase64']).hex(),'native icon readback differs')
 for style,values in defaults:
  for entry,value in zip(DEFAULT_ENTRIES,values):need(_native_lookup(memory,entry,style,default_object=True)==value,'native recipe ARM getter readback differs')
 for rid in custom_ids:
  row=next(r for r in inspected if r['id']==rid);want=next(r for r in desired if r['id']==rid);need(row['name']==want['name'],'custom name readback differs')
 result={'ready':True,'model':'GR IV','filename':'fwdc248b.bin','camera_tested':False,'source_sha256':OFFICIAL_SHA,'selection':selection,'native_edits':[{'slot':x['slot'],'name':x.get('name'),'icon_changed':'iconPixelsBase64' in x} for x in applied],'native_recipe_defaults':defaults,'custom_styles':[r['identity']['style_id'] for r in inspected if r['id'] in custom_ids],'extensions':extension_report,'canonical_source_recovered':True,'update_policy_installation':policy,'reset_required':bool(defaults),'compiler_source_sha256':sha(Path(__file__).read_bytes())}
 return rtos,bytes(pixels),result

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--config',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--catalog',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();paths=[v.resolve() for v in [a.input,a.config,a.report,a.output] if v is not None];need(len(paths)==len(set(paths)),'input/config/report/output paths must be distinct');source=load_image(a.input)
 if a.catalog:a.report.write_text(json.dumps(catalog(source)));return
 selection=json.loads(a.config.read_text());rtos,icons,report=compile_custom(source,selection)
 if not a.check:
  need(a.output is not None,'output required');candidate,proof=repack_image(source,rtos,new_icon_bytes=icons,new_version=0x010b0a0a,allow_older=True)
  with tempfile.TemporaryDirectory(prefix='m10v-gr4-custom-readback-') as folder:
   target=Path(folder)/'readback.bin';target.write_bytes(candidate);loaded=load_image(target);need(canonical_base(loaded.rtos)==source.rtos,'final custom package recovery differs');need(_metadata(loaded.rtos)['m10v_customization']['selection']==selection,'final custom selection differs')
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(candidate);report.update(candidate_sha256=sha(candidate),candidate_bytes=len(candidate),package=proof)
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
