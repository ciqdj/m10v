/* GR III target adapter: visible order is the twelve factory looks, Custom1,
 * Custom2, then up to ten enabled films. Model APIs keep their separate dynamic-tone
 * domain; Custom1/2 are bank selectors, never tone IDs written to a frame. */
#include "m10v_tone.h"
#include "m10v_library.h"
#ifndef M10V_NATIVE_BASE
#define M10V_NATIVE_BASE 0x540b6000u
#endif
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef uint32_t (*fn4)(uint32_t,uint32_t,uint32_t,uint32_t);
extern uint32_t m10v_menu_name(uint32_t,uint32_t);
extern uint32_t m10v_menu_icon(uint32_t,uint32_t);
extern uint32_t m10v_menu_value_name(uint32_t,uint32_t);
extern uint32_t m10v_menu_value_icon(uint32_t,uint32_t);
static uint8_t *model(void){return (uint8_t *)(uintptr_t)((fn1)0x5320ba9cu)(((fn1)0x5320ad88u)(0));}
static int shooting(const uint8_t *m){return (uintptr_t)m==0x55068200u&&m[0x1b]==0;}
static uint32_t row_tone(uint32_t row){return row<12?0:row<14?23+row-12:row<m10v_camera_library_menu_index()?25+row-14:128;}
uint32_t m10v_tone_menu_index(uint32_t address,uint32_t row){
 if(shooting((const uint8_t *)(uintptr_t)address)&&row>=12&&row<m10v_camera_library_menu_index())return row_tone(row);
 return ((fn2)0x532c2c80u)(address,row);
}
uint32_t m10v_tone_menu_menu_name(uint32_t translator,uint32_t value){
 uint8_t *m=model();
 return shooting(m)&&!m[0x1d]?m10v_menu_name(translator,row_tone(m10v_camera_library_shooting_count()+(value==23?1:2))):m10v_menu_value_name(translator,value);
}
uint32_t m10v_tone_menu_menu_icon(uint32_t translator,uint32_t value){
 uint8_t *m=model();
 return shooting(m)&&!m[0x1d]?m10v_menu_icon(translator,row_tone(m10v_camera_library_shooting_count()+(value==23?1:2))):m10v_menu_value_icon(translator,value);
}
uint32_t m10v_tone_menu_adj_name(uint32_t translator,uint32_t value){
 return shooting(model())?m10v_menu_name(translator,row_tone(m10v_camera_library_shooting_count()+(value==23?0:1))):m10v_menu_value_name(translator,value);
}
uint32_t m10v_tone_menu_adj_icon(uint32_t translator,uint32_t value){
 return shooting(model())?m10v_menu_icon(translator,row_tone(m10v_camera_library_shooting_count()+(value==23?0:1))):m10v_menu_value_icon(translator,value);
}
static uint32_t matches(uint32_t address,uint32_t tone,uint32_t row,uint32_t bank){
 if(bank)return (bank==1&&row==12)||(bank==2&&row==13);
 if(row==12||row==13||row>=m10v_camera_library_menu_index())return 0;
 return row<12?((fn2)0x532c2c80u)(address,row)==tone:row_tone(row)==tone;
}
uint32_t m10v_tone_menu_menu_matches(uint32_t controller,uint32_t tone,uint32_t row,uint32_t bank){
 uint8_t *m=model();
 if(shooting(m)&&!m[0x1d])return matches((uint32_t)(uintptr_t)m,tone,row,bank);
 return ((fn4)(M10V_NATIVE_BASE+0xc0u))(controller,tone,row,bank);
}
uint32_t m10v_tone_menu_adj_matches(uint32_t controller,uint32_t row){
 uint8_t *m=model();
 if(!shooting(m))return ((fn2)(M10V_NATIVE_BASE+0xd0u))(controller,row);
 uint32_t address=(uint32_t)(uintptr_t)m;
 return matches(address,((fn1)0x532bd6b4u)(address),row,((fn1)0x532bd6d4u)(address));
}
uint32_t m10v_tone_menu_adj_select(uint32_t controller,uint32_t row){
 if(shooting(model())){
  if(row==12||row==13)row=m10v_camera_library_shooting_count()+row-12;
  else if(row>=14&&row<m10v_camera_library_menu_index())row-=2;
 }
 return ((fn2)(M10V_NATIVE_BASE+0xe0u))(controller,row);
}
