#ifndef M10V_GR2_HDF_POSTPROCESS_H
#define M10V_GR2_HDF_POSTPROCESS_H
#include <stdint.h>
/* Original JPEG phase owns the IMG and primary BUFF for this synchronous call. */
uint32_t gr2_hdf_postprocess(uint8_t *context);
#endif
