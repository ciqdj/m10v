#ifndef M10V_GR2_CAPTURE_H
#define M10V_GR2_CAPTURE_H
#include "m10v_model.h"
#include "../../compat/gr2-v1/native/gr3/m10v_library.h"
/* Synchronous software adapter only. Camera lifecycle admission is separate. */
int gr2_render_planar(const m10v_gr2_image *,const m10v_library_state *,uint32_t,
                      const m10v_library_date *,uint32_t,uint8_t *,uint32_t);
/* Inline value-only payload; stock clone copies it without new references.
 * This bridge does not itself resize a pool or install a capture hook. */
typedef struct {
    uint32_t magic,version,slot,seed;
    m10v_library_state state;
    uint32_t processed,crc;
} m10v_gr2_frame;
/* Synchronous owner only, around the stock producer call. Result: 1 prepared,
 * 0 ordinary stock frame, -1 rejected without changing the color mode. */
int gr2_producer_ingress(uint8_t *,const m10v_library_state *,uint32_t);
int gr2_producer_leave(uint8_t *);
uint32_t gr2_producer_run(uint8_t *,uint32_t,const m10v_library_state *,uint32_t);
int gr2_frame_freeze(uint8_t *,const m10v_library_state *,uint32_t,uint32_t);
int gr2_frame_freeze_custom(uint8_t *,const m10v_library_state *,uint32_t,uint32_t,const uint8_t *);
int gr2_frame_read(const uint8_t *,m10v_gr2_frame *);
uint32_t gr2_image_owner_bytes(const uint8_t *);
/* The real camera hook must also establish event completion and cache aliases. */
int gr2_capture_admit(const uint8_t *,uint32_t,const uint8_t *,m10v_gr2_image *);

int gr2_capture_frozen(const uint8_t *,uint32_t,const uint8_t *);
int gr2_capture_process(const uint8_t *,uint32_t,const uint8_t *,const m10v_library_state *,uint32_t);
#endif
