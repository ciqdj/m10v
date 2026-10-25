#ifndef M10V_GR2_BOOT_H
#define M10V_GR2_BOOT_H
#include <stdint.h>
extern volatile uint32_t gr2_activation_ready;
extern volatile uint32_t gr2_startup_complete;
/* Source hooks must already be loaded; this never hot-patches instructions. */
int gr2_native_activate(void);
int gr2_native_ready(void);
uint32_t gr2_cpu_state(void);
int gr2_ui_storage_ready(void);
int gr2_ui_bootstrap(const uint32_t *message);
extern volatile uint32_t gr2_ui_boot_state;
#endif
