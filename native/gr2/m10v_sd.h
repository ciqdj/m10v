#ifndef M10V_GR2_SD_H
#define M10V_GR2_SD_H
#include <stdint.h>
#include "m10v_storage.h"
typedef struct {
    int (*size)(const char *,uint32_t *);
    int32_t (*read_at)(const char *,uint32_t,uint8_t *,uint32_t);
} gr2_pack_io;
/* Caller provides 4096 bytes for listing, 16384 for full record validation.
 * Full fetch requires an expected ID; scratch is never executable camera data. */
uint32_t gr2_pack_fetch(const gr2_pack_io *,uint32_t index,uint32_t expected,uint8_t *scratch,uint32_t full);
typedef struct { uint32_t magic,size,count;uint8_t header[4096]; } gr2_pack_manifest;
enum { GR2_PACK_IO_ERROR=-1,GR2_PACK_CHANGED=-2,GR2_PACK_INVALID=-3 };
int gr2_pack_manifest_load(const gr2_pack_io *,gr2_pack_manifest *,uint8_t *header_scratch);
/* Manifest remains immutable for one owned catalog session. Work is 16 KiB. */
int32_t gr2_pack_fetch_frozen(const gr2_pack_io *,const gr2_pack_manifest *,uint32_t index,uint32_t expected,uint8_t *work);
/* Manifest belongs to the UI session; each call releases all temporary storage. */
int gr2_sd_catalog_open(gr2_pack_manifest *);
uint32_t gr2_sd_frozen_record(const gr2_pack_manifest *,uint32_t,uint32_t,uint8_t *,uint32_t);
/* UI-only transaction; work size is 4096+2*RECORD_BYTES+1. A validated
 * frozen catalog and fresh journal precede the inactive snapshot write. */
int gr2_pack_install(const gr2_pack_io *,const gr2_storage_io *,const gr2_pack_manifest *,uint32_t,uint32_t,uint32_t,uint8_t *);
int gr2_sd_install(const gr2_pack_manifest *,uint32_t,uint32_t,uint32_t);
/* Preload on the UI/settings owner; capture only consumes inline records. */
int gr2_sd_custom_record(const m10v_library_state *,uint32_t,uint8_t *,uint32_t);
uint32_t gr2_sd_item(uint32_t index);
uint32_t gr2_sd_record(uint32_t index,uint32_t expected,uint8_t *out,uint32_t capacity);
int gr2_sd_catalog_name(uint32_t index,uint32_t expected,char *out,uint32_t capacity);
#endif
