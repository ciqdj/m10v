/* M10V menu adapters for the exact official ImageControlController ABI.
 * Count/index/max adapters are called only from this controller; the global
 * stock model APIs remain unchanged for ADJ and detail controllers.
 * Browsing private entries never writes a private ID to stock tone storage.
 * Explicit confirmation commits a validated journal and then activates one of
 * the five real stock slots. The original controller owns view allocation.
 */
#include "m10v_library.h"
#include "m10v_debug.h"
#ifndef M10V_SD_LIBRARY
#define M10V_SD_LIBRARY 0
#endif
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
static const uint8_t counts[15] = {13,6,33,4,4,7,5,4,4,4,4,9,9,9,4};
static uint8_t *model(void) {
    uint32_t root = ((root_fn)0x5320ad88u)();
    return (uint8_t *)(uintptr_t)((get_fn)0x5320ba9cu)(root);
}
static int supported(const uint8_t *m) {
    return (uintptr_t)m == 0x55068200u && m[0x1b] == 0;
}
static uint32_t mode(const uint8_t *m) { return supported(m) && m[0x1d] <= (M10V_SD_LIBRARY ? 46 : 14) ? m[0x1d] : 0; }
static uint32_t slot(const uint8_t *m) {
    /* Byte 0x1e is padding after the stock last member at 0x1c. Keep
     * the original m[0] entry snapshot intact for stock cancellation. */
    uint32_t tone = mode(m) && m[0x1e] ? m[0x1e] : m[0];
    for (uint32_t i = 0; i < 5; ++i) if (tone == tones[i]) return i;
    return 0;
}
uint32_t m10v_menu_count(uint32_t address) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((get_fn)(M10V_NATIVE_BASE + 0x80u))(address);
    uint32_t group=mode(m);
#if M10V_SD_LIBRARY
    if(group>=15)return 10;
    if(group==1)return 7;
#endif
    return counts[group];
}
uint32_t m10v_menu_max_count(void) { return 33; }
uint32_t m10v_menu_index(uint32_t address, uint32_t index) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
    uint32_t group = mode(m);
    if (!group) return index == 12 ? 128 : ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
#if M10V_SD_LIBRARY
    if(group>=15){
        if(index<8){uint32_t id=m10v_sd_camera_item(group-15,index);return id?512+id:600;}
        return index==8?601:index==9?602:0;
    }
    if(group==1&&index==6)return 603;
#endif
    if (index >= counts[group]) return 0;
    static const uint8_t first[15] = {0,129,144,176,180,184,208,192,196,200,218,224,224,224,233};
    if(group==2)return index==0?213:256+index-1;
    if(group==1&&index==5)return 214;
    return first[group]+index;
}
static uint32_t film_resource(uint32_t film);
static uint32_t resource(uint32_t tone) {
#if M10V_SD_LIBRARY
    if(tone>=545&&tone<=577)return film_resource(tone-512);
    if(tone>=600&&tone<=603)return 911+tone-600;
#endif
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
            if (m10v_library_valid(&state)) return film_resource(state.slots[i].film);
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
#if M10V_SD_LIBRARY
    if(tone>=545&&tone<=577)return 670+tone-512;
#endif
    if(tone>=144 && tone<176)return 671+tone-144;
    if(tone==213)return 703;
    if(tone>=256 && tone<288)return 704+tone-256;
    uint8_t *m=model();
    if(supported(m))for(uint32_t i=0;i<5;i++)if(tone==tones[i] || tone==208+i){
        m10v_library_state state;
        if(m10v_camera_library_load(&state)>=0)return 670+state.slots[i].film;
    }
    return tone==128?671:tone>=128?0x224:((call2_fn)(M10V_NATIVE_BASE + 0x30u))(translator, tone);
}
uint32_t m10v_menu_value_icon(uint32_t translator, uint32_t value) {
    return ((call2_fn)(M10V_NATIVE_BASE + 0x40u))(translator, value);
}
uint32_t m10v_menu_focus(uint32_t controller, uint32_t index) {
    uint8_t *m = model();
    M10V_LOG(30,controller,index,m[0],(uint32_t)m[0x1d]|((uint32_t)m[0x1e]<<8));
#if M10V_SD_LIBRARY
    if(mode(m)>=15){
        uint32_t id=index<8?m10v_sd_camera_item(mode(m)-15,index):0;
        __atomic_fetch_and(m+0x1f,1,__ATOMIC_RELAXED);
        __atomic_fetch_or(m+0x1f,(uint8_t)(id<<1),__ATOMIC_RELAXED);
        return 0;
    }
#endif
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
            if(group==2)selected=v->film>=33?v->film-33:0;
            else if(group==3)selected=v->grain;else if(group==4)selected=v->soft;
            else if(group==5)selected=state.stamp;else if(group==7)selected=state.format;
            else if(group==8)selected=state.corner;else if(group==9)selected=state.color;
            else if(group==11)selected=v->halo_gain;else if(group==12)selected=v->halo_spread;
            else if(group==13)selected=v->halo_threshold;else if(group==14)selected=v->halo_profile;
        }
    }
