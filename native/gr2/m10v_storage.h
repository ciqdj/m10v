#ifndef M10V_GR2_STORAGE_H
#define M10V_GR2_STORAGE_H
#include "../gr3/m10v_library.h"
int gr2_state_encode(const m10v_library_state *,uint8_t wire[104]);
int gr2_state_decode(const uint8_t wire[104],m10v_library_state *);
#endif
