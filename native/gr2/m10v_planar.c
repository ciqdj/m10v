#include "m10v_model.h"
/* In-place planar <-> paired chroma. Split off (3^k-1)/2 samples,
 * rotate the middle blocks, and traverse the power-of-three cycle leaders.
 * Each split consumes at least one third of the remaining samples: total
 * pixel traffic is O(n), with O(log n) stack and no frame-sized scratch. */
static void reverse(uint8_t *p,uint32_t n){
    for(uint32_t i=0;i<n/2;i++){uint8_t t=p[i];p[i]=p[n-1-i];p[n-1-i]=t;}
}
static void rotate(uint8_t *p,uint32_t left,uint32_t total){
    reverse(p,left);reverse(p+left,total-left);reverse(p,total);
}
static void cycle(uint8_t *p,uint32_t modulus,uint32_t leader,int inverse){
    uint32_t index=leader,half=modulus>>1;uint8_t carry=p[index-1];
    do {
        uint32_t next=inverse?((index&1)?(index>>1)+half+1:index>>1):
                              (index>half?index-(modulus-index):index*2);
        uint8_t previous=p[next-1];p[next-1]=carry;carry=previous;index=next;
    }while(index!=leader);
}
static void shuffle(uint8_t *p,uint32_t n,int inverse){
    if(n<2)return;
    uint32_t power=3,limit=2*n+1;
    while(power<=limit/3)power*=3;
    uint32_t block=power>>1;
    if(inverse)shuffle(p+2*block,n-block,1);
    else rotate(p+block,n-block,n);
    if(inverse)for(uint32_t i=0;i<2*block;i+=2){uint8_t t=p[i];p[i]=p[i+1];p[i+1]=t;}
    for(uint32_t leader=1;leader<power;leader*=3)cycle(p,power,leader,inverse);
    if(inverse)rotate(p+block,block,n);
    else {
        for(uint32_t i=0;i<2*block;i+=2){uint8_t t=p[i];p[i]=p[i+1];p[i+1]=t;}
        shuffle(p+2*block,n-block,0);
    }
}
int gr2_chroma_shuffle(uint8_t *p,uint32_t samples,int inverse){
    if(!p||!samples||samples>UINT32_MAX/2||samples*2>UINTPTR_MAX-(uintptr_t)p||(inverse!=0&&inverse!=1))return 0;
    shuffle(p,samples,inverse);return 1;
}
