#ifndef M10V_ISP_MULTIAXIS_H
#define M10V_ISP_MULTIAXIS_H
#include <stdint.h>
/* Native bit patterns, not display-domain matrices. All reserved bits must be
 * zero. Signed coefficients use the original two's-complement field encoding.
 * No pixel fidelity assertion follows from successful register packing. */
typedef struct {
 uint16_t boundaries[16];
 uint8_t selectors[20];
 uint32_t matrix12[60][9];
 uint32_t matrix10[40][9];
 uint8_t control[42];
 uint16_t final9[9];
} m10v_isp_multiaxis_target;
int m10v_isp_multiaxis_apply(void *frame,uint32_t frame_bytes,const m10v_isp_multiaxis_target *target);
#endif
