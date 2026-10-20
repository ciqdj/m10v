#ifndef M10V_GR2_UI_H
#define M10V_GR2_UI_H
#include <stdint.h>
/* Original loaded UTF-16 strings; caller never owns or frees these pointers. */
const uint16_t *gr2_original_text(uint32_t text_id,uint32_t language);
#endif
