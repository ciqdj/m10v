#ifndef M10V_GR2_CAPTURE_H
#define M10V_GR2_CAPTURE_H
#include "m10v_model.h"
#include "../gr3/m10v_library.h"
/* Synchronous software adapter only. Camera lifecycle admission is separate. */
int gr2_render_planar(const m10v_gr2_image *,const m10v_library_state *,uint32_t,
                      const m10v_library_date *,uint32_t,uint8_t *,uint32_t);
#endif
