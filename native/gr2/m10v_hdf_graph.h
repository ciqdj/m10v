#ifndef M10V_GR2_HDF_GRAPH_H
#define M10V_GR2_HDF_GRAPH_H
#include <stdint.h>
/* Synchronous original graph owner retains IMG and tag20 BUFF references.
 * These helpers do not allocate, submit pixels or change context strength. */
int gr2_hdf_graph_prepare(const uint32_t *request,uint32_t hdr);
uint32_t gr2_hdf_graph_curve(uint32_t original,const uint32_t *level);
#endif
