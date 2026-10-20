#ifndef M10V_GR2_SD_H
#define M10V_GR2_SD_H
#include <stdint.h>
typedef struct {
    int (*size)(const char *,uint32_t *);
    int32_t (*read_at)(const char *,uint32_t,uint8_t *,uint32_t);
} gr2_pack_io;
/* Caller provides 4096 bytes for listing, 16384 for full record validation.
 * Full fetch requires an expected ID; scratch is never executable camera data. */
uint32_t gr2_pack_fetch(const gr2_pack_io *,uint32_t index,uint32_t expected,uint8_t *scratch,uint32_t full);
uint32_t gr2_sd_item(uint32_t index);
uint32_t gr2_sd_record(uint32_t index,uint32_t expected,uint8_t *out,uint32_t capacity);
int gr2_sd_catalog_name(uint32_t index,uint32_t expected,char *out,uint32_t capacity);
#endif
