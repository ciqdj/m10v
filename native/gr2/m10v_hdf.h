#ifndef M10V_GR2_HDF_H
#define M10V_GR2_HDF_H
#include <stdint.h>
#define GR2_HDF_FRAME_OFFSET 0x12b8cu
#define GR2_IMAGE_BODY_BYTES (GR2_HDF_FRAME_OFFSET+16u)
typedef struct {uint32_t magic,control,sequence,crc;} gr2_hdf_frame;
int gr2_hdf_frame_freeze(uint8_t *context,uint32_t strength,uint32_t sequence);
int gr2_hdf_frame_read(const uint8_t *context,gr2_hdf_frame *out);
/* Private inline phase: scheduling freezes one family before clone policy;
 * preparation consumes that phase once before reserving JPEG buffers. */
int gr2_hdf_frame_policy_mark(uint8_t *context,uint8_t *peer);
int gr2_hdf_frame_policy_consume(uint8_t *context);
#define GR2_HDF_BANDS 11u
#define GR2_HDF_CURVE_OFFSET 0xe040u
#define GR2_HDF_CURVE_BYTES 8192u
#define GR2_HDF_WORKSPACE_BYTES (GR2_HDF_CURVE_OFFSET+GR2_HDF_BANDS*GR2_HDF_CURVE_BYTES)
/* Caller owns the original tag20 scratch for the complete synchronous graph.
 * Requires its fourth original expanded curve to be the exact identity curve.
 * No frame admission, persistence, allocation, DMA or capture hook is installed.
 * Off returns0 without touching memory; invalid inputs return-1 before writes. */
int gr2_hdf_prepare_bands(uint16_t *workspace,uint32_t bytes,uint32_t strength);
/* Caller retains the original tag20 handle throughout the check/use. */
uint32_t gr2_hdf_workspace_bytes(const void *data);
#endif