#if M10V_SD_LIBRARY
    if(group>=15){
        uint32_t id=m10v_sd_camera_item(group-15,0);
        __atomic_fetch_and(m+0x1f,1,__ATOMIC_RELAXED);
        __atomic_fetch_or(m+0x1f,(uint8_t)(id<<1),__ATOMIC_RELAXED);
    }
#endif
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
#if M10V_SD_LIBRARY
    if(group>=15){
        if(index==10){m[0x1d]=1;redraw(controller);return 0;}
        if(index==11){m[0x1d]=0;return ((get_fn)(M10V_NATIVE_BASE+0x60u))(controller);}
        if(index==8||index==9){
            uint32_t next=index==8?(group>15?group-1:group):(group<46?group+1:group);
            if(next!=group&&m10v_sd_camera_item(next-15,0)){m[0x1d]=(uint8_t)next;redraw(controller);}
            return 0;
        }
        uint32_t cached=__atomic_load_n(m+0x1f,__ATOMIC_RELAXED)>>1;
        uint32_t current=index<8?m10v_sd_camera_item(group-15,index):0;
        if(!cached||cached!=current||m10v_sd_camera_install(group-15,index,cached,slot(m))){failure(controller);return 0;}
        ((call2_fn)(M10V_NATIVE_BASE+0x00u))((uint32_t)(uintptr_t)m,tones[slot(m)]);
        m[0x1d]=1;redraw(controller);return 0;
    }
    if(group==1&&index==6){
        if(!m10v_sd_camera_item(0,0)){failure(controller);return 0;}
        m[0x1d]=15;redraw(controller);return 0;
    }
#endif
    uint32_t group_count=m10v_menu_count((uint32_t)(uintptr_t)m);
    if (index == group_count) {
        m[0x1d] = group==1?0:group>=11?10:group==10?1:group>=7?5:1;
        redraw(controller); return 0;
    }
    if (index == group_count + 1) {
        m[0x1d] = 0; return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
    }
    if (index >= group_count) return 0;
    if (group == 1) { m[0x1d] = (uint8_t)(index==5?10:index == 4 ? 6 : index + 2); redraw(controller); return 0; }
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
    m10v_library_state state;
    if (m10v_camera_library_load(&state) < 0) { failure(controller); return 0; }
    uint32_t target = slot(m); int result;
    M10V_LOG(60,controller,index,group,target);
    if(group>=11){const m10v_slot *v=&state.slots[target];
        result=m10v_camera_library_halation(&state,target,group==11?index:v->halo_gain,group==12?index:v->halo_spread,group==13?index:v->halo_threshold,group==14?index:v->halo_profile);
    }
    else if (group == 2) result = m10v_camera_library_select(&state, target, index + 33);
    else if (group == 3) result = m10v_camera_library_texture(&state, target, index, state.slots[target].soft);
    else if (group == 4) result = m10v_camera_library_texture(&state, target, state.slots[target].grain, index);
    else result = m10v_camera_library_stamp(&state, group == 5 ? index : state.stamp,
        group == 7 ? index : state.format, group == 8 ? index : state.corner, group == 9 ? index : state.color);
    M10V_LOG(61,controller,(uint32_t)result,group,state.slots[target].film);
    if (result) { failure(controller); return 0; }
    if (group == 2) ((call2_fn)(M10V_NATIVE_BASE + 0x00u))((uint32_t)(uintptr_t)m, tones[target]);
    m[0x1d] = group>=11?10:group >= 7 || group == 5 ? 5 : 1;
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
    uint8_t *m = model(); if (supported(m)) { m[0x1d] = 0; m[0x1e] = 0;
#if M10V_SD_LIBRARY
    __atomic_fetch_and(m+0x1f,1,__ATOMIC_RELAXED);
#endif
 }
    uint32_t result=((get_fn)(M10V_NATIVE_BASE + 0xb0u))(controller);
    M10V_LOG(11,controller,result,m[0],m[0x1d]);return result;
}
