#ifndef M10V_GR2_SETTINGS_PAGE_H
#define M10V_GR2_SETTINGS_PAGE_H
#include "../gr3/m10v_settings.h"
/* Existing UI owner and initialized graphics/fonts only. NULL ops binds the
 * native journal/SD backend; external callback context must outlive the page. */
void *gr2_settings_open(const m10v_settings_ops *,uint32_t screen);
int gr2_settings_close(void);
/* Existing camera menu/UI owner only; private routes never enter stock FSM. */
int gr2_settings_menu_route(uint32_t route);
int gr2_menu_entries_enable(uint32_t enabled);
int gr2_settings_key(uint32_t key);
int gr2_settings_draw(void);
int gr2_settings_raw_event(const uint32_t *message);
int gr2_settings_peek(m10v_settings *);
#endif
