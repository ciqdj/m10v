#!/usr/bin/env python3
"""Build and independently reload an M10V GR IV candidate from the exact official input."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'vendor/gr4'))
from gr4_editor.firmware import load_image,repack_image
from gr4_editor.filter_reader import read_filters
from gr4_editor.slots import (_Patch,_metadata,_finish,_canonical_restore,canonical_base,
    apply_filter_registry,prepare_update_policy,_mov,_branch,_target,BASE,TEXT_CATALOG,ICON_CATALOG)
from scripts.build_gr4_m10v_library import build as build_runtime,default_state,validate_state
from scripts.m10v_catalog_resources import catalog_texts
OFFICIAL_SHA='a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f'
RTOS_SHA='a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1'
def sha(b):return hashlib.sha256(b).hexdigest()

def initial_state(configuration):
    required={'slots','stamp','format','corner','color'}
    if not isinstance(configuration,dict) or not required<=set(configuration) or set(configuration)-required-{'hdf','filmNameStamp'}:raise ValueError('complete five-slot configuration required')
    if configuration.get('hdf',0)!=0:raise ValueError('digital HDF is only supported on GR III')
    if type(configuration.get('filmNameStamp',False)) is not bool or configuration.get('filmNameStamp',False):raise ValueError('film name stamp is only supported on GR III / GR IIIx')
    slots=configuration['slots']
    if not isinstance(slots,list) or len(slots)!=5:raise ValueError('five slots required')
    b=bytearray(default_state())
    def integer(v,maximum):
        if type(v)is not int or not 0<=v<=maximum:raise ValueError('invalid configuration field')
        return v
    for i,s in enumerate(slots):
        if set(s)!={'film','grain','soft','halo','effects'}:raise ValueError('invalid slot fields')
        h=s['halo'];e=s['effects']
        if set(h)!={'gain','spread','threshold','profile'} or set(e)!={'grainSize','leakGain','leakPosition','leakSpread','leakVariation','filmExposure'}:raise ValueError('invalid effect fields')
        film=integer(s['film'],78)
        if not film:raise ValueError('film zero is invalid')
        struct.pack_into('<H6B',b,12+i*8,film,integer(s['grain'],3),integer(s['soft'],3),
            integer(h['gain'],8) if integer(h['profile'],3) else 0,integer(h['spread'],8),integer(h['threshold'],8),h['profile'])
        b[56+i*8:64+i*8]=bytes([integer(e['grainSize'],2),integer(e['leakGain'],8),integer(e['leakPosition'],5),
            integer(e['leakSpread'],8),integer(e['leakVariation'],1),integer(e['filmExposure'],2),0,0])
    b[52:56]=bytes(integer(configuration[k],2 if k=='stamp' else 3) for k in ['stamp','format','corner','color'])
    struct.pack_into('<I',b,100,zlib.crc32(b[:100]));return validate_state(bytes(b))

def install_resources(patch,icons):
    labels=catalog_texts();text_end=1024+len(labels)
    if len(labels)!=194:raise ValueError('shared camera labels changed')
    descriptors=[]
    for text in labels:
        encoded=(text+'\0').encode('utf-16-le')
        at=patch.append(encoded,4)
        descriptors.append(patch.append(struct.pack('<BBHI',len(encoded)//2,1,0,at),4))
    roots=[]
    for language in range(21):
        old=patch.word(TEXT_CATALOG+4*language)
        contents=bytes(patch.image[old-BASE:old-BASE+896*4])
        if len(contents)!=896*4:raise ValueError('text directory extent differs')
        row=bytearray(text_end*4);row[:len(contents)]=contents
        struct.pack_into('<'+str(len(descriptors))+'I',row,1024*4,*descriptors)
        roots.append(patch.append(row,16))
    for i,at in enumerate(roots):patch.set_word(TEXT_CATALOG+4*i,at,'M10V preserved native language directory')
    text_bound=[]
    for site in (0x535734f4,0x53572ae0):
        helper=_target(site,patch.word(site))
        if patch.word(helper)!=0xe52d3004:raise ValueError('text bound continuation differs')
        patch.set_word(helper+4,_mov(3,text_end-1),'M10V text upper bound');text_bound.append(helper+4)
    artwork=(ROOT/'native/gr3/m10v_icons.rgba').read_bytes()
    if len(artwork)!=78*6400:raise ValueError('shared film artwork incomplete')
    grain_artwork=(ROOT/'native/gr4/grain_size_icon.rgba').read_bytes()
    if len(grain_artwork)!=6400 or sha(grain_artwork)!='4d4ab11bf24c60777a57b9cddff4223c771dd361035dc4338ce99b7fa9f23711':raise ValueError('GR3 grain size artwork differs')
    film_count=len(artwork)//6400; icon_count=film_count+1;icon_last=1024+icon_count-1
    directory=bytearray((1024+icon_count)*4)
    directory[:1024*4]=patch.image[ICON_CATALOG-BASE:ICON_CATALOG-BASE+1024*4]
    pixels=bytearray(icons);pixels.extend(bytes(-len(pixels)&3));pixel_start=len(pixels);pixels.extend(artwork)
    pixels.extend(grain_artwork)
    for i in range(icon_count):
        descriptor=patch.append(struct.pack('<HHHHI',1,40,40,0,(pixel_start+6400*i)//4),16)
        struct.pack_into('<I',directory,(1024+i)*4,descriptor)
    table=patch.append(directory,16)
    patch.set_word(0x533ef604,_mov(0,table&65535),'M10V icon directory low')
    patch.set_word(0x533ef608,_mov(0,table>>16,high=True),'M10V icon directory high')
    for site,reg in ((0x5323dbb4,3),(0x5323e40c,2)):patch.set_word(site,_mov(reg,icon_last),'M10V icon upper bound')
    return bytes(pixels),{'text_first':1024,'text_last':text_end-1,'texts':labels,'descriptors':descriptors,
        'text_bound_sites':text_bound,'language_rows':roots,'icon_first':1024,'icon_last':icon_last,'film_icon_last':1024+film_count-1,'grain_size_icon':icon_last,'icon_table':table,
        'pixel_offset':pixel_start,'artwork_sha256':sha(artwork),'grain_size_icon_sha256':sha(grain_artwork)}

def prepare_package_policy(rtos,base):
    """Refresh this registry's recovery records before the generic repacker.

    The repacker's demo adapter treats GR4REG01 as foreign recovery metadata.
    Installing its update gate there would omit the newly changed gate words
    from compiler_base_restore. The registry owner records them first, so the
    repacker can preserve the already installed policy without another edit.
    """
    if canonical_base(rtos)!=base:raise ValueError('GR4 pre-policy canonical recovery failed')
    result,proof=prepare_update_policy(rtos,allow_older=True)
    if canonical_base(result)!=base:raise ValueError('GR4 package policy canonical recovery failed')
    return result,proof

def prepare(source,config,out):
    if sha(source.candidate)!=OFFICIAL_SHA or sha(source.rtos)!=RTOS_SHA:raise ValueError('exact official GR IV 1.11 input required')
    initial=initial_state(config['configuration'])
    if type(config.get('debug_mode',False))is not bool:raise ValueError('invalid debug mode')
    if config.get('version_unlock',{'enabled':False})!={'enabled':False}:raise ValueError('GR4 version unlock not implemented')
    originals=read_filters(source);template=next(x for x in originals if x['name']=='Standard')
    rows=deepcopy(originals);artwork=(ROOT/'native/gr3/m10v_icons.rgba').read_bytes()
    labels=catalog_texts()
    # New style identities are assigned by the existing independent GR4 registry.
    for i in range(5):
        row=deepcopy(template);film=struct.unpack_from('<H',initial,12+8*i)[0]
        row.update(id='m10v-slot-'+str(i+1),kind='custom',name='M10V Slot '+str(i+1),enabled=True,
            editable=True,identity={},template_id=template['id'],menu_order=len(rows),calibration=None,xmp=None,pending_color_conversion=False)
        row['icon_rgba']={'hex':artwork[(film-1)*6400:film*6400].hex()}
        for p in row.get('parameters',[]):
            if p['id'] in ('Saturation','ColorHue','ImageKey','Contrast','ContrastHighLight','ContrastShadow','Sharpness','Shading','ClarityControl'):
                p.update(value=4,default=4,enabled=True)
        rows.append(row)
    from scripts.build_gr4_extensions import normalize_extensions,prepare_gr4_crops
    extensions=normalize_extensions(config.get('extensions'))
    registry,icons,registry_report=apply_filter_registry(source.rtos,source.icon_bytes,rows,originals,
        **prepare_gr4_crops(source.rtos,extensions['aspect']))
    meta=_metadata(registry);length=struct.unpack_from('<I',registry,len(registry)-8)[0]
    patch=_Patch(registry[:len(registry)-16-length])
    # Native crop readback runs against the registry's original lookup layer,
    # before M10V replaces those entries with dynamic menu dispatch.
    from scripts.build_gr4_extensions import apply_extensions
    extension_report=apply_extensions(patch,extensions)
    icons,resources=install_resources(patch,icons)
    base=(BASE+len(patch.image)+15)&~15
    manifest=build_runtime(out,base,initial.hex(),rtos=source.rtos,debug_mode=config.get('debug_mode',False),debug_build_id=int(sha(initial)[:8],16))
    runtime=bytearray((Path(out)/'m10v-library-arm.bin').read_bytes())
    # Preserve vendor custom-style fallback routing in every original entry.
    for row in manifest['continuations']:
        entry,off=row['entry'],row['offset'];word=patch.word(entry)
        if word&0xff000000==0xea000000:
            struct.pack_into('<I',runtime,off,_branch(base+off,_target(entry,word)))
    manifest['code_sha256']=sha(runtime)
    (Path(out)/'m10v-library-arm.bin').write_bytes(runtime)
    (Path(out)/'m10v-library-arm.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if patch.append(runtime,16)!=base:raise ValueError('GR4 runtime base moved')
    symbols=manifest['symbols'];applied=[]
    def hook(at,expected,new,label):
        old=patch.word(at)
        if old!=expected:raise ValueError('GR4 hook preimage differs: '+label)
        patch.set_word(at,new,label);applied.append({'address':at,'before':old,'after':new,'label':label})
    profile=json.loads((ROOT/'native/gr4/ui-abi.json').read_text())
    for row in profile['image_control_scoped_hooks']:
        hook(row['address'],int(row['expected'],16),_branch(row['address'],symbols[row['symbol']],link=True),'M10V ImageControl scoped '+row['symbol'])
    # Entry continuations deliberately keep the registry's original fallback.
    for key in ('name','value_name','icon','value_icon','focus','confirm','key','enter','rows'):
        row=profile['image_control_entries'].get(key)
        if row:
            at=row['address'];hook(at,patch.word(at),_branch(at,symbols['m10v_menu_'+key]),'M10V ImageControl '+key)
    hook(0x537035c8,0xeb076798,_branch(0x537035c8,symbols['m10v_chain_capture'],link=True),'M10V still JPEG render before encoder enqueue')
    for kind in ('settings_menu','detail'):
        for row in manifest[kind]['patches']:
            raw=bytes.fromhex(row['expected']);new=bytes.fromhex(row['replacement']);at=row['address']
            if bytes(patch.image[at-BASE:at-BASE+len(raw)])!=raw:raise ValueError('GR4 '+kind+' preimage differs: '+row['label'])
            if len(raw)!=len(new):raise ValueError('GR4 patch size differs')
            patch.image[at-BASE:at-BASE+len(raw)]=new
            applied.append({'address':at,'before_hex':raw.hex(),'after_hex':new.hex(),'label':row['label']})
    meta['compiler_base_restore']=_canonical_restore(source.rtos,patch.image)
    meta['m10v']={'runtime':manifest,'resources':resources,'patches':applied,'extensions':extension_report,
        'initial_state_hex':initial.hex(),'camera_tested':False}
    result=_finish(patch.image,meta)
    result,update_policy=prepare_package_policy(result,source.rtos)
    if canonical_base(result)!=source.rtos:raise ValueError('GR4 canonical recovery failed')
    if result[base-BASE:base-BASE+len(runtime)]!=runtime:raise ValueError('GR4 runtime independent readback differs')
    # Read back final resource directories/descriptors from emitted bytes.
    for i,text in enumerate(resources['texts']):
        at=resources['descriptors'][i]-BASE
        size,kind,zero,pointer=struct.unpack_from('<BBHI',result,at)
        encoded=(text+'\0').encode('utf-16-le')
        if kind!=1 or zero or size*2!=len(encoded) or result[pointer-BASE:pointer-BASE+len(encoded)]!=encoded:raise ValueError('GR4 text readback failed')
    for i in range(79):
        descriptor=struct.unpack_from('<I',result,resources['icon_table']-BASE+4*(1024+i))[0]
        kind,width,height,zero,pointer=struct.unpack_from('<HHHHI',result,descriptor-BASE)
        if (kind,width,height,zero)!=(1,40,40,0) or pointer*4!=resources['pixel_offset']+6400*i:raise ValueError('GR4 icon descriptor readback failed')
    if icons[resources['pixel_offset']:resources['pixel_offset']+len(artwork)]!=artwork:raise ValueError('GR4 icon artwork readback failed')
    source_files={str(p.relative_to(ROOT)):sha(p.read_bytes()) for folder in ('native/gr3','native/gr4','scripts')
        for p in (ROOT/folder).glob('*') if p.is_file() and p.suffix in ('.c','.h','.py','.json','.rgba')}
    return result,icons,{'schema':'m10v-gr4-firmware-build/v1','ready':True,'model':'GR IV','filename':'fwdc248b.bin',
        'source_sha256':OFFICIAL_SHA,'runtime_source_sha256':sha(json.dumps(source_files,sort_keys=True).encode()),
        'runtime':manifest,'resources':resources,'patches':applied,'extensions':extensions,
        'update_policy_requested':True,'update_policy_installation':update_policy,
        'configuration':config['configuration'],'film_count':78,'active_slots':5,'external_film_pack':True,
        'features':['film','800t','5207','phoenix-ii-200','harman-red-125','fuji-c200','kodak-proimage-100','kodak-tmax-100','aerochrome-iii-1443','aerocolor-iv-2460','vision3-50d-5203','grain','soft','timestamp'],
        'camera_tested':False,'validation':{'offline':'passed','hardware':'not_tested','canonical_source_recovered':True}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('input','config','report'):parser.add_argument('--'+k,type=Path,required=True)
    parser.add_argument('--output',type=Path);parser.add_argument('--check',action='store_true')
    parser.add_argument('--version',default='1.11.10.10');args=parser.parse_args()
    if not args.check and args.output is None:parser.error('--output is required for a build')
    paths=[p.resolve() for p in (args.input,args.config,args.report,args.output) if p]
    if len(set(paths))!=len(paths):parser.error('input/config/report/output paths must be distinct')
    config=json.loads(args.config.read_text());source=load_image(args.input)
    with tempfile.TemporaryDirectory(prefix='m10v-gr4-native-') as tmp:
        rtos,icons,report=prepare(source,config,Path(tmp))
        if not args.check:
            from gr4_editor.versions import version_word
            candidate,package=repack_image(source,rtos,new_icon_bytes=icons,new_version=version_word(args.version),allow_older=True)
            target=Path(tmp)/'readback.bin';target.write_bytes(candidate);loaded=load_image(target)
            meta=_metadata(loaded.rtos)
            if canonical_base(loaded.rtos)!=source.rtos or meta['m10v']['initial_state_hex']!=initial_state(config['configuration']).hex():raise ValueError('GR4 final package independent readback failed')
            runtime=report['runtime'];at=runtime['base']-BASE
            if sha(loaded.rtos[at:at+runtime['code_bytes']])!=runtime['code_sha256']:raise ValueError('GR4 final packaged code differs')
            report.update(candidate_sha256=sha(candidate),candidate_bytes=len(candidate),version=loaded.internal_version,package=package)
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(candidate)
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('ready','model','filename','camera_tested')}))
if __name__=='__main__':main()
