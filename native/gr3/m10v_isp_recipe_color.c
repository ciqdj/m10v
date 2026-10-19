#include "m10v_isp_recipe_color.h"
#include <stddef.h>
#if M10V_ISP_NATIVE_LOOK
#include "m10v_isp_native_look.h"
#if M10V_ISP_NATIVE_GRAIN_MODE
#include "m10v_isp_native_effects.h"
#endif
#endif
#ifndef M10V_ISP_RECIPE_COLOR_OBSERVER
#define M10V_ISP_RECIPE_COLOR_OBSERVER 1
#endif
#ifndef M10V_ISP_RECIPE_COLOR_PRODUCER
#define M10V_ISP_RECIPE_COLOR_PRODUCER 0
#endif
#if M10V_ISP_SHARED_HDF
extern uint32_t m10v_hdf_settings(uint32_t,uint32_t);
#endif
_Static_assert(sizeof(m10v_isp_recipe_color)==M10V_SAVE_COLOR_BYTES,"recipe color extent");
static m10v_isp_recipe_color *owned(void *recipe){
    uintptr_t address=(uintptr_t)recipe;
    if((address&3)||address<0x55000000u||address>0x80000000u-M10V_SAVE_RECIPE_EXTENDED_BYTES||
       *(uint32_t *)recipe!=0x53d0fc90u)return 0;
    /* Factory extension initializes trace first; never probe beyond stock
     * object based on a coincidental vptr alone. Integration installs the sole
     * factory allocation hook together with this module. */
    if(*(uint32_t *)((uint8_t *)recipe+M10V_SAVE_RECIPE_BYTES)!=M10V_SAVE_TRACE_MAGIC)return 0;
    return (m10v_isp_recipe_color *)((uint8_t *)recipe+M10V_SAVE_COLOR_OFFSET);
}
static m10v_isp_recipe_color *from_context(const void *context){
    if(!context)return 0;
    uintptr_t parameters=((const uint32_t *)context)[0x30/4];
    if(parameters<0x1a8)return 0;
    return owned((void *)(parameters-0x1a8));
}
int m10v_isp_frame_recipe_snapshot(void *recipe,const m10v_library_state *state){
    m10v_isp_recipe_color *s=owned(recipe);
    if(!s||!m10v_library_valid(state))return 0;
    if(s->magic==M10V_ISP_RECIPE_COLOR_MAGIC&&s->busy)return 0;
    s->magic=0;
    for(uint32_t i=0;i<sizeof(*state);i++)((uint8_t *)&s->state)[i]=((const uint8_t *)state)[i];
    s->version=1;s->bytes=sizeof(*s);s->status=M10V_ISP_RECIPE_READY;
    s->sequence=state->sequence;s->tone=0;s->si=0;
    s->info=0;s->tuning=0;s->busy=0;
#if M10V_ISP_NATIVE_GRAIN_MODE
    s->native_grain.magic=0;
#endif
    s->magic=M10V_ISP_RECIPE_COLOR_MAGIC;
    return 1;
}
int m10v_isp_frame_recipe_state(void *recipe,m10v_library_state *out){
    m10v_isp_recipe_color *s=owned(recipe);
    if(!s||!out||s->magic!=M10V_ISP_RECIPE_COLOR_MAGIC||s->version!=1||s->bytes!=sizeof(*s))return 0;
    for(uint32_t i=0;i<sizeof(*out);i++)((uint8_t *)out)[i]=((const uint8_t *)&s->state)[i];
    return m10v_library_valid(out);
}
int m10v_isp_frame_recipe_producer(void *recipe){
#if M10V_ISP_RECIPE_COLOR_PRODUCER
    m10v_isp_recipe_color *s=owned(recipe);
    if(!s)return 0;
    if(s->magic==M10V_ISP_RECIPE_COLOR_MAGIC)return 1;
    /* Only called by the two post-mutex producer adapters, before queueing.
     * Never called from factory/ISP/encoder callbacks. */
    m10v_library_state state;
    if(m10v_camera_library_load(&state)<0)return 0;
    return m10v_isp_frame_recipe_snapshot(recipe,&state);
#else
    (void)recipe;return 0;
#endif
}
int m10v_isp_frame_recipe_begin(const void *context,void *tuning,void *info){
    m10v_isp_recipe_color *s=from_context(context);
    if(!s||s->magic!=M10V_ISP_RECIPE_COLOR_MAGIC||s->version!=1||s->bytes!=sizeof(*s)||
       (s->status!=M10V_ISP_RECIPE_READY&&s->status!=M10V_ISP_RECIPE_APPLIED&&s->status!=M10V_ISP_RECIPE_OBSERVED)||s->busy||!tuning||!info||
       *(uint32_t *)tuning!=0x53dbd8a0u)return 0;
#if M10V_ISP_NATIVE_LOOK
    /* Native completion is consumed by this recipe's own JPEG. Cross-recipe
     * configurations keep their original software route until the ownership
     * transfer itself supplies an explicit completion handoff. Stock setup
     * writes R+99c=C+30, R+9a0=C+34: C begins at R+96c. */
    if((uintptr_t)context!=(uintptr_t)s-M10V_SAVE_COLOR_OFFSET+0x96cu)return 0;
#endif
    const uint8_t *f=info;
    uint32_t si=*(const uint32_t *)(f+0x82d0);
    if(f[0x82ac]>1||!si||((const uint32_t *)context)[0x34/4]!=si){
        s->status=M10V_ISP_RECIPE_MISMATCH;return 0;
    }
    const uint8_t *shot=(const uint8_t *)(uintptr_t)si;
    if(f[0x82ac])shot+=0x71248;
    uint32_t tone=shot[0x77c],slot;
    if(tone==12)slot=0;else if(tone>=18&&tone<=21)slot=tone-17;
    else return 0;
    s->tone=tone;s->si=si;
#if !M10V_ISP_RECIPE_COLOR_OBSERVER && !M10V_ISP_NATIVE_LOOK
    uint32_t film=s->state.slots[slot].film;
    if(film<34||film>65){s->status=M10V_ISP_RECIPE_UNSUPPORTED;return 0;}
    uint16_t knots[99];
    if(m10v_library_tables(film,s->target.matrix_q13,s->target.post_q9,
                           &s->target.curves[0][0],knots)){
        s->status=M10V_ISP_RECIPE_REJECTED;return 0;
    }
#else
    (void)slot;
#endif
    s->info=(uint32_t)(uintptr_t)info;s->tuning=(uint32_t)(uintptr_t)tuning;
    s->busy=1;return 1;
}
int m10v_isp_frame_recipe_finish(const void *context){
    m10v_isp_recipe_color *s=from_context(context);
    if(!s||s->magic!=M10V_ISP_RECIPE_COLOR_MAGIC||!s->busy)return 0;
    void *info=(void *)(uintptr_t)s->info;
    const uint8_t *tuning=(const uint8_t *)(uintptr_t)s->tuning;
    s->info=0;s->tuning=0;s->busy=0;
    if(!info||!tuning||*(const uint32_t *)tuning!=0x53dbd8a0u){s->status=M10V_ISP_RECIPE_MISMATCH;return 0;}
#if M10V_ISP_RECIPE_COLOR_OBSERVER
    s->status=M10V_ISP_RECIPE_OBSERVED;return 1;
#else
    const void *gamma=*(const void *const *)(tuning+0x17c);
    /* Original536dc474..494 derives context color space from shot+7be==1.
     * The temporary Still Make stack context has returned; retain no pointer. */
    const uint8_t *shot=(const uint8_t *)(uintptr_t)s->si;
    if(((const uint8_t *)info)[0x82ac])shot+=0x71248;
    uint32_t cs=shot[0x7be]==1;
#if M10V_ISP_NATIVE_LOOK
    uint32_t slot=s->tone==12?0:s->tone-17;
    uint32_t film=s->state.slots[slot].film;
    uint32_t exposure=film==68?s->state.effects[slot].film_exposure:0;
    uint32_t generation=(uint32_t)(uintptr_t)s^s->si^s->sequence;
    if(!generation)generation=1;
    m10v_isp_native_look look;
    int result=m10v_isp_native_look_prepare(&look,film,exposure,generation)&&
        m10v_isp_native_look_apply(&look,gamma,info,cs)&&
        m10v_isp_native_look_matches(&look,film,exposure,generation);
#else
    int result=m10v_isp_frame_apply(gamma,info,&s->target,cs);
#endif
    s->status=result?M10V_ISP_RECIPE_APPLIED:M10V_ISP_RECIPE_REJECTED;
    return result;
#endif
}

