#ifndef M10V_GR2_HDF_CONFIGURATION_H
#define M10V_GR2_HDF_CONFIGURATION_H
#include <stdint.h>
/* UI-only publication creates the original nonrecursive mutex. Nonzero HDF
 * requires an already prepared original bank0. These functions never switch
 * pools or touch the SD card. Capture reads/freezes use timeout0; an existing
 * frame snapshot survives later publication/clear without reacquiring a lock. */
int gr2_hdf_configuration_publish(uint32_t strength,uint32_t sequence);
int gr2_hdf_configuration_read(uint32_t *strength,uint32_t *sequence);
int gr2_hdf_configuration_freeze(uint8_t *context);
int gr2_hdf_configuration_clear(void);
#endif
