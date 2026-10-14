#ifndef M10V_HALATION_CONTROLS_H
#define M10V_HALATION_CONTROLS_H
#include <stdint.h>
/* Dedicated settings backend. Never reinterpret the stock color sliders. */
static inline __attribute__((always_inline)) uint32_t m10v_control_record(void){
    return ((uint32_t (*)(uint32_t,uint32_t,uint32_t))0x540be000u)(5,0,0);
}
static inline __attribute__((always_inline)) uint32_t m10v_camera_controls(const uint8_t *si,uint32_t base){
    (void)si;
    return ((uint32_t (*)(uint32_t,uint32_t,uint32_t))0x540be000u)(0,base,0);
}
#endif
