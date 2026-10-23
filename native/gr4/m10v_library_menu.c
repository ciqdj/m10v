/* M10V menu adapters for the exact official ImageControlController ABI.
 * Count/index/max adapters are called only from this controller; the global
 * stock model APIs remain unchanged for ADJ and detail controllers.
 * Browsing private entries never writes a private ID to stock tone storage.
 * Explicit confirmation commits a validated journal and then activates one of
 * the five real stock slots. The original controller owns view allocation.
 */
#include "../gr3/m10v_library.h"
#include "../gr3/m10v_debug.h"
#ifndef M10V_NATIVE_BASE
#define M10V_NATIVE_BASE 0x540b6000u
#endif
typedef uint32_t (*get_fn)(uint32_t);
typedef uint32_t (*call2_fn)(uint32_t, uint32_t);
typedef uint32_t (*call3_fn)(uint32_t, uint32_t, uint32_t);
typedef uint32_t (*root_fn)(void);
static const uint8_t tones[5] = {36,37,38,39,40};
/* The persistent catalog keeps IDs 1..65 for existing journals. Only the
 * curated 800T and original 32 simulations are offered for replacement. */
static const uint8_t counts[22] = {13,7,46,0,0,7,5,4,4,4,3,9,9,9,0,0,0,0,0,0,0,3};
static uint8_t *model(void) {
    uint32_t root = ((root_fn)0x5323ea84u)();
    return (uint8_t *)(uintptr_t)((get_fn)0x5323f928u)(root);
}
static int supported(const uint8_t *m) {
    return (uintptr_t)m == 0x5508a6dcu && m[0x1f] == 0;
}
static uint32_t mode(const uint8_t *m) { return supported(m) && m[0x21] <= 21 ? m[0x21] : 0; }
static uint32_t slot(const uint8_t *m) {
    /* Byte 0x22 is padding after the stock last member at 0x20. Keep
     * the original m[0] entry snapshot intact for stock cancellation. */
    uint32_t tone = mode(m) && m[0x22] ? m[0x22] : m[0];
    for (uint32_t i = 0; i < 5; ++i) if (tone == tones[i]) return i;
    return 0;
}
static uint32_t root_rows(const uint8_t *m,uint32_t index){
    m10v_library_state state;uint32_t film=0;
    if(m10v_camera_library_load(&state)>=0)film=state.slots[slot(m)].film;
    uint32_t rows[4]={129,132,133,0},n=3;
    if(film==33||film==67||film==68)rows[n++]=film==68?340:film==67?339:214;
    return index==0xffffffffu?n:index<n?rows[index]:0;
}
static uint32_t group_count(uint32_t group,const uint8_t *m){
    if(group==1)return root_rows(m,0xffffffffu);
    return counts[group];
}
uint32_t m10v_menu_count(uint32_t address) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((get_fn)(M10V_NATIVE_BASE + 0x80u))(address);
    return mode(m)?group_count(mode(m),m):((get_fn)(M10V_NATIVE_BASE + 0x80u))(address)+1;
}
uint32_t m10v_menu_max_count(void) { return 46; }
/* GR4 owns three native footer rows; private M10V pages have Back/Done only.
 * This helper replaces only ImageControlController total-active-row lookup. */
