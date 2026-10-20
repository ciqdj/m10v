#ifndef M10V_GR2_EFFECT_NAMES_H
#define M10V_GR2_EFFECT_NAMES_H
/* UI owner only. Stable buffers outlive cached stock widget pointers.
 * Every original language/alias preimage is checked before any table write. */
int gr2_effect_names_refresh(void);
int gr2_effect_names_restore(void);
int gr2_effect_names_enabled(void);
#endif
