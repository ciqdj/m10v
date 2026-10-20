#ifndef M10V_GR2_CONFIGURATION_H
#define M10V_GR2_CONFIGURATION_H
#include "m10v_capture.h"
/* UI task only: publish an owned immutable copy of all selected custom
 * records. The caller's state/record buffers may be released on return.
 * Capture/read use the original nonrecursive RTOS mutex with timeout zero;
 * contention returns immediately. No function in this module opens files. */
int gr2_configuration_publish(const m10v_library_state *,const uint8_t *const records[5]);
int gr2_configuration_read(m10v_library_state *);
/* One atomic UI value snapshot, five persistent-label inputs, 96 UTF16 units each. */
int gr2_configuration_names(uint16_t out[5][96]);
int gr2_configuration_freeze(uint8_t *context,uint32_t seed);
int gr2_configuration_clear(void);
/* UI owner only: load journal and every selected LUT before publishing. */
int gr2_configuration_reload(void);
uint32_t gr2_producer_active(uint8_t *,uint32_t);
#endif
