#ifndef M10V_GR2_BOOT_H
#define M10V_GR2_BOOT_H
#include <stdint.h>
extern volatile uint32_t gr2_activation_ready;
/* Source hooks must already be loaded; this never hot-patches instructions. */
int gr2_native_activate(void);
int gr2_native_ready(void);
uint32_t gr2_cpu_state(void);
#endif
