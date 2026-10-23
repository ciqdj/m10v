#!/usr/bin/env python3
"""Run production stamp across layouts with ASan/UBSan and row guards."""
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include <stdlib.h>
#include <assert.h>
#include "m10v_library.c"
int main(void){
    static const uint32_t sizes[][2]={{6000,4000},{4000,6000},{320,240},{240,320},{96,64},{32,24},{8,8}};
    char name[24];m10v_library_date date={2026,10,20,23,59};
    for(uint32_t size=0;size<7;++size){
        uint32_t w=sizes[size][0],h=sizes[size][1],stride=w+16,bytes=stride*h;
        uint8_t *y=malloc(bytes+32),*uv=malloc(bytes+32);assert(y&&uv);
        m10v_library_image image={y,uv,bytes,bytes,w,h,stride};
        for(uint32_t c=32;c<=126;c+=23){
            for(uint32_t n=0;n<23;++n)name[n]=(char)(32+(c-32+n)%95);name[23]=0;
            for(uint32_t corner=0;corner<4;++corner)for(uint32_t mode=0;mode<3;++mode)for(uint32_t format=0;format<4;++format){
                for(uint32_t i=0;i<bytes+32;++i){y[i]=73;uv[i]=129;}
                m10v_library_state state;m10v_library_init(&state);
                state.stamp=mode;state.format=format;state.reserved=1;state.corner=corner;state.color=corner;
                stamp(&image,&state,&date,name);
                for(uint32_t row=0;row<h;++row)for(uint32_t x=w;x<stride;++x){assert(y[row*stride+x]==73);assert(uv[row*stride+x]==129);}
                for(uint32_t i=bytes;i<bytes+32;++i){assert(y[i]==73);assert(uv[i]==129);}
            }
        }
        free(y);free(uv);
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'probe.c';source.write_text(HARNESS)
    out=Path(tmp)/'probe'
    subprocess.run([shutil.which('clang') or 'clang','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'native/gr3'),str(source),*[str(ROOT/'native/gr3'/f) for f in ['halation_core.c','film_5207.c','film_harman.c','film_curated.c','film_newstocks.c','film_style_filters_0.c','film_style_filters_1.c']],'-o',str(out)],check=True)
    subprocess.run([str(out)],check=True)
print('Production C stamp: ASan/UBSan and row/tail guards passed.')
