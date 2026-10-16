#ifndef M10V_FILM_5207_H
#define M10V_FILM_5207_H
#include "m10v_library.h"
void m10v_5207_rgb(const uint8_t rgb[3], uint8_t out[3]);
void m10v_5207_render(m10v_library_image *,const m10v_film_effects *,uint32_t grain,uint32_t seed);
/* Shared grain/leak renderer: color=0 leaves the film color transform unchanged. */
void m10v_5207_texture(m10v_library_image *,const m10v_film_effects *,uint32_t,uint32_t,uint32_t color);
void m10v_5207_texture_q8(m10v_library_image *,const m10v_film_effects *,uint32_t grain_q8,uint32_t,uint32_t color);
#endif
