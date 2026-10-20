#include "m10v_model.h"
/* Constant-memory planar <-> paired-chroma conversion. The recursive rotations
 * work for arbitrary plane lengths; no frame-size temporary allocation is used.
 * Worst-case byte moves are O(n log n); camera timing is still to be measured. */
static void reverse(uint8_t *p,uint32_t n){
    for(uint32_t i=0;i<n/2;i++){uint8_t t=p[i];p[i]=p[n-1-i];p[n-1-i]=t;}
}
static void rotate(uint8_t *p,uint32_t left,uint32_t total){
    reverse(p,left);reverse(p+left,total-left);reverse(p,total);
}
static void shuffle(uint8_t *p,uint32_t n,int inverse){
    if(n<2)return;
    uint32_t half=n>>1;
    if(!inverse)rotate(p+half,n-half,n);
    shuffle(p,half,inverse);shuffle(p+2*half,n-half,inverse);
    if(inverse)rotate(p+half,half,n);
}
int gr2_chroma_shuffle(uint8_t *p,uint32_t samples,int inverse){
    if(!p||!samples||samples>UINT32_MAX/2||samples*2>UINTPTR_MAX-(uintptr_t)p||(inverse!=0&&inverse!=1))return 0;
    shuffle(p,samples,inverse);return 1;
}
