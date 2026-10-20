#ifndef M10V_GR2_UI_H
#define M10V_GR2_UI_H
#include <stdint.h>
/* Original loaded UTF-16 strings; caller never owns or frees these pointers. */
const uint16_t *gr2_original_text(uint32_t text_id,uint32_t language);
/* Fresh detached storage only; this is not menu open/registration. */
int gr2_effect_view_init(void *storage,uint32_t capacity);
int gr2_film_card_rgba(uint8_t *,uint32_t capacity,uint32_t film,uint32_t slot,uint32_t selected);
/* UI thread only, initialized stock 640x480 logical context. Rectangle is
 * left/top/right/bottom, count excludes the required UTF-16 terminator. */
int gr2_text_draw(const uint16_t *,uint32_t,const int16_t rectangle[4],uint32_t color);
/* UI owner only; physical x/y packed in low/high16, one 120x196 card. */
int gr2_card_draw(uint32_t film,uint32_t slot,uint32_t selected,uint32_t position);
#endif
