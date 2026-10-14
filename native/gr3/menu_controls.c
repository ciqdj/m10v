/* Dedicated 800T settings. The stock B26-byte record/file remains untouched.
 * Only the current record's allocation gains this 32-byte private tail.
 * ABI: op0 pack capture,1 get UI field,2 set,3 render row,4 factory default,
 * 5 protected record address,6 raw active settings,7 reset selected UI set.
 * A missing/unwritable SD card still permits RAM controls until power-off. */
#include <stdint.h>
#define INLINE static inline __attribute__((always_inline))
#define DEFAULT 0x2533u
#define READY 0x38564d52u
#define FOOTER 0x43464738u
INLINE int ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
INLINE int code(uint32_t p,uint32_t n){return !(p&3)&&p>=0x53000000u&&p<0x540b6000u&&n<=0x540b6000u-p;}
INLINE int valid(uint32_t p){return !(p&0xfffc0000u)&&(p&15)<=8&&((p>>4)&15)<=8&&((p>>8)&15)<=8&&((p>>12)&15)<=3&&((p>>16)&15)<=3;}
INLINE uint32_t checksum(const uint32_t *p){return 0x80073813u^p[3]^(p[4]<<3)^(p[5]<<7);}
INLINE int file(uint32_t *data,int writing){
    typedef uint32_t (*get)(void);
    typedef int (*open)(uint32_t,const char *,uint32_t,uint32_t *,uint32_t *);
    typedef int (*io)(uint32_t,uint32_t,void *,uint32_t,uint32_t *);
    typedef int (*close)(uint32_t,uint32_t,uint32_t *);
    uint32_t m=((get)0x535847d8u)();if(!ram(m,24))return 0;
    uint32_t fs=((uint32_t *)m)[5];if(!ram(fs,4))return 0;
    uint32_t vt=*(uint32_t *)fs;if(!code(vt,44))return 0;
    uint32_t *v=(uint32_t *)vt;uint32_t fn=v[writing?10:9];
    if(!code(v[7],4)||!code(v[8],4)||!code(fn,4))return 0;
    volatile uint32_t name[4];name[0]=0x4d5c3a43u;name[1]=0x38563031u;name[2]=0x2e474643u;name[3]=0x004e4942u;
    uint32_t h=0,e=0;if(!((open)v[7])(fs,(const char *)name,writing?0:1,&h,&e)||!h)return 0;
    int ok=((io)fn)(fs,h,data,32,&e);
    ((close)v[8])(fs,h,&e);return ok;
}
uint32_t m10v_menu_800t(uint32_t op,uint32_t ui,uint32_t arg){
    typedef uint32_t (*get)(void);
    uint32_t m=((get)0x5320b31cu)();
    uint32_t r=ram(m,8)?((uint32_t *)m)[1]:0;
    if(op==5)return ram(r,0xb48)?r:0;
    uint32_t set=0,field=arg,value=arg&255;
    int isui=op==1||op==2||op==3||op==4||op==7;
    if(isui){
        if(!ram(ui,0x1a0)||((uint8_t *)ui)[0x19a]!=8||((uint8_t *)ui)[0x19d]!=0)return 0;
        set=((uint8_t *)ui)[0x199];
        if(op==2)field=arg>>8;
        if(op==3)field=arg>>16;
        if(op==4)field=((uint32_t (*)(uint32_t))0x531b01d0u)(ui)-18;
        if(op!=7&&field>4)return 0;
    }else if(ram(r,0xb48))set=((uint8_t *)r)[0x1c0];
    if(set>2)return 0;
    if(op==4)return (DEFAULT>>(field*4))&15;
    uint32_t packed=DEFAULT;
    volatile uint32_t *p=0;
    if(ram(r,0xb48)){
        p=(volatile uint32_t *)(r+0xb28);
        uint32_t ready=__atomic_load_n(p,__ATOMIC_ACQUIRE);
        if(ready==0){
            uint32_t expected=0;
            if(__atomic_compare_exchange_n(p,&expected,1,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
                uint32_t disk[8];for(uint32_t i=0;i<8;i++)disk[i]=0;
                int ok=file(disk,0)&&disk[0]==READY&&disk[1]==1&&disk[6]==32&&disk[7]==FOOTER&&disk[2]==checksum(disk)&&valid(disk[3])&&valid(disk[4])&&valid(disk[5]);
                for(uint32_t i=1;i<8;i++)p[i]=disk[i];
                if(!ok){p[1]=1;p[2]=0;p[3]=DEFAULT;p[4]=DEFAULT;p[5]=DEFAULT;p[6]=32;p[7]=FOOTER;}
                __atomic_store_n(p,READY,__ATOMIC_RELEASE);ready=READY;
            }
        }
        if(ready==READY){packed=__atomic_load_n(p+3+set,__ATOMIC_ACQUIRE);if(!valid(packed))packed=DEFAULT;}
        else p=0; /* Never wait for a filesystem initializer on the capture task. */
    }
    if(op==2||op==7){
        if(!p)return 0;
        if(op==2){if(value>(field<3?8u:3u))return 0;packed=(packed&~(15u<<(field*4)))|(value<<(field*4));}else packed=DEFAULT;
        __atomic_store_n(p+3+set,packed,__ATOMIC_RELEASE);
        uint32_t disk[8];disk[0]=READY;disk[1]=1;disk[6]=32;disk[7]=FOOTER;
        for(uint32_t i=3;i<6;i++){disk[i]=__atomic_load_n(p+i,__ATOMIC_ACQUIRE);if(!valid(disk[i]))disk[i]=DEFAULT;}
        disk[2]=checksum(disk);file(disk,1);return 1;
    }
    if(op==1)return (packed>>(field*4))&15;
    if(op==6)return packed;
    if(op==3){
        value=(packed>>(field*4))&15;
        /* ASCII values work in every stock language/font. Captions localized separately. */
        uint16_t txt[16];for(uint32_t i=0;i<16;i++)txt[i]=0;
        if(field<3){txt[0]='0'+value;txt[1]='/';txt[2]='8';}
        else if(value==0){txt[0]='O';txt[1]='f';txt[2]='f';}
        else if(value==1){txt[0]='L';txt[1]='o';txt[2]='w';}
        else if(value==2){txt[0]=field==3?'N':'M';txt[1]=field==3?'a':'i';txt[2]=field==3?'t':'d';}
        else{txt[0]='H';txt[1]='i';txt[2]='g';txt[3]='h';}
        uint32_t list=*(uint32_t *)(ui+0x194);
        if(!ram(list,4))return 0;
        uint32_t row=((uint32_t (*)(uint32_t,uint32_t))0x53394758u)(list,arg&255);
        if(!ram(row,4))return 0;
        ((void (*)(uint32_t,uint32_t,const uint16_t *))0x5339e2f8u)(row,0x1e3,txt);return 1;
    }
    uint32_t gain=packed&15,radius=(packed>>4)&15,threshold=(packed>>8)&15;
    uint32_t profile=(packed>>12)&15,grain=(packed>>16)&15;
    profile=profile==0?0:profile==1?1:profile==2?4:7;
    grain=grain==0?0:grain==1?2:grain==2?4:8;
    if(ui==1)gain>>=1;
    return 0x80000000u|gain|(radius<<4)|(threshold<<8)|(grain<<12)|(profile<<16);
}
