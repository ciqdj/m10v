#ifndef M10V_ZOOM_H
#define M10V_ZOOM_H
#include <stdint.h>
/* IIIx nominal71 uses the stock 50/28 ratio (RTOS literal53d2ffe8),
 * not71/40: preserve original crop enum6 and native metadata/resolution.
 * Two persistent user-editable crop slots. Firmware adapters own selection,
 * image geometry and per-photo metadata; this module never touches pixels. */
#define M10V_ZOOM_BYTES 24u
#if M10V_CAMERA_GR3X
#define M10V_ZOOM_MIN_MM 40u
#define M10V_ZOOM_MAX_MM 71u
#define M10V_ZOOM_DEFAULT_SECOND_BITS 0x3fe49249u
#define M10V_ZOOM_DEFAULT_FIRST 50u
#define M10V_ZOOM_DEFAULT_SECOND 71u
#define M10V_ZOOM_LEGACY_MAX_MM 71u
#else
#define M10V_ZOOM_MIN_MM 28u
#define M10V_ZOOM_MAX_MM 50u
#define M10V_ZOOM_DEFAULT_SECOND_BITS 0x3fe49249u
#define M10V_ZOOM_DEFAULT_FIRST 35u
#define M10V_ZOOM_DEFAULT_SECOND 50u
#define M10V_ZOOM_LEGACY_MAX_MM 100u
#endif
#define M10V_ZOOM_STALE (-2)
typedef struct { uint32_t sequence; uint16_t mm[2]; } m10v_zoom_state;
typedef struct {
 void *context;
 int (*read)(void *,unsigned,void *,unsigned);
 int (*write)(void *,unsigned,const void *,unsigned);
} m10v_zoom_io;
typedef struct { uint32_t sequence,slot,value; } m10v_zoom_editor;
int m10v_zoom_load(m10v_zoom_state *,const m10v_zoom_io *);
void m10v_zoom_open(m10v_zoom_editor *,const m10v_zoom_state *,unsigned slot);
void m10v_zoom_adjust(m10v_zoom_editor *,int direction);
int m10v_zoom_save(m10v_zoom_state *,const m10v_zoom_editor *,const m10v_zoom_io *);
int m10v_zoom_replace(m10v_zoom_state *,uint32_t,uint32_t,const m10v_zoom_io *);
uint32_t m10v_zoom_bits(uint32_t mm);
uint32_t m10v_zoom_mm(uint32_t bits);
uint32_t m10v_zoom_title(void);
uint32_t m10v_zoom_caption(uint32_t bits);
#endif
