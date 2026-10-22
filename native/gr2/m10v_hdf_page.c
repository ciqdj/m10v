#include "m10v_hdf_page.h"
#include "m10v_hdf_control.h"
#include "m10v_hdf_configuration.h"
#include "m10v_settings_page.h"
#include "m10v_ui.h"
#include "m10v_model.h"
#define PAGE_MAGIC 0x47324850u
typedef struct {gr2_overlay overlay;uint32_t magic,value,saved,error,closed;} page;
static page *active;
static const uint16_t text_0[]={0x48,0x44,0x46,0x20,0x6a21,0x62df,0};
static const uint16_t text_1[]={0x5de6,0x53f3,0x9009,0x62e9,0x20,0x4f,0x4b,0x4fdd,0x5b58,0x20,0x44,0x49,0x53,0x50,0x53d6,0x6d88,0};
static const uint16_t text_2[]={0x5173,0x95ed,0};
static const uint16_t text_3[]={0x5f31,0};
static const uint16_t text_4[]={0x4e2d,0};
static const uint16_t text_5[]={0x5f3a,0};
static const uint16_t text_6[]={0x8bfb,0x53d6,0x6216,0x4fdd,0x5b58,0x5931,0x8d25,0};
static const uint16_t text_7[]={0x5168,0x5c40,0x6570,0x5b57,0x67d4,0x7126,0x20,0xb7,0x20,0x72ec,0x7acb,0x4e8e,0x80f6,0x5377,0};

static const uint16_t *const labels[]={text_0,text_1,text_2,text_3,text_4,text_5,text_6,text_7};
const uint16_t *gr2_hdf_page_title(void){return text_0;}
int gr2_hdf_page_active(void){return active!=0;}
static int fill(uint32_t plane,int16_t x,int16_t y,int16_t right,int16_t bottom,uint32_t color){
 int16_t box[4]={x,y,right,bottom};return gr2_fill_rect(plane,box,color);
}
static int text(uint32_t index,int16_t x,int16_t y,int16_t right,int16_t bottom){
 const uint16_t *caption=labels[index];uint32_t count=0;while(caption[count])count++;
 int16_t box[4]={x,y,right,bottom};return gr2_text_draw_full(caption,count,box,0x20001);
}
int gr2_hdf_page_draw(void){
 page *p=active;if(!p||p->magic!=PAGE_MAGIC||p->closed||p->value>3u)return 0;
 int ok=fill(0,0,0,719,479,0x20000)&&fill(1,0,0,719,479,0x20004);
 ok=text(0,20,12,699,61)&&text(1,20,424,699,469)&&ok;
 for(uint32_t i=0;i<4u;i++){
  int16_t x=(int16_t)(36+170*i);
  if(p->value==i)ok=fill(1,x,182,x+149,257,0x20001)&&fill(1,x+3,185,x+146,254,0x20004)&&ok;
  ok=text(2+i,x+10,191,x+139,246)&&ok;
 }
 ok=text(p->error?6:7,20,320,699,375)&&ok;p->overlay.dirty=ok?0:1;return ok;
}
static int destroy(void *owner,uint32_t reason){
 (void)reason;page *p=owner;if(active==p)active=0;p->magic=0;
 fill(0,0,0,719,479,0x20000);fill(1,0,0,719,479,0x20000);gr2_release(p);return 1;
}
int gr2_hdf_page_close(void){return active?gr2_overlay_detach(&active->overlay):0;}
int gr2_hdf_page_key(uint32_t key){
 page *p=active;if(!p||p->magic!=PAGE_MAGIC||p->closed||key>M10V_KEY_NEXT)return 0;
 if(key==M10V_KEY_BACK)return gr2_hdf_page_close();
 if(key==M10V_KEY_OK){
  if(gr2_hdf_update(p->value))return gr2_hdf_page_close();
  uint32_t actual,sequence;
  if(gr2_hdf_configuration_read(&actual,&sequence))p->saved=p->value=actual;
  p->error=1;
 }else{
  if(key==M10V_KEY_LEFT||key==M10V_KEY_UP||key==M10V_KEY_PREVIOUS){if(p->value)p->value--;}
  else if(p->value<3u)p->value++;
  p->error=0;
 }
 p->overlay.dirty=1;return 1;
}
int gr2_hdf_page_raw_event(const uint32_t *message){
 if(!message||((uintptr_t)message&3u)||!active)return 0;
 uint32_t key;
 switch(message[0]){
  case 0x60001006u:case 0x60001017u:key=M10V_KEY_UP;break;
  case 0x60001007u:case 0x60001018u:key=M10V_KEY_DOWN;break;
  case 0x60001008u:case 0x60001014u:key=M10V_KEY_LEFT;break;
  case 0x60001009u:case 0x60001015u:key=M10V_KEY_RIGHT;break;
  case 0x6000100au:case 0x60001016u:key=M10V_KEY_OK;break;
  case 0x6000100eu:key=M10V_KEY_BACK;break;
  default:return 0;
 }
 return gr2_hdf_page_key(key);
}
static uint32_t event(void *owner,const uint32_t *message){
 page *p=owner;if(!message||p!=active||p->magic!=PAGE_MAGIC)return 0;
 uint32_t key;
 switch(message[0]){
  case 0x60000003u:return (uint32_t)gr2_hdf_page_draw();
  case 0x60000005u:p->closed=1;return 1;
  case 0x60002001u:case 0x60002506u:key=M10V_KEY_RIGHT;break;
  case 0x60002002u:case 0x60002505u:key=M10V_KEY_LEFT;break;
  case 0x60002003u:case 0x60002503u:key=M10V_KEY_UP;break;
  case 0x60002004u:case 0x60002504u:key=M10V_KEY_DOWN;break;
  case 0x60002005u:case 0x60002501u:key=M10V_KEY_OK;break;
  case 0x60002006u:case 0x60002502u:key=M10V_KEY_BACK;break;
  default:return 0;
 }
 return (uint32_t)gr2_hdf_page_key(key);
}
void *gr2_hdf_page_open(void){
 if(active||gr2_settings_active())return 0;
 page *p=gr2_allocate(sizeof(*p));if(!p)return 0;
 for(uint32_t i=0;i<sizeof(*p);i++)((uint8_t *)p)[i]=0;
 uint32_t strength,sequence;
 if(gr2_hdf_reload()&&gr2_hdf_configuration_read(&strength,&sequence))p->saved=p->value=strength;
 else p->error=1;
 p->magic=PAGE_MAGIC;p->overlay.event=event;p->overlay.destroy=destroy;
 if(!gr2_overlay_attach(&p->overlay)){gr2_release(p);return 0;}
 active=p;return p;
}
int gr2_hdf_page_peek(uint32_t out[4]){
 uintptr_t o=(uintptr_t)out,b=(uintptr_t)active;
 if(!active||!out||(o&3u)||o>UINTPTR_MAX-16u||(o<b+sizeof(*active)&&b<o+16u))return 0;
 out[0]=active->value;out[1]=active->saved;out[2]=active->error;out[3]=active->closed;return 1;
}