uint32_t m10v_isp_frame_recipe_completed(void *recipe,uint32_t shooting,uint32_t tone,const m10v_library_state *state){
#if M10V_ISP_NATIVE_LOOK
    m10v_isp_recipe_color *s=owned(recipe);
    if(!s||!state||!shooting||s->magic!=M10V_ISP_RECIPE_COLOR_MAGIC||s->version!=1||s->bytes!=sizeof(*s)||
       s->busy||
       !m10v_library_valid(state)||s->sequence!=state->sequence)return 0;
    for(uint32_t i=0;i<sizeof(*state);i++)if(((const uint8_t *)state)[i]!=((const uint8_t *)&s->state)[i])return 0;
    uint32_t completed=s->status==M10V_ISP_RECIPE_APPLIED&&s->si==shooting&&s->tone==tone?M10V_NATIVE_COLOR:0;
#if M10V_ISP_NATIVE_GRAIN_MODE
    uint32_t slot=tone==12?0:tone>=18&&tone<=21?tone-17:5;
    if(slot<5&&s->native_grain.magic==0x374e5247u&&s->native_grain.si==shooting&&s->native_grain.tone==tone&&s->native_grain.done&&
       s->native_grain.grain==state->slots[slot].grain&&s->native_grain.size==state->effects[slot].grain_size)completed|=M10V_NATIVE_GRAIN;
#endif
    return completed;
#else
    (void)recipe;(void)shooting;(void)tone;(void)state;return 0;
#endif
}

