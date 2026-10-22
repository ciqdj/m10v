#include <stdint.h>

/* Extend the frozen GRLife DNG descriptor ABI without changing older ratios.
 * The descriptor stores a pointer to capture properties at +0x84 and a pointer
 * to sensor/crop geometry at +0x7c. All addresses are camera virtual addresses.
 */
static uint32_t read32(uint32_t address) {
    const uint8_t *p = (const uint8_t *)(uintptr_t)address;
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void write32(uint32_t address, uint32_t value) {
    uint8_t *p = (uint8_t *)(uintptr_t)address;
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

int m10v_aspect_dng_tags(uint32_t image, uint32_t out) {
    static const uint16_t widths[] = {6000, 4800, 3360, 1920};
    static const uint16_t heights[] = {4000, 3200, 2240, 1280};
    uint32_t properties, geometry, sensor_w, sensor_h, start_x, start_y;
    uint32_t image_x, image_y, width, height, x, y;
    uint8_t *result;
    unsigned i;

    if (!image || !out) return -1;
    properties = read32(image + 0x84);
    if (!properties || *(const uint8_t *)(uintptr_t)(properties + 0x719fe) != 5)
        return ((int (*)(uint32_t, uint32_t))(uintptr_t)0x540b7308)(image, out);
    geometry = read32(image + 0x7c);
    if (!geometry) return -1;
    sensor_w = read32(geometry + 0x10);
    sensor_h = read32(geometry + 0x14);
    width = read32(geometry + 0x20);
    height = read32(geometry + 0x24);
    if (!sensor_w || !sensor_h || !width || !height) return -1;
    start_x = read32(geometry + 8);
    start_y = read32(geometry + 12);
    image_x = read32(geometry + 0x18);
    image_y = read32(geometry + 0x1c);
    if (image_x < start_x || image_y < start_y) return -1;
    x = image_x - start_x;
    y = image_y - start_y;
    if (x > sensor_w || y > sensor_h ||
        width > sensor_w - x || height > sensor_h - y) return -1;

    /* Same 20-byte result as gr_dng_default_crop_tags: x,y,w,h,raw,size,
     * recognized,reserved. An unknown geometry remains a safe uncropped result.
     */
    write32(out, x);
    write32(out + 4, y);
    write32(out + 8, width);
    write32(out + 12, height);
    result = (uint8_t *)(uintptr_t)out;
    result[16] = 5;
    result[17] = 0xff;
    result[18] = 0;
    result[19] = 0;
    for (i = 0; i < 4; ++i) {
        uint32_t crop_w = (((uint32_t)heights[i] * 7 + 48) / 96) * 16;
        if (height != heights[i] || (width != widths[i] && width != crop_w))
            continue;
        if (width == widths[i]) x += (width - crop_w) / 2;
        write32(out, x);
        write32(out + 8, crop_w);
        result[17] = (uint8_t)i;
        result[18] = 1;
        return 1;
    }
    return 0;
}
