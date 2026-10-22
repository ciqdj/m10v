#include "m10v_configuration.h"
#include "m10v_hdf.h"
#include "m10v_hdf_configuration.h"
#include "m10v_sd.h"
#include "m10v_storage.h"
#include "../gr3/m10v_sd_library.h"
#define CONFIG_MAGIC 0x47524346u
typedef struct {
    uint32_t magic,bytes;
    m10v_library_state state;
    uint32_t offsets[5];
    uint8_t records[];
} configuration;
_Static_assert(sizeof(configuration)==132,"GR II configuration ABI");
static configuration *published;
static int32_t mutex_id;
static uint32_t frame_seed;
static const uint8_t carriers[5]={9,10,11,18,8};
int gr2_configuration_is_carrier(uint32_t tone){
 for(uint32_t i=0;i<5u;i++)if(tone==carriers[i])return 1;
 return 0;
}
static int span(const void *p,uint32_t n,uint32_t alignment){uintptr_t v=(uintptr_t)p;return v&&!(v&(alignment-1))&&n<=UINTPTR_MAX-v;}
static void copy(void *out,const void *in,uint32_t n){for(uint32_t i=0;i<n;i++)((uint8_t *)out)[i]=((const uint8_t *)in)[i];}
static int lock(void){return mutex_id>0&&((int32_t (*)(int32_t,int32_t))(uintptr_t)0xA0066D94u)(mutex_id,0)==0;}
static void unlock(void){((int32_t (*)(int32_t))(uintptr_t)0xA00671B8u)(mutex_id);}
static int create(void){
    if(mutex_id>0)return 1;
    /* Same attribute2/nonrecursive mutex as the official wrapper, without its
     * fatal metadata allocator/assertion path. Called only by the UI owner. */
    const struct {uint16_t attribute,ceiling;uint32_t reserved;} descriptor={2,0,0};
    int32_t id=((int32_t (*)(const void *))(uintptr_t)0xA00665CCu)(&descriptor);
    if(id<=0)return 0;
    mutex_id=id;return 1;
}
int gr2_configuration_publish(const m10v_library_state *state,const uint8_t *const records[5]){
    if(!span(state,sizeof(*state),4)||!span(records,20,4)||!m10v_library_valid(state))return 0;
    uint32_t count=0;
    for(uint32_t i=0;i<5;i++){
        uint32_t id=state->slots[i].film;
        if(id>M10V_FILM_COUNT){
            if(!span(records[i],M10V_SD_RECORD_BYTES,1)||m10v_sd_record(records[i],M10V_SD_RECORD_BYTES,id)!=id)return 0;
            count++;
        }else if(records[i])return 0;
    }
    uint32_t bytes=sizeof(configuration)+count*M10V_SD_RECORD_BYTES;
    configuration *next=gr2_allocate(bytes);if(!next)return 0;
    next->magic=CONFIG_MAGIC;next->bytes=bytes;copy(&next->state,state,sizeof(*state));
    uint32_t offset=sizeof(configuration);
    for(uint32_t i=0;i<5;i++){
        uint32_t id=next->state.slots[i].film;next->offsets[i]=0;
        if(id>M10V_FILM_COUNT){
            next->offsets[i]=offset;copy((uint8_t *)next+offset,records[i],M10V_SD_RECORD_BYTES);
            if(m10v_sd_record((uint8_t *)next+offset,M10V_SD_RECORD_BYTES,id)!=id){gr2_release(next);return 0;}
            offset+=M10V_SD_RECORD_BYTES;
        }
    }
    if(!m10v_library_valid(&next->state)||!create()||!lock()){gr2_release(next);return 0;}
    configuration *old=published;published=next;unlock();gr2_release(old);return 1;
}
int gr2_configuration_read(m10v_library_state *out){
    if(!span(out,sizeof(*out),4)||!lock())return 0;
    configuration *current=published;int ok=current&&current->magic==CONFIG_MAGIC;
    if(ok){
        uintptr_t a=(uintptr_t)out,b=(uintptr_t)current;
        ok=!(a<b+current->bytes&&b<a+sizeof(*out));
        if(ok)copy(out,&current->state,sizeof(*out));
    }
    unlock();return ok;
}
int gr2_configuration_freeze(uint8_t *context,uint32_t seed){
    uint32_t body=gr2_image_owner_bytes(context);if(body!=0xfb8cu&&body!=0x12b8cu&&body!=GR2_IMAGE_BODY_BYTES)return 0;
    m10v_gr2_frame existing;
    if(gr2_frame_read(context,&existing))return !context[0x408]||context[0x408]==carriers[existing.slot];
    uint32_t slot=0;while(slot<5&&context[0x408]!=carriers[slot])slot++;
    if(slot==5||!lock())return 0;
    configuration *current=published;int ok=0;
    if(current&&current->magic==CONFIG_MAGIC){
        if(!seed){frame_seed++;if(!frame_seed)frame_seed++;seed=frame_seed;}
        uint32_t offset=current->offsets[slot];
        if(current->state.slots[slot].film<=M10V_FILM_COUNT)ok=gr2_frame_freeze(context,&current->state,slot,seed);
        else if(offset>=sizeof(configuration)&&offset<=current->bytes&&M10V_SD_RECORD_BYTES<=current->bytes-offset)
            ok=gr2_frame_freeze_custom(context,&current->state,slot,seed,(const uint8_t *)current+offset);
    }
    unlock();return ok;
}
int gr2_configuration_begin(uint8_t *context){
 uint32_t body=gr2_image_owner_bytes(context);
 if(body!=0xfb8cu&&body!=0x12b8cu&&body!=GR2_IMAGE_BODY_BYTES)return 0;
 uint32_t bytes=body==0xfb8cu?128u:128u+M10V_SD_RECORD_BYTES;
 for(uint32_t i=0;i<bytes;i++)((volatile uint8_t *)context)[0xfb0cu+i]=0;
 return gr2_configuration_freeze(context,0);
}
int gr2_configuration_clear(void){
    if(!lock())return 0;
    configuration *old=published;published=0;unlock();gr2_release(old);return 1;
}

