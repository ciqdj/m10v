#ifndef M10V_GR2_HDF_STORAGE_H
#define M10V_GR2_HDF_STORAGE_H
#include "m10v_storage.h"
/* UI owner only. Independent24-byte little-endian HDF1 records, never the
 * film-state journal. Store requires an existing valid bank; unknown files
 * are not permission to initialize. Outputs remain unchanged on failure. */
int gr2_hdf_journal_load(const gr2_storage_io *,uint32_t *strength,uint32_t *sequence);
int gr2_hdf_journal_store(const gr2_storage_io *,uint32_t strength);
/* UI services must be live; first creation requires exact SDK absence. */
int gr2_hdf_journals_absent(void);
int gr2_hdf_initialize_state(void);
int gr2_hdf_load_state(uint32_t *strength,uint32_t *sequence);
int gr2_hdf_save_state(uint32_t strength);
#endif
