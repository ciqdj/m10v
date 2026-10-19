#ifndef M10V_FILM_CARD_H
#define M10V_FILM_CARD_H
#include <stdint.h>
enum { M10V_CARD_WIDTH=120, M10V_CARD_HEIGHT=196, M10V_CARD_PIXELS=120*196,
       M10V_CARD_FIRST=743, M10V_CARD_COUNT=5 };
/* Caller supplies exactly M10V_CARD_PIXELS writable ARGB words. */
int m10v_film_card_render(uint32_t *,uint32_t film,uint32_t slot,uint32_t selected);
#endif
