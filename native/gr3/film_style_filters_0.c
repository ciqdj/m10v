#include <stdint.h>
#include "film_style_filters_0_data.h"
/* Separate immutable bank keeps each ARM module below 64 KiB. */
const uint8_t *m10v_style_filters_0_table(uint32_t variant){return variant<4?&m10v_style_filters_luts_0[variant][0][0]:0;}
