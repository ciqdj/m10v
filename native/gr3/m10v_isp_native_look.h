#ifndef M10V_ISP_NATIVE_LOOK_H
#define M10V_ISP_NATIVE_LOOK_H
#include "m10v_isp_frame_color.h"
#define M10V_ISP_NATIVE_LOOK_MAGIC 0x374c434eu
#define M10V_ISP_NATIVE_LOOK_VERSION 1u
enum { M10V_NATIVE_LOOK_EMPTY=0, M10V_NATIVE_LOOK_READY=1,
       M10V_NATIVE_LOOK_APPLIED=2, M10V_NATIVE_LOOK_REJECTED=3 };
/* Per-recipe storage, never global. generation must identify the queued shot.
 * exposure: RED 0=EI125, 1=EI64, 2=EI250; zero for all other films.
 * Profiles are new native creative looks, NOT old CPU LUT equivalence. */
typedef struct {
 uint32_t magic,version,generation,film,exposure,status,applied_frame;
 m10v_isp_frame_target target;
} m10v_isp_native_look;
int m10v_isp_native_look_prepare(m10v_isp_native_look *,uint32_t film,uint32_t exposure,uint32_t generation);
/* Invoke once after stock Still Make on the OWNED frame for carrier tones
 * 12,18..21 only. The caller checks recipe/ShootingInfo identity. No heap or
 * shared tuning changes. Failure leaves original frame unchanged. */
int m10v_isp_native_look_apply(m10v_isp_native_look *,const void *gamma,void *frame,uint32_t color_space);
/* Sole authorization to skip CPU color; textures/spatial effects still run.
 * Require the same queued generation, film and RED exposure, never global state. */
int m10v_isp_native_look_matches(const m10v_isp_native_look *,uint32_t film,uint32_t exposure,uint32_t generation);
#endif
