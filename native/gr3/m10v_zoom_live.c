/* GR III 2.10 crop controls. Runtime state and captions are owned by caller. */
typedef unsigned int u32;
#define FN(a,t) ((t)(a))
extern u32 m10v_zoom_camera_bits(u32 slot);
extern u32 m10v_zoom_camera_slot(u32 bits);
extern int m10v_zoom_camera_select(u32 slot);
extern u32 m10v_zoom_native_front_bits(u32 controller);
extern u32 m10v_zoom_native_back_bits(u32 backend);
extern u32 m10v_zoom_native_set_bits(u32 controller,u32 bits);
static u32 controller(void) {
    return FN(0x5320b31c,u32 (*)(u32))(FN(0x5320ad88,u32 (*)(void))());
}
static u32 backend(void) {
    return *(u32 *)FN(0x53525d5c,u32 (*)(void))();
}
/* Used after editing the active slot; reports backend acceptance. */
int m10v_zoom_live_apply(u32 slot) {
    if(slot>2) return -1;
    u32 bits=m10v_zoom_camera_bits(slot);
    (void)m10v_zoom_native_set_bits(controller(),bits);
    if(m10v_zoom_native_back_bits(backend())!=bits) return -1;
    (void)m10v_zoom_camera_select(slot);
    return 0;
}
/* Both stock menu and ADJ use index0,1,2, where2 means uncropped. */
u32 m10v_zoom_set(u32 ignored,u32 slot) {
    (void)ignored;
    if(slot>2) return 0;
    u32 bits=m10v_zoom_camera_bits(slot);
    u32 result=m10v_zoom_native_set_bits(controller(),bits);
    if(m10v_zoom_native_back_bits(backend())==bits)
        (void)m10v_zoom_camera_select(slot);
    return result;
}
u32 m10v_zoom_selected(u32 ignored,u32 slot) {
    (void)ignored;
    if(slot>2) return 0;
    return m10v_zoom_camera_slot(m10v_zoom_native_front_bits(controller()))==slot;
}
/* Preserve the native bounded retry, setup side effect and final still check.
 * A rejected candidate advances to the following slot, just as stock does. */
void m10v_zoom_cycle(void) {
    u32 root=FN(0x5320ad88,u32 (*)(void))();
    u32 front=FN(0x5320b31c,u32 (*)(u32))(root),back=backend();
    u32 slot=m10v_zoom_camera_slot(m10v_zoom_native_back_bits(back));
    if(slot>2) slot=2;
    for(u32 attempt=0;attempt<3;attempt++) {
        (void)FN(0x5320b7fc,u32 (*)(u32))(root);
        slot=slot==2?0:slot+1;
        u32 bits=m10v_zoom_camera_bits(slot);
        (void)m10v_zoom_native_set_bits(front,bits);
        if(m10v_zoom_native_back_bits(back)==bits) {
            (void)m10v_zoom_camera_select(slot);
            break;
        }
    }
    u32 still=FN(0x53243e40,u32 (*)(u32))(front);
    FN(0x536b93d0,void (*)(u32,u32,u32,u32,u32))(!still,0x53b21184,0x53b21164,0x64b,0x53b4de08);
}
