#ifndef M10V_GR2_HDF_LAYOUT_H
#define M10V_GR2_HDF_LAYOUT_H
#include <stdint.h>
uint32_t gr2_hdf_buffer_layout(uint32_t mode,uint32_t drive,uint32_t auxiliary,uint32_t variant);
/* UI owner only. Stages a layout decision; never publishes a pixel setting. */
int gr2_hdf_prepare_pool(uint32_t strength);
#endif
