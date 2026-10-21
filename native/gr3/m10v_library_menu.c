/* M10V menu adapters for the exact official ImageControlController ABI.
 * Count/index/max adapters are called only from this controller; the global
 * stock model APIs remain unchanged for ADJ and detail controllers.
 * Browsing private entries never writes a private ID to stock tone storage.
 * Explicit confirmation commits a validated journal and then activates one of
 * the five real stock slots. The original controller owns view allocation.
 */
#include "m10v_library.h"
#include "m10v_debug.h"
#if M10V_SD_LIBRARY
#include "m10v_sd_library.h"
#endif
#ifndef M10V_NATIVE_BASE
#define M10V_NATIVE_BASE 0x540b6000u
#endif
typedef uint32_t (*get_fn)(uint32_t);
typedef uint32_t (*call2_fn)(uint32_t, uint32_t);
typedef uint32_t (*call3_fn)(uint32_t, uint32_t, uint32_t);
typedef uint32_t (*root_fn)(void);
static const uint8_t tones[5] = {12,18,19,20,21};
/* The persistent catalog keeps IDs 1..65 for existing journals. Only the
 * curated 800T and original 32 simulations are offered for replacement. */
static const uint8_t counts[22] = {13,7,46,5,4,7,5,4,4,4,3,9,9,9,0,5,3,9,6,9,2,3};
static uint8_t *model(void) {
    uint32_t root = ((root_fn)0x5320ad88u)();
    return (uint8_t *)(uintptr_t)((get_fn)0x5320ba9cu)(root);
}
static int supported(const uint8_t *m) {
    return (uintptr_t)m == 0x55068200u && m[0x1b] == 0;
}
static uint32_t mode(const uint8_t *m) { return supported(m) && m[0x1d] <= 21 ? m[0x1d] : 0; }
static uint32_t slot(const uint8_t *m) {
    /* Byte 0x1e is padding after the stock last member at 0x1c. Keep
     * the original m[0] entry snapshot intact for stock cancellation. */
    uint32_t tone = mode(m) && m[0x1e] ? m[0x1e] : m[0];
    for (uint32_t i = 0; i < 5; ++i) if (tone == tones[i]) return i;
    return 0;
}
static uint32_t group_count(uint32_t group,const uint8_t *m){
    if(group==1){m10v_library_state state;return m10v_camera_library_load(&state)>=0&&(state.slots[slot(m)].film==33||state.slots[slot(m)].film==67||state.slots[slot(m)].film==68)?6:5;}
    (void)m;
    return counts[group];
}
uint32_t m10v_menu_count(uint32_t address) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((get_fn)(M10V_NATIVE_BASE + 0x80u))(address);
    return group_count(mode(m),m);
}
uint32_t m10v_menu_max_count(void) { return 46; }
uint32_t m10v_menu_index(uint32_t address, uint32_t index) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
    uint32_t group = mode(m);
    if (!group) return index == 12 ? 128 : ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
    if (index >= group_count(group,m)) return 0;
    static const uint8_t first[15] = {0,129,144,176,180,184,208,192,196,200,218,224,224,224,233};
    if(group==1&&index>=2)index++;
    if(group==2)return index==0?213:index<=13?(index<=3?287+index:340+index):256+index-14;
    if(group==1&&index==5)return 300;
    if(group==1&&index==6){m10v_library_state s;
        if(m10v_camera_library_load(&s)>=0){uint32_t film=s.slots[slot(m)].film;return film==68?340:film==67?339:214;}
        return 214;}
    if(group==21)return 341+index;
    if(group==3&&index==4)return 301;
    if(group==15)return index<4?302+index:306;
    if(group==16)return 310+index;
    if(group==17||group==19)return 224+index;
    if(group==18)return 320+index;
    if(group==20)return 330+index;

    return first[group]+index;
}
static uint32_t resource(uint32_t tone) {
    if(tone>=344&&tone<=353)return (M10V_SD_LIBRARY?978:937)+tone-344;
    if(tone==288)return 911;
    if(tone==289||tone==290)return 930+tone-289;
    if(tone==339)return 932;
    if(tone>=340&&tone<=343)return 933+tone-340;
    if(tone==300)return 912;
    if(tone>=301&&tone<=305)return 913+tone-301;
    if(tone==306)return 929;
    if(tone>=310&&tone<=312)return 918+tone-310;
    if(tone>=320&&tone<=325)return 921+tone-320;
    if(tone>=330&&tone<=331)return 927+tone-330;
    if(tone>=256&&tone<288)return 879+tone-256;
    if(tone==214)return 861;
    if(tone>=218&&tone<222)return 862+tone-218;
    if(tone>=224&&tone<233)return 866+tone-224;
    if(tone>=233&&tone<237)return 875+tone-233;
    if (tone == 213) return 860;
    if (tone >= 144 && tone < 176) return 786 + tone - 144;
    for (uint32_t i = 0; i < 5; ++i) if (tone == tones[i]) return 818 + i;
    if (tone == 128) return 825;
    if (tone >= 129 && tone < 134) return 826 + tone - 129;
    if (tone >= 176 && tone < 180) return 831 + tone - 176;
    if (tone >= 180 && tone < 184) return 835 + tone - 180;
    if (tone >= 184 && tone < 191) return 839 + tone - 184;
    if (tone >= 192 && tone < 196) return 846 + tone - 192;
    if (tone >= 196 && tone < 200) return 850 + tone - 196;
    if (tone >= 200 && tone < 204) return 854 + tone - 200;
    if (tone >= 208 && tone < 213) return 818 + tone - 208;
    return 0;
}
static uint32_t film_resource(uint32_t film) {
    if (film >= 1 && film <= 32) return 786 + film - 1;
    if (film == 66) return 911;
    if (film >= 69 && film <= 78) return (M10V_SD_LIBRARY?978:937)+film-69;
    if (film >= 67 && film <= 68) return 930+film-67;
    if (film == 33) return 860;
    if (film >= 34 && film <= 65) return 879 + film - 34;
    return 0;
}
uint32_t m10v_menu_name(uint32_t translator, uint32_t tone) {
    for (uint32_t i = 0; i < 5; ++i) {
        if ((tone == tones[i] || tone == 208 + i) && supported(model())) {
            m10v_library_state state;
            /* Load initializes the compiled defaults even when storage is
             * unavailable. Never index a catalog with an unchecked journal. */
            m10v_camera_library_load(&state);
            if (m10v_library_valid(&state)) {
#if M10V_SD_LIBRARY
                if(state.slots[i].film>M10V_FILM_COUNT)return 991+i;
#endif
                return film_resource(state.slots[i].film);
            }
        }
    }
    uint32_t id = resource(tone);
    return id ? id : ((call2_fn)(M10V_NATIVE_BASE + 0x10u))(translator, tone);
}
uint32_t m10v_menu_value_name(uint32_t translator, uint32_t value) {
    if (mode(model()) && (value == 23 || value == 24)) return value == 23 ? 858 : 859;
    return ((call2_fn)(M10V_NATIVE_BASE + 0x20u))(translator, value);
}
uint32_t m10v_menu_icon(uint32_t translator, uint32_t tone) {
    if(tone>=144 && tone<176)return 671+tone-144;
    if(tone>=344&&tone<=353)return 739+tone-344;
    if(tone>=288&&tone<=290)return 736+tone-288;
    if(tone==213)return 703;
    if(tone>=256 && tone<288)return 704+tone-256;
    uint8_t *m=model();
    if(supported(m))for(uint32_t i=0;i<5;i++)if(tone==tones[i] || tone==208+i){
        m10v_library_state state;
        if(m10v_camera_library_load(&state)>=0){
#if M10V_SD_LIBRARY
            if(state.slots[i].film>M10V_FILM_COUNT)return 754;
#endif
            return 670+state.slots[i].film;
        }
    }
    return tone==128?671:tone>=128?0x224:((call2_fn)(M10V_NATIVE_BASE + 0x30u))(translator, tone);
}
uint32_t m10v_menu_value_icon(uint32_t translator, uint32_t value) {
    return ((call2_fn)(M10V_NATIVE_BASE + 0x40u))(translator, value);
}
uint32_t m10v_menu_focus(uint32_t controller, uint32_t index) {
    uint8_t *m = model();
    M10V_LOG(30,controller,index,m[0],(uint32_t)m[0x1d]|((uint32_t)m[0x1e]<<8));
    uint32_t result=0;
    if (!(supported(m) && (mode(m) || index == 12)))
        result=((call2_fn)(M10V_NATIVE_BASE + 0xa0u))(controller, index);
    M10V_LOG(31,controller,index,result,(uint32_t)m[0x1d]|((uint32_t)m[0x1e]<<8));
    return result;
}
static void redraw(uint32_t controller) {
    M10V_LOG(50,controller,0,0,0);
    ((get_fn)0x531ac074u)(controller);
    uint32_t view = *(const uint32_t *)(uintptr_t)(controller + 0x174u);
    uint8_t *m=model();uint32_t group=mode(m),selected=0,target=slot(m);
    if(group==6)selected=target;
    else if(group>=2&&group!=10){
        m10v_library_state state;
        if(m10v_camera_library_load(&state)>=0){const m10v_slot *v=&state.slots[target];
            /* Hidden historical looks stay active until an explicit confirm.
             * Their browsing cursor safely starts at 800T without a write. */
            if(group==2)selected=v->film==33?0:v->film>=66?v->film-65:v->film>=34?v->film-20:0;
            else if(group==3)selected=v->grain;else if(group==4)selected=0;
            else if(group==5)selected=state.stamp;else if(group==7)selected=state.format;
            else if(group==8)selected=state.corner;else if(group==9)selected=state.color;
            else if(group>=16)selected=((const uint8_t *)&state.effects[target])[group-16];
            else if(group==11)selected=v->halo_gain;else if(group==12)selected=v->halo_spread;
            else if(group==13)selected=v->halo_threshold;else if(group==14)selected=v->halo_profile;
        }
    }
    ((call2_fn)0x53395430u)(view, selected);
    M10V_LOG(51,controller,selected,group,target);
}
static void failure(uint32_t controller) {
    uint32_t caption = *(const uint32_t *)(uintptr_t)(controller + 0x160u);
    ((call3_fn)0x53396f80u)(caption, 824, 0);
}
#if M10V_DEBUG_MODE
static uint32_t menu_confirm_impl(uint32_t controller) {
#else
uint32_t m10v_menu_confirm(uint32_t controller) {
#endif
    uint8_t *m = model();
    if (!supported(m)) return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
    uint32_t view = *(const uint32_t *)(uintptr_t)(controller + 0x174u);
    uint32_t index = ((get_fn)0x53394820u)(view), group = mode(m);
    if (!group) {
        if (index != 12) return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
        /* The stock entry snapshot at m[0] does not follow live browsing.
         * Capture the actual tone before switching to the private menu. */
        uint32_t active = ((get_fn)0x532bd6b4u)((uint32_t)(uintptr_t)m);
        m[0x1e] = 0;
        for (uint32_t i = 0; i < 5; ++i) if (active == tones[i]) m[0x1e] = (uint8_t)active;
        m[0x1d] = 1; redraw(controller); return 0;
    }
    if (index == group_count(group,m)) {
        m[0x1d] = group==1?0:group==21?1:group==16?3:group>=17?15:group==15?1:group>=11?10:group==10?1:group>=7?5:1;
        redraw(controller); return 0;
    }
    if (index == (uint32_t)group_count(group,m) + 1) {
        m[0x1d] = 0; return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
    }
    if (index >= group_count(group,m)) return 0;
    if (group == 1) {
        if(index>=2)index++;
        m10v_library_state s;uint32_t extra=m10v_camera_library_load(&s)>=0&&s.slots[slot(m)].film==68?21:10;
        m[0x1d]=(uint8_t)(index==6?extra:index==5?15:index==4?6:index+2);redraw(controller);return 0; }
    if(group==3&&index==4){m[0x1d]=16;redraw(controller);return 0;}
    if (group == 6) {
        m[0x1e] = tones[index];
        ((call2_fn)(M10V_NATIVE_BASE + 0x00u))((uint32_t)(uintptr_t)m, tones[index]);
        m[0x1d] = 1; redraw(controller); return 0;
    }
    if (group == 5 && index >= 3) {
        if (index <= 5) m[0x1d] = (uint8_t)(index + 4);
        else m[0x1d] = 1;
        redraw(controller); return 0;
    }
    if(group==10){m[0x1d]=(uint8_t)(11+index);redraw(controller);return 0;}
    if(group==15&&index<4){m[0x1d]=(uint8_t)(17+index);redraw(controller);return 0;}
    m10v_library_state state;
    if (m10v_camera_library_load(&state) < 0) { failure(controller); return 0; }
    uint32_t target = slot(m); int result;
    M10V_LOG(60,controller,index,group,target);
    if(group==21)result=m10v_camera_library_effects(&state,target,6,index);
    else if(group>=16)result=m10v_camera_library_effects(&state,target,group-16,index);
    else if(group==15)result=m10v_camera_library_effects(&state,target,5,0);
    else if(group>=11){const m10v_slot *v=&state.slots[target];
        result=m10v_camera_library_halation(&state,target,group==11?index:v->halo_gain,group==12?index:v->halo_spread,group==13?index:v->halo_threshold,group==14?index:v->halo_profile);
    }
    else if (group == 2) result = m10v_camera_library_select(&state, target, index==0?33:index<=13?65+index:20+index);
    else if (group == 3) result = m10v_camera_library_texture(&state, target, index, state.slots[target].soft);
    else if (group == 4) return M10V_LIBRARY_INVALID;
    else result = m10v_camera_library_stamp(&state, group == 5 ? index : state.stamp,
        group == 7 ? index : state.format, group == 8 ? index : state.corner, group == 9 ? index : state.color);
    M10V_LOG(61,controller,(uint32_t)result,group,state.slots[target].film);
    if (result) { failure(controller); return 0; }
    if (group == 2) ((call2_fn)(M10V_NATIVE_BASE + 0x00u))((uint32_t)(uintptr_t)m, tones[target]);
    m[0x1d] = group==21?1:group==16?3:group>=15?15:group>=11?10:group >= 7 || group == 5 ? 5 : 1;
    redraw(controller); return 0;
}
#if M10V_DEBUG_MODE
uint32_t m10v_menu_confirm(uint32_t controller) {
    uint8_t *m=model();M10V_LOG(40,controller,m[0],m[0x1d],m[0x1e]);
    uint32_t result=menu_confirm_impl(controller);
    M10V_LOG(41,controller,result,m[0x1d],m[0x1e]);return result;
}
static uint32_t menu_key_impl(uint32_t controller, uint32_t event) {
#else
uint32_t m10v_menu_key(uint32_t controller, uint32_t event) {
#endif
    uint8_t *m = model();
    if (supported(m)) {
        uint16_t key = *(const uint16_t *)(uintptr_t)event;
        if (key == 0xd8) return m10v_menu_confirm(controller);
        if (mode(m) && key == 0xde) return 0;
        if (key == 0x89 || key == 0xda) m[0x1d] = 0;
        if (mode(m) && (key == 0x86 || key == 0x87)) {
            m[0x1d] = 0; return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
        }
    }
    return ((call2_fn)(M10V_NATIVE_BASE + 0x50u))(controller, event);
}
#if M10V_DEBUG_MODE
uint32_t m10v_menu_key(uint32_t controller,uint32_t event) {
    uint16_t key=*(const uint16_t *)(uintptr_t)event;
    uint8_t *m=model();M10V_LOG(20,controller,key,m[0],m[0x1d]);
    uint32_t result=menu_key_impl(controller,event);
    M10V_LOG(21,controller,key,result,m[0x1d]);return result;
}
#endif
uint32_t m10v_menu_enter(uint32_t controller) {
    M10V_LOG(10,controller,0,0,0);
    uint8_t *m = model(); if (supported(m)) { m[0x1d] = 0; m[0x1e] = 0; }
    uint32_t result=((get_fn)(M10V_NATIVE_BASE + 0xb0u))(controller);
    M10V_LOG(11,controller,result,m[0],m[0x1d]);return result;
}

#if M10V_SD_LIBRARY
/* The resource adapter reserves 80 bytes in the ORIGINAL getter's stack frame.
 * Descriptor + UTF-16 live until that getter restores SP from FP; no retained
 * heap pointer, writable ROM descriptor or shared scratch is published. The
 * first 16 bytes remain available for original outgoing stack arguments. */
uint32_t m10v_menu_custom_resource(uint32_t resource,uint32_t *out){
 if(resource<991||resource>995||!out)return 0;
 char name[24];const char *text="Custom LUT";m10v_library_state state;
 if(m10v_camera_library_load(&state)>=0&&m10v_sd_camera_custom_name(&state,resource-991,name,sizeof(name)))text=name;
 uint16_t *utf=(uint16_t *)(out+2);uint32_t n=0;
 for(;n<23&&text[n];n++)utf[n]=(uint8_t)text[n];utf[n++]=0;
 out[0]=n|0x100u;out[1]=(uint32_t)(uintptr_t)utf;
 return (uint32_t)(uintptr_t)out;
}
#endif
