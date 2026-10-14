"""Build an instrumented capture adapter and bounded on-camera SD trace writer.

No guard is relaxed. All pixel writes remain the reviewed original adapter's.
"""
import json,hashlib,subprocess,tempfile,re
from pathlib import Path
from scripts.build_gr3_halation import ROOT,FLAGS,extract_text
RETURN_STAGES=['context_range','recipe_range','sequence_mode','topology','request_ranges',
 'record_tone_format','geometry','plane_ranges','raw_dimensions_range','raw_dimensions',
 'raw_source_range','plane_alias','preview_geometry','preview_ranges','scratch_range','scratch_alias']
def build_trace():
    source=(ROOT/'native/gr3/halation_camera.c').read_text()
    source=source.replace('void m10v_capture_800t(', 'void m10v_capture_800t_trace(')
    count=0
    def replace(m):
        nonlocal count
        count+=1
        return '{((void (*)(uint32_t,uint32_t,const uint32_t *))0x540bc800u)('+str(count)+',context,0);return;}'
    source=re.sub(r'\breturn;',replace,source)
    if count!=len(RETURN_STAGES):raise ValueError(f'guard trace drift: {count}')
    before='''uint32_t trace_stats[8];
    for(uint32_t k=0;k<8;k++)trace_stats[k]=0;
    uint32_t sx=(width>>6)&~1u,sy=height>>6;
    if(!sx)sx=2;if(!sy)sy=1;
    for(uint32_t r=0;r<height;r+=sy)for(uint32_t x=0;x<width;x+=sx) {
        uint32_t light=image.y[r*stride+x];
        if(light>trace_stats[1])trace_stats[1]=light;
        trace_stats[2]+=light>216;trace_stats[3]++;
        trace_stats[4]+=image.chroma[r*stride+x+1];trace_stats[6]+=light;
    }
    '''
    source=source.replace('int result =',before+'int result =')
    after='''trace_stats[0]=(uint32_t)result;
    for(uint32_t r=0;r<height;r+=sy)for(uint32_t x=0;x<width;x+=sx) {
        trace_stats[5]+=image.chroma[r*stride+x+1];trace_stats[7]+=image.y[r*stride+x];
    }
    '''
    source=source.replace('if (result == M10V_HALO_OK)',after+'if (result == M10V_HALO_OK)')
    source=source[:source.rfind('}')]+ '\n    ((void (*)(uint32_t,uint32_t,const uint32_t *))0x540bc800u)(100,context,trace_stats);\n'+source[source.rfind('}'):]
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);c=tmp/'trace_adapter.c';c.write_text(source)
        for name,path,entry,extra in [('logger',ROOT/'native/gr3/halation_trace.c','m10v_trace_800t',[]),
            ('adapter',c,'m10v_capture_800t_trace',['-DM10V_CAMERA_ORDER=1','-DM10V_CAMERA_TONE=18','-DM10V_CAMERA_STRENGTH=2','-I'+str(ROOT/'native/gr3')])]:
            obj=tmp/(name+'.o');subprocess.run(['clang',*FLAGS,*extra,'-c',str(path),'-o',str(obj)],check=True,capture_output=True)
            code=extract_text(obj.read_bytes(),entry)
            if len(code)>(0x400 if name=='logger' else 0x1c00):raise ValueError('trace code exceeds placement')
            yield name,code
if __name__=='__main__':
    out=ROOT/'builds/gr3-800t-live-debug';out.mkdir(exist_ok=True)
    for name,code in build_trace():
        (out/(name+'-arm.bin')).write_bytes(code)
        print(name,len(code),hashlib.sha256(code).hexdigest())
    (out/'stages.json').write_text(json.dumps({str(i+1):n for i,n in enumerate(RETURN_STAGES)},indent=2)+'\n')
