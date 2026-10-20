#ifndef M10V_GR2_SETTINGS_BACKEND_H
#define M10V_GR2_SETTINGS_BACKEND_H
#include "m10v_sd.h"
#include "../gr3/m10v_settings.h"
/* One caller-owned UI session; no open files survive a callback. */
typedef struct { gr2_pack_manifest manifest;uint32_t attempted; } gr2_settings_backend;
int gr2_settings_backend_bind(gr2_settings_backend *,m10v_settings_ops *);
void gr2_settings_backend_refresh(gr2_settings_backend *);
#endif
