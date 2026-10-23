#include <stdint.h>
#include "film_style_filters_1_data.h"
#include "film_spectral_data.h"
/* Separate immutable bank keeps each ARM module below 64 KiB. */
const uint8_t *m10v_style_filters_1_table(uint32_t variant){return variant<3?&m10v_style_filters_luts_1[variant][0][0]:variant==3?&m10v_spectral_5213_lut[0][0]:0;}