extern uint32_t gr2_producer_original(uint8_t *,uint32_t);
uint32_t gr2_producer_active(uint8_t *context,uint32_t argument){
    gr2_hdf_configuration_freeze(context);
    if(gr2_configuration_freeze(context,0))return gr2_producer_run(context,argument,0,0);
    return gr2_producer_original(context,argument);
}

int gr2_configuration_reload(void){
    m10v_library_state state;if(!gr2_load_state(&state))return 0;
    uint32_t count=0;for(uint32_t i=0;i<5;i++)if(state.slots[i].film>M10V_FILM_COUNT)count++;
    uint8_t *work=count?gr2_allocate(count*M10V_SD_RECORD_BYTES):0;
    if(count&&!work)return 0;
    const uint8_t *records[5];uint32_t offset=0;
    for(uint32_t i=0;i<5;i++){
        records[i]=0;if(state.slots[i].film<=M10V_FILM_COUNT)continue;
        if(!gr2_sd_custom_record(&state,i,work+offset,M10V_SD_RECORD_BYTES)){gr2_release(work);return 0;}
        records[i]=work+offset;offset+=M10V_SD_RECORD_BYTES;
    }
    int ok=gr2_configuration_publish(&state,records);gr2_release(work);return ok;
}

int gr2_configuration_names(uint16_t out[5][96]){
    if(!span(out,5*96*2,2)||!lock())return 0;
    configuration *current=published;int ok=current&&current->magic==CONFIG_MAGIC;
    if(ok){uintptr_t a=(uintptr_t)out,b=(uintptr_t)current;ok=!(a<b+current->bytes&&b<a+5*96*2);}
    uint16_t next[5][96];
    if(ok)for(uint32_t i=0;i<5;i++){
        uint32_t id=current->state.slots[i].film,offset=current->offsets[i];
        const char *name=id<=M10V_FILM_COUNT?m10v_library_name(id):0;
        uint32_t limit=95;
        if(id>M10V_FILM_COUNT&&offset>=sizeof(configuration)&&offset<=current->bytes&&M10V_SD_RECORD_BYTES<=current->bytes-offset){
            name=(const char *)current+offset+16;limit=23;
        }
        if(!name){ok=0;break;}
        uint32_t n=0;for(;n<limit&&name[n];n++)next[i][n]=(uint8_t)name[n];
        if(!n||name[n]){ok=0;break;}
        for(;n<96;n++)next[i][n]=0;
    }
    if(ok)copy(out,next,5*96*2);
    unlock();return ok;
}
