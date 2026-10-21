#ifndef M10V_GR2_HDF_H
#define M10V_GR2_HDF_H
#include <stdint.h>
#define GR2_HDF_BANDS 11u
#define GR2_HDF_CURVE_OFFSET 0xe040u
#define GR2_HDF_CURVE_BYTES 8192u
#define GR2_HDF_WORKSPACE_BYTES (GR2_HDF_CURVE_OFFSET+GR2_HDF_BANDS*GR2_HDF_CURVE_BYTES)
/* Caller owns the original tag20 scratch for the complete synchronous graph.
 * Requires its fourth original expanded curve to be the exact identity curve.
 * No frame admission, persistence, allocation, DMA or capture hook is installed.
 * Off returns0 without touching memory; invalid inputs return-1 before writes. */
int gr2_hdf_prepare_bands(uint16_t *workspace,uint32_t bytes,uint32_t strength);
#endif
