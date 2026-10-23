#ifndef M10V_ZOOM_MENU_H
#define M10V_ZOOM_MENU_H
#include "m10v_zoom.h"
#define M10V_SETTINGS_ZOOM 8u
typedef struct {
 m10v_zoom_state saved;
 m10v_zoom_editor editor;
 uint32_t focus,editing,closed,error,selected;
} m10v_zoom_menu;
typedef struct {
 int (*load)(m10v_zoom_state *);
 int (*save)(m10v_zoom_state *,const m10v_zoom_editor *);
 int (*select)(unsigned);
 unsigned (*current)(void);
} m10v_zoom_menu_ops;
void m10v_zoom_menu_open(m10v_zoom_menu *,const m10v_zoom_menu_ops *);
void m10v_zoom_menu_key(m10v_zoom_menu *,const m10v_zoom_menu_ops *,uint32_t);
#endif
