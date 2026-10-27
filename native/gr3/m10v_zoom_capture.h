#ifndef M10V_ZOOM_CAPTURE_H
#define M10V_ZOOM_CAPTURE_H
#include <stdint.h>
#include "m10v_zoom.h"
/* Stateless helpers only: firmware integration must supply the current image's
 * immutable focal value and native/aspect baseline dimensions. Zero means
 * unhandled: invoke the unchanged native path. No camera validation implied. */
typedef struct {
    uint32_t x, y, width, height;
    uint32_t output_width, output_height;
} m10v_zoom_capture_rect;
int m10v_zoom_capture_marker_encode(uint32_t mm, uint8_t marker[3]);
uint32_t m10v_zoom_capture_marker_decode(const uint8_t marker[3]);
/* Proposed aligned geometry policy. source_{w,h} are uncropped aspect-specific
 * dimensions; quality_{w,h} are the requested native/aspect JPEG size. Keep
 * these two geometries separate: quality does not change the field of view.
 * Alignment and ISP acceptance still require firmware/device validation. */
int m10v_zoom_capture_geometry(uint32_t mm, uint32_t source_w,
    uint32_t source_h, uint32_t quality_w, uint32_t quality_h,
    m10v_zoom_capture_rect *out);
uint32_t m10v_zoom_capture_quality_count(uint32_t mm);
int m10v_zoom_capture_quality_value(uint32_t mm, uint32_t index);
/* Display-only dispatch: canonical28/35/50 =>delegate sentinel; exact custom
 * =>numeric resource; invalid/rounded foreign floats =>blank0, never guessed. */
#define M10V_ZOOM_CAPTURE_DISPLAY_DELEGATE UINT32_MAX
uint32_t m10v_zoom_capture_caption(uint32_t bits);
uint32_t m10v_zoom_capture_custom(uint32_t bits);
#endif