#if M10V_ISP_NATIVE_GRAIN_MODE
static int grain_ram(uintptr_t p,uint32_t bytes){return !(p&3)&&p>=0x55000000u&&p<=0x80000000u-bytes;}
static m10v_isp_recipe_color *grain_owner(const void *context){
    if(!grain_ram((uintptr_t)context,0x40)||*(const uint32_t *)context!=0x53d0fc60u)return 0;
    m10v_isp_recipe_color *s=from_context(context);
    uint32_t si=((const uint32_t *)context)[0x34/4];
    if(s&&(uintptr_t)context!=(uintptr_t)s-M10V_SAVE_COLOR_OFFSET+0x4320u)return 0;
    if(!s||s->magic!=M10V_ISP_RECIPE_COLOR_MAGIC||s->version!=1||s->bytes!=sizeof(*s)||s->busy||!grain_ram(si,0x94c)||!m10v_library_valid(&s->state))return 0;
    return s;
}
#endif
uint32_t m10v_isp_frame_recipe_grain_settings(const void *context,void *params,uint32_t execution){
#if M10V_ISP_NATIVE_GRAIN_MODE
    if(execution>1||!grain_ram((uintptr_t)context,0x40)||*(const uint32_t *)context!=0x53d0fc60u||!grain_ram((uintptr_t)params,0x34))return 0;
    uint32_t hdf=0;
#if M10V_ISP_SHARED_HDF
    hdf=m10v_hdf_settings((uint32_t)(uintptr_t)context,(uint32_t)(uintptr_t)params);
#endif
    uint32_t si=((const uint32_t *)context)[0x34/4];
    if(!grain_ram(si,0x94c))return hdf;
    uint32_t tone=*(const uint8_t *)(uintptr_t)(si+0x77c),slot;
    if(tone==12)slot=0;else if(tone>=18&&tone<=21)slot=tone-17;else return hdf;
    uintptr_t values=((const uint32_t *)params)[0x10/4];
    if(!grain_ram(values,12))return hdf;
    /* The carrier's original menu grain is not the queued custom grain. If
     * ownership/planning rejects, keep native grain off for the CPU route. */
    ((int16_t *)values)[2]=0;
    m10v_isp_recipe_color *s=grain_owner(context);
    if(!s)return hdf;
    uint32_t grain=s->state.slots[slot].grain,size=s->state.effects[slot].grain_size;
    if(grain>3||size>2)return hdf;
    if(execution){
        if(s->native_grain.magic!=0x374e5247u||!s->native_grain.planned||s->native_grain.si!=si||s->native_grain.tone!=tone||s->native_grain.grain!=grain||s->native_grain.size!=size)return hdf;
        s->native_grain.armed=1;s->native_grain.done=0;s->native_grain.noise_ready=0;
    }else{
        s->native_grain.magic=0x374e5247u;s->native_grain.si=si;s->native_grain.tone=tone;s->native_grain.grain=grain;s->native_grain.size=size;
        s->native_grain.planned=1;s->native_grain.armed=0;s->native_grain.noise_ready=0;s->native_grain.done=0;
    }
    ((int16_t *)values)[2]=(int16_t)(grain?4-grain:0);
    return grain!=0||hdf;
#else
    (void)context;(void)params;(void)execution;return 0;
#endif
}
int m10v_isp_frame_recipe_grain_noise(const void *context,uint8_t *noise,uint32_t bytes,uint32_t width,uint32_t height,uint32_t stride){
#if M10V_ISP_NATIVE_GRAIN_MODE
    m10v_isp_recipe_color *s=grain_owner(context);
    if(!s||s->native_grain.magic!=0x374e5247u||!s->native_grain.armed||!s->native_grain.grain||s->native_grain.si!=((const uint32_t *)context)[0x34/4])return 0;
    int result=m10v_isp_native_effects_noise_shape(noise,bytes,width,height,stride,s->native_grain.size);
    s->native_grain.noise_ready=result==0;return result==0;
#else
    (void)context;(void)noise;(void)bytes;(void)width;(void)height;(void)stride;return 0;
#endif
}
void m10v_isp_frame_recipe_grain_done(const void *context,const void *params,uint32_t result){
#if M10V_ISP_NATIVE_GRAIN_MODE
    m10v_isp_recipe_color *s=grain_owner(context);
    if(!s||s->native_grain.magic!=0x374e5247u||!s->native_grain.armed)return;
    uintptr_t values=grain_ram((uintptr_t)params,0x34)?((const uint32_t *)params)[0x10/4]:0;
    s->native_grain.done=result==1&&s->native_grain.grain&&grain_ram(values,12)&&
      ((const int16_t *)values)[2]==(int16_t)(4-s->native_grain.grain)&&s->native_grain.si==((const uint32_t *)context)[0x34/4];
    s->native_grain.armed=0;
#else
    (void)context;(void)params;(void)result;
#endif
}

