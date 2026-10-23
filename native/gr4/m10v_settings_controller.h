#ifndef M10V_SETTINGS_CONTROLLER_H
#define M10V_SETTINGS_CONTROLLER_H
#include "m10v_settings_view.h"
/* Two instances are embedded after the original TopMenu object, never placed
 * in undocumented RAM or freed independently from their owner. */
typedef struct {
 uint8_t base[0x158];
 m10v_settings_view view;
 m10v_settings state;
 uint32_t page;
} m10v_settings_controller;
#define M10V_SETTINGS_OWNER_BYTES 0x13ecu
#define M10V_SETTINGS_CONTROLLER_BYTES 0x320u
_Static_assert(sizeof(m10v_settings_controller)<=M10V_SETTINGS_CONTROLLER_BYTES,"controller tail capacity");
#define M10V_SETTINGS_FILMS_ROUTE 0x0200f100u
#define M10V_SETTINGS_STAMP_ROUTE 0x0200f101u
uint32_t m10v_settings_controller_owner_size(void);
uint32_t m10v_settings_controller_top_ctor(uint32_t owner);
uint32_t m10v_settings_controller_top_dtor(uint32_t owner);
uint32_t m10v_settings_controller_factory(uint32_t factory,uint32_t route);
uint32_t m10v_settings_controller_ready(m10v_settings_controller *,uint32_t route);
void m10v_settings_controller_enter(m10v_settings_controller *,uint32_t route,uint32_t flags);
uint32_t m10v_settings_controller_key(m10v_settings_controller *,uint32_t event);
#endif
