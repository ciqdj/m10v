#ifndef M10V_GR2_HDF_CONTROL_H
#define M10V_GR2_HDF_CONTROL_H
#include <stdint.h>
/* Existing UI owner only; independent HDF journals and capture cache. A failed
 * write is reconciled with disk even if it may already have persisted. Never
 * call these from startup, capture workers or an interrupt. */
extern volatile uint32_t gr2_hdf_ui_boot_state;
int gr2_hdf_ui_bootstrap(const uint32_t *message);
int gr2_hdf_reload(void);
int gr2_hdf_update(uint32_t strength);
#endif
