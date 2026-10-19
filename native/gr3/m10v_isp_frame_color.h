#ifndef M10V_ISP_FRAME_COLOR_H
#define M10V_ISP_FRAME_COLOR_H
#include <stdint.h>
/* Relative transform of the current stock matrix, then RGB curves, then
 * relative post transform. Caller owns the complete 0x9000-byte R2Y frame.
 * This is a parameter writer, not an arbitrary 3-D LUT accelerator. */
typedef struct {
    int16_t matrix_q13[9], post_q9[9];
    uint16_t curves[3][256];
} m10v_isp_frame_target;
/* gamma is the ORIGINAL initialized object, read-only. No shared state, heap,
 * or mutation of the original cached object. Must run after stock Still Make.
 * Zero means rejected before writing, one means applied. */
int m10v_isp_frame_apply(const void *gamma, void *frame,
                         const m10v_isp_frame_target *target, uint32_t color_space);
#endif
