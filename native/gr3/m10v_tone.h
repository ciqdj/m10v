#ifndef M10V_TONE_H
#define M10V_TONE_H
#include <stdint.h>
#ifndef M10V_APPENDED_SLOTS
#define M10V_APPENDED_SLOTS 0
#endif
#define M10V_TONE_CHOICES (M10V_APPENDED_SLOTS ? 17u : 12u)
#define M10V_LIBRARY_INDEX (M10V_APPENDED_SLOTS ? 19u : 12u)
static inline uint32_t m10v_slot_tone(uint32_t slot){
 static const uint8_t legacy[5]={12,18,19,20,21};
 return slot<5?(M10V_APPENDED_SLOTS?25u+slot:legacy[slot]):0;
}
static inline uint32_t m10v_tone_slot(uint32_t tone){
 if(M10V_APPENDED_SLOTS)return tone>=25&&tone<=29?tone-25:5;
 return tone==12?0:tone>=18&&tone<=21?tone-17:5;
}
static inline int m10v_tone_valid(uint32_t tone){
 return (tone>=11&&tone<=22)||(M10V_APPENDED_SLOTS&&tone>=25&&tone<=29);
}
#endif