/* Only the LiveView Make vtable callback calls this. It updates bounded ISP
 * parameter banks, never photo pixels, live buffers, filesystem or graph queues. */
int m10v_isp_frame_live_color(void *tuning,void *info){
#if M10V_ISP_LIVE_COLOR
    uintptr_t a=(uintptr_t)tuning,f=(uintptr_t)info;
    if((a&3)||(f&3)||a<0x55000000u||a>0x80000000u-0x400u||f<0x55000000u||f>0x80000000u-0x9000u||
       *(const uint32_t *)tuning!=0x53dbd938u)return 0;
    const uint8_t *frame=info;
    uint32_t si=*(const uint32_t *)(frame+0x82d0);
    if(frame[0x82ac]>1||!si||si<0x55000000u||si>0x80000000u-0x80000u)return 0;
    const uint8_t *shot=(const uint8_t *)(uintptr_t)si+(frame[0x82ac]?0x71248:0);
    uint32_t tone=shot[0x77c],slot=tone==12?0:tone>=18&&tone<=21?tone-17:5;
    if(slot>=5)return 0;
    m10v_library_state state;if(!m10v_camera_library_preview(&state))return 0;
    uint32_t film=state.slots[slot].film,exposure=film==68?state.effects[slot].film_exposure:0;
    m10v_isp_native_look look;
    return m10v_isp_native_look_prepare(&look,film,exposure,state.sequence+1u)&&
        m10v_isp_native_look_apply(&look,*(const void *const *)((const uint8_t *)tuning+0x17c),info,shot[0x7be]==1);
#else
    (void)tuning;(void)info;return 0;
#endif
}

void m10v_isp_frame_live_prepare(void *tuning,const void *info){
#if M10V_ISP_LIVE_COLOR
    uintptr_t a=(uintptr_t)tuning,f=(uintptr_t)info;
    if((a&3)||(f&3)||a<0x55000000u||a>0x80000000u-0x400u||f<0x55000000u||f>0x80000000u-0x9000u||*(const uint32_t *)tuning!=0x53dbd938u)return;
    const uint8_t *frame=info;uint32_t si=*(const uint32_t *)(frame+0x82d0);
    if(frame[0x82ac]>1||si<0x55000000u||si>0x80000000u-0x80000u)return;
    uint32_t tone=*((const uint8_t *)(uintptr_t)si+(frame[0x82ac]?0x71248:0)+0x77c);
    uint32_t slot=tone==12?0:tone>=18&&tone<=21?tone-17:5;
    m10v_library_state state;
    if(slot<5&&m10v_camera_library_preview(&state)&&state.slots[slot].film>=33){
        /* Original Live Make otherwise reuses already written frame banks.
         * Invalidate only its internal cached-tone byte; original Make restores
         * it from unmodified SI and reconstructs clean base parameters. */
        ((uint8_t *)tuning)[0x1a8]=255;
    }
#else
    (void)tuning;(void)info;
#endif
}
