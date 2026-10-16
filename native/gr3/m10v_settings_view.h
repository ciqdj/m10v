#ifndef M10V_SETTINGS_VIEW_H
#define M10V_SETTINGS_VIEW_H
#include "m10v_settings.h"
/* GR III 2.10 only. Unintegrated view; caller owns route and root lifetime. */
enum { M10V_VIEW_CAPACITY=40, M10V_VIEW_COUNT=37 };
typedef struct { uint32_t widgets[M10V_VIEW_CAPACITY]; uint32_t count; } m10v_settings_view;
enum {
 M10V_VIEW_FILMS=915, M10V_VIEW_STAMP, M10V_VIEW_FILM_HELP,
 M10V_VIEW_CATALOG_HELP, M10V_VIEW_STAMP_HELP, M10V_VIEW_VALUE_HELP,
 M10V_VIEW_EMPTY, M10V_VIEW_CHANGED, M10V_VIEW_FAILED,
 M10V_VIEW_MODE, M10V_VIEW_FORMAT, M10V_VIEW_CORNER, M10V_VIEW_COLOR,
 M10V_VIEW_OFF, M10V_VIEW_DATE, M10V_VIEW_DATETIME,
 M10V_VIEW_YMD, M10V_VIEW_DMY, M10V_VIEW_YMD_DASH, M10V_VIEW_SHORT_YEAR,
 M10V_VIEW_TOP_LEFT, M10V_VIEW_TOP_RIGHT, M10V_VIEW_BOTTOM_LEFT, M10V_VIEW_BOTTOM_RIGHT,
 M10V_VIEW_WHITE, M10V_VIEW_ORANGE, M10V_VIEW_RED, M10V_VIEW_YELLOW,
 M10V_VIEW_EDIT_MODE, M10V_VIEW_EDIT_FORMAT, M10V_VIEW_EDIT_CORNER, M10V_VIEW_EDIT_COLOR,
 M10V_VIEW_CHOOSE_FILM
};
/* Initialize the entire struct to zero before first create. */
int m10v_settings_view_create(m10v_settings_view *);
void m10v_settings_view_draw(m10v_settings_view *, const m10v_settings *, const m10v_settings_ops *);
/* Caller must unregister the shown root before destruction. */
void m10v_settings_view_destroy(m10v_settings_view *);
#endif
