#include "m10v_model.h"
typedef int32_t (*rtos_alloc_fn)(int32_t,uint32_t,void **);
typedef int32_t (*rtos_free_fn)(int32_t,void *);
static int32_t pool(void){
    const uint32_t *system=(const uint32_t *)(uintptr_t)0xA00C2BA4u;
    const uint8_t *p=(const uint8_t *)(uintptr_t)system[1];
    if(!p||*(const uint32_t *)p!=0x4D504C20u||p[4]!=0)return -1;
    return *(const int16_t *)(p+0x14);
}
static int pointer_in_pool(const void *p){
    uintptr_t v=(uintptr_t)p;return !(v&3)&&v>=0xA0900010u&&v<0xA0B00010u;
}
void *gr2_allocate(uint32_t bytes){
    if(!bytes||bytes>0x200000u)return 0;
    int32_t id=pool();void *out=0;if(id<=0)return 0;
    if(((rtos_alloc_fn)(uintptr_t)0xA006798Cu)(id,bytes,&out)<0)return 0;
    if(!pointer_in_pool(out)||bytes>0xA0B00010u-(uintptr_t)out)return 0;
    return out;
}
int32_t gr2_release(void *p){
    if(!p)return 0;
    int32_t id=pool();if(id<=0||!pointer_in_pool(p))return -1;
    return ((rtos_free_fn)(uintptr_t)0xA0067BE8u)(id,p);
}
int gr2_read_clock(uint16_t output[6]){
    if(!output)return 0;
    uint16_t fields[6]={0,0,0,0,0,0};
    ((void (*)(uint16_t *))(uintptr_t)0xA00341A9u)(fields);
    if(!gr2_date_valid(fields))return 0;
    for(uint32_t i=0;i<6;i++)output[i]=fields[i];
    return 1;
}
