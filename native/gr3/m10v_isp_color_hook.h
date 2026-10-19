#ifndef M10V_ISP_COLOR_HOOK_H
#define M10V_ISP_COLOR_HOOK_H
#include <stdint.h>
/* Internal AAPCS helper; not the stock gamma ABI. The call-site adapter must
 * finish stock gamma Make at the original SP, then pass r0=Gamma, r1=context,
 * r2=info, r3=ImageTuning. Returned status is diagnostic only; the adapter
 * restores original gamma r0-r12, LR and SP before continuing Still Make. */
enum m10v_isp_color_hook_result {
    M10V_ISP_COLOR_FOREIGN=0,
    M10V_ISP_COLOR_APPLIED=1,
    M10V_ISP_COLOR_DISABLED=-1,
    M10V_ISP_COLOR_REJECTED=-2
};
int m10v_isp_frame_color_hook_gamma(void *gamma,const void *context,
                                  void *frame,const void *tuning);
#endif
