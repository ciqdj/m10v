#ifndef M10V_LIBRARY_H
#define M10V_LIBRARY_H
#include <stdint.h>

#define M10V_FILM_COUNT 65u
#define M10V_SLOT_COUNT 5u
#define M10V_LIBRARY_OK 0
#define M10V_LIBRARY_INVALID -1
#define M10V_LIBRARY_STORE_FAILED -2

typedef struct { uint16_t film; uint8_t grain, soft, halo_gain, halo_spread, halo_threshold, halo_profile; } m10v_slot;
typedef struct {
    uint32_t magic;
    uint16_t version, size;
    uint32_t sequence;
    m10v_slot slots[M10V_SLOT_COUNT];
    uint8_t stamp, format, corner, color;
    uint32_t reserved, crc;
} m10v_library_state;
typedef struct {
    uint8_t *y, *chroma;
    uint32_t y_bytes, chroma_bytes, width, height, stride;
} m10v_library_image;
typedef struct { uint16_t year; uint8_t month, day, hour, minute; } m10v_library_date;
typedef int (*m10v_library_store)(void *, const m10v_library_state *);

void m10v_library_init(m10v_library_state *);
int m10v_library_valid(const m10v_library_state *);
const char *m10v_library_name(uint32_t film);
int m10v_library_select(m10v_library_state *, uint32_t slot, uint32_t film,
                        m10v_library_store, void *);
int m10v_library_texture(m10v_library_state *, uint32_t slot, uint32_t grain, uint32_t soft,
                         m10v_library_store, void *);
int m10v_library_halation(m10v_library_state *, uint32_t slot, uint32_t gain, uint32_t spread, uint32_t threshold, uint32_t profile, m10v_library_store, void *);
int m10v_library_detail(m10v_library_state *, uint32_t slot, uint32_t gain, uint32_t spread, uint32_t threshold, uint32_t grain, uint32_t soft, m10v_library_store, void *);
int m10v_library_tables(uint32_t film, int16_t *, int16_t *, uint16_t *, uint16_t *);
int m10v_library_stamp(m10v_library_state *, uint32_t enabled, uint32_t format,
                       uint32_t corner, uint32_t color, m10v_library_store, void *);
int m10v_library_render(m10v_library_image *, const m10v_library_state *, uint32_t slot,
                        const m10v_library_date *, uint32_t seed, uint8_t *scratch,
                        uint32_t scratch_bytes);
/* Nonnegative load provenance: 0=new journal, 1=defaults, 2=v2 migration,
 * 3=v1 migration. All are usable validated states; negative is failure. */
int m10v_camera_library_load(m10v_library_state *);
int m10v_camera_library_select(m10v_library_state *, uint32_t slot, uint32_t film);
int m10v_camera_library_texture(m10v_library_state *, uint32_t slot, uint32_t grain, uint32_t soft);
int m10v_camera_library_halation(m10v_library_state *, uint32_t slot, uint32_t gain, uint32_t spread, uint32_t threshold, uint32_t profile);
int m10v_camera_library_detail(m10v_library_state *, uint32_t slot, uint32_t gain, uint32_t spread, uint32_t threshold, uint32_t grain, uint32_t soft);
int m10v_camera_library_stamp(m10v_library_state *, uint32_t enabled, uint32_t format,
                             uint32_t corner, uint32_t color);
#endif
