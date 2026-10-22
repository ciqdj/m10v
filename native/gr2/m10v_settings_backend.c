#include "m10v_settings_backend.h"
#include "m10v_configuration.h"
#include "m10v_effect_names.h"
#include "../gr3/m10v_sd_library.h"
_Static_assert(sizeof(gr2_settings_backend)==4112,"GR II settings backend ABI");
static int activate(void){
    return gr2_initialize_state()&&gr2_configuration_reload()&&(!gr2_effect_names_enabled()||gr2_effect_names_refresh());
}
static int load(void *context,m10v_library_state *state){
    (void)context;return activate()&&gr2_configuration_read(state)?0:-1;
}
static int store(void *context,const m10v_library_state *state){
    (void)context;return gr2_save_state(state)&&activate()?0:-1;
}
static uint32_t item(void *context,uint32_t index){
    gr2_settings_backend *backend=context;
    if(!backend||index>=256)return 0;
    if(!backend->attempted){backend->attempted=1;if(!gr2_sd_catalog_open(&backend->manifest))return 0;}
    const gr2_pack_manifest *m=&backend->manifest;
    if(m->magic!=0x4752324du||index>=m->count||m10v_sd_header(m->header,m->size)!=m->count)return 0;
    return m10v_sd_u32(m->header+64+12*index);
}
static int install(void *context,uint32_t index,uint32_t expected,uint32_t slot){
    gr2_settings_backend *backend=context;
    if(!backend||!backend->attempted)return -1;
    if(gr2_sd_install(&backend->manifest,index,expected,slot))return -1;
    return activate()?0:-1;
}
static int stamp(void *context,uint32_t mode,uint32_t format,uint32_t corner,uint32_t color){
    m10v_library_state state;
    if(load(context,&state))return -1;
    return m10v_library_stamp(&state,mode,format,corner,color,store,context);
}
static int name_stamp(void *context,uint32_t enabled){
    m10v_library_state state;
    if(load(context,&state))return -1;
    return m10v_library_film_name_stamp(&state,enabled,store,context);
}
void gr2_settings_backend_refresh(gr2_settings_backend *backend){
    if(backend){backend->attempted=0;backend->manifest.magic=0;}
}
int gr2_settings_backend_bind(gr2_settings_backend *backend,m10v_settings_ops *ops){
    uintptr_t b=(uintptr_t)backend,o=(uintptr_t)ops;
    if(!b||!o||(b&3)||(o&3)||sizeof(*backend)>UINTPTR_MAX-b||sizeof(*ops)>UINTPTR_MAX-o||
       (b<o+sizeof(*ops)&&o<b+sizeof(*backend)))return 0;
    for(uint32_t i=0;i<sizeof(*backend);i++)((uint8_t *)backend)[i]=0;
    ops->context=backend;ops->load=load;ops->item=item;ops->install=install;ops->stamp=stamp;ops->film_name_stamp=name_stamp;
    return 1;
}

void gr2_detail_backend_bind(gr2_detail_ops *ops){if(ops){ops->context=0;ops->load=load;ops->store=store;}}