uint32_t m10v_menu_rows(uint32_t controller) {
    (void)controller;uint8_t *m=model();
    return m10v_menu_count((uint32_t)(uintptr_t)m)+(mode(m)?2u:3u);
}
uint32_t m10v_menu_index(uint32_t address, uint32_t index) {
    const uint8_t *m = (const uint8_t *)(uintptr_t)address;
    if (!supported(m)) return ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
    uint32_t group = mode(m);
    if (!group) return index == ((get_fn)(M10V_NATIVE_BASE + 0x80u))(address) ? 128 : ((call2_fn)(M10V_NATIVE_BASE + 0x90u))(address, index);
    if (index >= group_count(group,m)) return 0;
    static const uint8_t first[15] = {0,129,144,176,180,184,208,192,196,200,218,224,224,224,233};
    if(group==2)return index==0?213:index<=13?(index<=3?287+index:340+index):256+index-14;
    if(group==1)return root_rows(m,index);
    if(group==21)return 341+index;

    return first[group]+index;
}
static uint32_t resource(uint32_t tone) {
    if(tone>=344&&tone<=353)return 970+tone-344;
    if(tone==288)return 911;
    if(tone==289||tone==290)return 930+tone-289;
    if(tone==339)return 932;
    if(tone>=340&&tone<=343)return 933+tone-340;
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
    if(film>=69&&film<=78)return 970+film-69;
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
            if (m10v_library_valid(&state)) return 238+film_resource(state.slots[i].film);
        }
    }
    uint32_t id = resource(tone);
    return id ? id+238 : ((call2_fn)(M10V_NATIVE_BASE + 0x10u))(translator, tone);
}
uint32_t m10v_menu_value_name(uint32_t translator, uint32_t value) {
    if (mode(model()) && (value == 31 || value == 32)) return value == 31 ? 1096 : 1097;
    return ((call2_fn)(M10V_NATIVE_BASE + 0x20u))(translator, value);
}
uint32_t m10v_menu_icon(uint32_t translator, uint32_t tone, uint32_t flags) {
    /* Native GR4 hides this icon family whenever its third argument is nonzero. */
    if(flags)return 0;
    if(tone>=144 && tone<176)return 1024+tone-144;
    if(tone>=344&&tone<=353)return 1092+tone-344;
    if(tone>=288&&tone<=290)return 1089+tone-288;
    if(tone==213)return 1056;
    if(tone>=256 && tone<288)return 1057+tone-256;
    uint8_t *m=model();
    if(supported(m))for(uint32_t i=0;i<5;i++)if(tone==tones[i] || tone==208+i){
        m10v_library_state state;
        if(m10v_camera_library_load(&state)>=0)return 1023+state.slots[i].film;
    }
    return tone==128?1024:tone>=128?0:((call3_fn)(M10V_NATIVE_BASE + 0x30u))(translator, tone, flags);
}
uint32_t m10v_menu_value_icon(uint32_t translator, uint32_t value) {
    return ((call2_fn)(M10V_NATIVE_BASE + 0x40u))(translator, value);
}
uint32_t m10v_menu_focus(uint32_t controller, uint32_t index) {
    uint8_t *m = model();
    M10V_LOG(30,controller,index,m[0],(uint32_t)m[0x21]|((uint32_t)m[0x22]<<8));
    uint32_t result=0;
    if (!(supported(m) && (mode(m) || index == ((get_fn)(M10V_NATIVE_BASE + 0x80u))((uint32_t)(uintptr_t)m))))
        result=((call2_fn)(M10V_NATIVE_BASE + 0xa0u))(controller, index);
    M10V_LOG(31,controller,index,result,(uint32_t)m[0x21]|((uint32_t)m[0x22]<<8));
    return result;
}
static void redraw(uint32_t controller) {
    M10V_LOG(50,controller,0,0,0);
    ((get_fn)0x531c615cu)(controller);
    uint32_t view = *(const uint32_t *)(uintptr_t)(controller + 0x178u);
    uint8_t *m=model();uint32_t group=mode(m),selected=0,target=slot(m);
    if(group==6)selected=target;
    else if(group>=2&&group!=10){
        m10v_library_state state;
        if(m10v_camera_library_load(&state)>=0){const m10v_slot *v=&state.slots[target];
            /* Hidden historical looks stay active until an explicit confirm.
             * Their browsing cursor safely starts at 800T without a write. */
            if(group==2)selected=v->film==33?0:v->film>=66?v->film-65:v->film>=34?v->film-20:0;
            else if(group==3)selected=v->grain;else if(group==4)selected=v->soft;
            else if(group==5)selected=state.stamp;else if(group==7)selected=state.format;
            else if(group==8)selected=state.corner;else if(group==9)selected=state.color;
            else if(group==21)selected=state.effects[target].film_exposure;
            else if(group==11)selected=v->halo_gain;else if(group==12)selected=v->halo_spread;
            else if(group==13)selected=v->halo_threshold;else if(group==14)selected=v->halo_profile;
        }
    }
    ((call2_fn)0x53571788u)(view, selected);
    M10V_LOG(51,controller,selected,group,target);
}
static void failure(uint32_t controller) {
    uint32_t caption = *(const uint32_t *)(uintptr_t)(controller + 0x164u);
    ((call3_fn)0x5357338cu)(caption, 1062, 0);
}
#if M10V_DEBUG_MODE
static uint32_t menu_confirm_impl(uint32_t controller) {
#else
uint32_t m10v_menu_confirm(uint32_t controller) {
#endif
    uint8_t *m = model();
    if (!supported(m)) return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
    uint32_t view = *(const uint32_t *)(uintptr_t)(controller + 0x178u);
    uint32_t index = ((get_fn)0x53570b6cu)(view), group = mode(m);
    if(group==3||group==4||(group>=15&&group<=20))return 0;
    if (!group) {
        if (index != ((get_fn)(M10V_NATIVE_BASE + 0x80u))((uint32_t)(uintptr_t)m)) return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
        /* The stock entry snapshot at m[0] does not follow live browsing.
         * Capture the actual tone before switching to the private menu. */
        uint32_t active = ((get_fn)0x533b64e0u)((uint32_t)(uintptr_t)m);
        m[0x22] = 0;
        for (uint32_t i = 0; i < 5; ++i) if (active == tones[i]) m[0x22] = (uint8_t)active;
        m[0x21] = 1; redraw(controller); return 0;
    }
    if (index == group_count(group,m)) {
        m[0x21] = group==1?0:group==21?1:group>=11?10:group==10?1:group>=7?5:1;
        redraw(controller); return 0;
    }
    if (index == (uint32_t)group_count(group,m) + 1) {
        m[0x21] = 0; return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
    }
    if (index >= group_count(group,m)) return 0;
    if(group==1){
        uint32_t item=root_rows(m,index);
        m[0x21]=(uint8_t)(item==129?2:item==132?5:item==133?6:item==340?21:10);
        redraw(controller);return 0;
    }
    if (group == 6) {
        m[0x22] = tones[index];
        ((call2_fn)(M10V_NATIVE_BASE + 0x00u))((uint32_t)(uintptr_t)m, tones[index]);
        m[0x21] = 1; redraw(controller); return 0;
    }
    if (group == 5 && index >= 3) {
        if (index <= 5) m[0x21] = (uint8_t)(index + 4);
        else m[0x21] = 1;
        redraw(controller); return 0;
    }
    if(group==10){m[0x21]=(uint8_t)(11+index);redraw(controller);return 0;}
    m10v_library_state state;
    if (m10v_camera_library_load(&state) < 0) { failure(controller); return 0; }
    uint32_t target = slot(m); int result;
    M10V_LOG(60,controller,index,group,target);
    if(group==21)result=m10v_camera_library_effects(&state,target,6,index);
    else if(group>=11){const m10v_slot *v=&state.slots[target];
        result=m10v_camera_library_halation(&state,target,group==11?index:v->halo_gain,group==12?index:v->halo_spread,group==13?index:v->halo_threshold,group==14?index:v->halo_profile);
    }
    else if (group == 2) result = m10v_camera_library_select(&state, target, index==0?33:index<=13?65+index:20+index);
    else result = m10v_camera_library_stamp(&state, group == 5 ? index : state.stamp,
        group == 7 ? index : state.format, group == 8 ? index : state.corner, group == 9 ? index : state.color);
    M10V_LOG(61,controller,(uint32_t)result,group,state.slots[target].film);
    if (result) { failure(controller); return 0; }
    if (group == 2) ((call2_fn)(M10V_NATIVE_BASE + 0x00u))((uint32_t)(uintptr_t)m, tones[target]);
    m[0x21] = group==21?1:group>=11?10:group >= 7 || group == 5 ? 5 : 1;
    redraw(controller); return 0;
}
#if M10V_DEBUG_MODE
uint32_t m10v_menu_confirm(uint32_t controller) {
    uint8_t *m=model();M10V_LOG(40,controller,m[0],m[0x21],m[0x22]);
    uint32_t result=menu_confirm_impl(controller);
    M10V_LOG(41,controller,result,m[0x21],m[0x22]);return result;
}
static uint32_t menu_key_impl(uint32_t controller, uint32_t event) {
#else
uint32_t m10v_menu_key(uint32_t controller, uint32_t event) {
#endif
    uint8_t *m = model();
    if (supported(m)) {
        uint16_t key = *(const uint16_t *)(uintptr_t)event;
        if (key == 0xe0) return m10v_menu_confirm(controller);
        if (mode(m) && key == 0xe6) return 0;
        if (key == 0x8d || key == 0xe2) m[0x21] = 0;
        if (mode(m) && (key == 0x8a || key == 0x8b)) {
            m[0x21] = 0; return ((get_fn)(M10V_NATIVE_BASE + 0x60u))(controller);
        }
    }
    return ((call2_fn)(M10V_NATIVE_BASE + 0x50u))(controller, event);
}
#if M10V_DEBUG_MODE
uint32_t m10v_menu_key(uint32_t controller,uint32_t event) {
    uint16_t key=*(const uint16_t *)(uintptr_t)event;
    uint8_t *m=model();M10V_LOG(20,controller,key,m[0],m[0x21]);
    uint32_t result=menu_key_impl(controller,event);
    M10V_LOG(21,controller,key,result,m[0x21]);return result;
}
#endif
uint32_t m10v_menu_enter(uint32_t controller) {
    M10V_LOG(10,controller,0,0,0);
    uint8_t *m = model(); if (supported(m)) { m[0x21] = 0; m[0x22] = 0; }
    uint32_t result=((get_fn)(M10V_NATIVE_BASE + 0xb0u))(controller);
    M10V_LOG(11,controller,result,m[0],m[0x21]);return result;
}
