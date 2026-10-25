#ifndef M10V_GR2_HDF_PAGE_H
#define M10V_GR2_HDF_PAGE_H
#include <stdint.h>
/* Existing UI owner, initialized original fonts/graphics and file services. */
void *gr2_hdf_page_open(void);
int gr2_hdf_page_active(void);
int gr2_hdf_page_close(void);
int gr2_hdf_page_key(uint32_t key);
int gr2_hdf_page_raw_event(const uint32_t *message);
int gr2_hdf_page_draw(void);
int gr2_hdf_page_peek(uint32_t out[4]);
const uint16_t *gr2_hdf_page_title(void);
#endif
