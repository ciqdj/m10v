#include "m10v_zoom_capture.h"
static int custom(uint32_t mm) {
    return mm >= 28 && mm <= 100 && mm != 28 && mm != 35 && mm != 50;
}
int m10v_zoom_capture_marker_encode(uint32_t mm, uint8_t marker[3]) {
    if (!marker || !custom(mm)) return 0;
    marker[0] = 0;
    marker[1] = (uint8_t)(0x80 | (mm - 28));
    marker[2] = 1;
    return 1;
}
uint32_t m10v_zoom_capture_marker_decode(const uint8_t marker[3]) {
    uint32_t mm;
    if (!marker || marker[0] != 0 || marker[2] != 1 || !(marker[1] & 0x80))
        return 0;
    mm = (marker[1] & 0x7f) + 28;
    return custom(mm) ? mm : 0;
}
int m10v_zoom_capture_geometry(uint32_t mm, uint32_t source_w,
    uint32_t source_h, uint32_t quality_w, uint32_t quality_h,
    m10v_zoom_capture_rect *out) {
    uint32_t w, h;
    if (!out || !custom(mm) || !source_w || !source_h ||
        source_w > 6000 || source_h > 4000 || !quality_w || !quality_h ||
        quality_w > source_w || quality_h > source_h) return 0;
    w = ((source_w * 28) / mm) & ~15u;
    h = ((source_h * 28) / mm) & ~15u;
    if (!w || !h) return 0;
    out->x = (6000 - w) / 2;
    out->y = (4000 - h) / 2;
    out->width = w;
    out->height = h;
    out->output_width = quality_w < w ? quality_w : w;
    out->output_height = quality_h < h ? quality_h : h;
    return 1;
}
uint32_t m10v_zoom_capture_quality_count(uint32_t mm) {
    if (!custom(mm)) return 0;
    return mm < 35 ? 4 : mm < 50 ? 3 : 2;
}
int m10v_zoom_capture_quality_value(uint32_t mm, uint32_t index) {
    uint32_t count = m10v_zoom_capture_quality_count(mm);
    if (!count || index >= count) return -1;
    return (int)(4 - count + index);
}
