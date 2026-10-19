/* Install only at the locked Still Make gamma BL with its explicit adapter. */
#include "m10v_isp_frame_color.h"
#include "m10v_isp_color_hook.h"
#include <stdint.h>
#include "m10v_isp_slot_config.h"
int m10v_isp_frame_color_hook_gamma(void *gamma,const void *context,
                                     void *frame,const void *tuning){
    /* Adapter completes original gamma at its unchanged stack geometry. */
    const uint8_t *f=frame;
    if(!gamma||!context||!f||!tuning||*(const uint32_t *)tuning!=0x53dbd8a0u||
       f[0x82ac]!=1)return M10V_ISP_COLOR_FOREIGN;
    const uint8_t *si=*(const uint8_t *const *)(f+0x82d0);
    if(!si)return M10V_ISP_COLOR_FOREIGN;
    uint32_t tone=si[0x71248+0x77c],slot;
    if(tone==12)slot=0;
    else if(tone>=18&&tone<=21)slot=tone-17;
    else return M10V_ISP_COLOR_FOREIGN;
    /* Selection is original per-frame metadata; immutable targets are baked
     * into this candidate's ROM. No mutable menu/SD state is consulted here.
     * Thus another frame cannot replace this frame's target while queued. */
    if(!m10v_isp_slot_enabled[slot])return M10V_ISP_COLOR_DISABLED;
    return m10v_isp_frame_apply(gamma,frame,&m10v_isp_slot_targets[slot],
                               ((const uint8_t *)context)[0x52])?
        M10V_ISP_COLOR_APPLIED:M10V_ISP_COLOR_REJECTED;
}
