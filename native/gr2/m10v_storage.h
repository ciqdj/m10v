#ifndef M10V_GR2_STORAGE_H
#define M10V_GR2_STORAGE_H
#include "../gr3/m10v_library.h"
int gr2_state_encode(const m10v_library_state *,uint8_t wire[104]);
int gr2_state_decode(const uint8_t wire[104],m10v_library_state *);
typedef struct {
    int32_t (*read)(const char *,uint8_t *,uint32_t);
    int32_t (*write)(const char *,const uint8_t *,uint32_t);
} gr2_storage_io;
int gr2_journal_load(const gr2_storage_io *,m10v_library_state *);
int gr2_journal_store(const gr2_storage_io *,const m10v_library_state *);
int32_t gr2_file_read(const char *,uint8_t *,uint32_t);
int gr2_file_size(const char *,uint32_t *);
int32_t gr2_file_read_at(const char *,uint32_t offset,uint8_t *,uint32_t capacity);
int32_t gr2_file_write(const char *,const uint8_t *,uint32_t);
int gr2_load_state(m10v_library_state *);
int gr2_save_state(const m10v_library_state *);
#endif
