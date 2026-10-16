#include "film_harman.h"
#include "film_harman_data.h"
static uint8_t clip(int x){return (uint8_t)(x<0?0:x>255?255:x);}
void m10v_harman_rgb(uint32_t variant,const uint8_t rgb[3],uint8_t out[3]){
    if(variant>3){for(uint32_t c=0;c<3;c++)out[c]=rgb[c];return;}
    const uint8_t (*table)[3]=m10v_harman_luts[variant];
    uint32_t p[3],f[3],order[3]={0,1,2};
    for(uint32_t c=0;c<3;c++){uint32_t q=(uint32_t)rgb[c]*14;p[c]=q/255;if(p[c]>13)p[c]=13;f[c]=q-p[c]*255;}
    for(uint32_t i=0;i<2;i++)for(uint32_t j=i+1;j<3;j++)if(f[order[j]]>f[order[i]]){uint32_t t=order[i];order[i]=order[j];order[j]=t;}
    uint32_t index=(p[0]*15+p[1])*15+p[2];
    static const uint32_t step[3]={225,15,1};
    int total[3];for(uint32_t c=0;c<3;c++)total[c]=(int)table[index][c]*255;
    for(uint32_t i=0;i<3;i++){
        uint32_t next=index+step[order[i]];
        for(uint32_t c=0;c<3;c++)total[c]+=(int)f[order[i]]*((int)table[next][c]-(int)table[index][c]);
        index=next;
    }
    for(uint32_t c=0;c<3;c++)out[c]=clip((total[c]+127)/255);
}
