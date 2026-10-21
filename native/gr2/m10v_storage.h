#ifndef M10V_GR2_STORAGE_H
#define M10V_GR2_STORAGE_H
#include "../gr3/m10v_library.h"
typedef struct {
    int32_t (*read)(const char *,uint8_t *,uint32_t);
    int32_t (*write)(const char *,const uint8_t *,uint32_t);
} gr2_storage_io;
/* UI owner only; work contains RECORD_BYTES+1 bytes. Store returns the
 * inactive zero-based bank without changing the supplied state/journal. */
int gr2_custom_snapshot_store(const gr2_storage_io *,const m10v_library_state *,uint32_t,const uint8_t *,uint8_t *,uint32_t *);
int gr2_custom_snapshot_read(const gr2_storage_io *,const m10v_library_state *,uint32_t,uint8_t *,uint8_t *);
int gr2_state_encode(const m10v_library_state *,uint8_t wire[104]);
int gr2_state_decode(const uint8_t wire[104],m10v_library_state *);

int gr2_journal_load(const gr2_storage_io *,m10v_library_state *);
int gr2_journal_store(const gr2_storage_io *,const m10v_library_state *);
int32_t gr2_file_read(const char *,uint8_t *,uint32_t);
int gr2_file_size(const char *,uint32_t *);
int32_t gr2_file_read_at(const char *,uint32_t offset,uint8_t *,uint32_t capacity);
int32_t gr2_file_write(const char *,const uint8_t *,uint32_t);
/* 1 proven absent, 0 at least one exists, -1 search/allocation error. UI only. */
int gr2_journals_absent(void);
/* UI owner only: existing valid journal or proven-empty first initialization. */
int gr2_initialize_state(void);
int gr2_load_state(m10v_library_state *);
int gr2_save_state(const m10v_library_state *);
#endif
