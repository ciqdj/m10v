#ifndef M10V_GR2_MODEL_H
#define M10V_GR2_MODEL_H
#include <stdint.h>
/* GR II uses separate U/V planes. This is not the GR III CbCr descriptor. */
typedef struct {
    uint8_t *y,*u,*v;
    uint32_t y_bytes,u_bytes,v_bytes,width,height,y_stride,chroma_stride,format;
} m10v_gr2_image;
extern volatile uint32_t gr2_boot_count;
uint32_t gr2_post_load(void);
int gr2_date_valid(const uint16_t fields[6]);
int gr2_capture_decode(const uint8_t descriptor[48],m10v_gr2_image *output);
int gr2_chroma_shuffle(uint8_t *,uint32_t samples,int inverse);
void *gr2_allocate(uint32_t);
int32_t gr2_release(void *);
int gr2_read_clock(uint16_t output[6]);
int gr2_cache_before(void);
int gr2_cache_after(void);
#endif
