/* GR IV 1.11 center slider. Native callback owns orientation/level decisions.
 * Borrow exactly two FrameViews; f6/f7 are padding after native member f5. */
#include <stdint.h>
typedef uint32_t(*fn1)(uint32_t);typedef void(*fn2)(uint32_t,uint32_t);typedef void(*fn3)(uint32_t,uint32_t,uint32_t);
extern uint32_t m10v_level_frame_vtable(void);
static uint32_t w(uint32_t p,uint32_t o){return *(uint32_t*)(uintptr_t)(p+o);}
static uint8_t b(uint32_t p,uint32_t o){return *(uint8_t*)(uintptr_t)(p+o);}
static void sw(uint32_t p,uint32_t o,uint32_t v){*(uint32_t*)(uintptr_t)(p+o)=v;}
/* IEEE-754 degrees to signed quarter degrees, without FP/runtime helpers. */
int32_t m10v_level_quarter(uint32_t bits){
 uint32_t e=(bits>>23)&255,m=(bits&0x7fffff)|0x800000,v;int32_t shift=(int32_t)e-148;
 if(!e||e==255)return 0;
 if(shift>=8)return bits>>31?-1440:1440;
 v=shift>=0?m<<(uint32_t)shift:shift<=-24?0:m>>(uint32_t)-shift;
 if(v>1440)v=1440;return bits>>31?-(int32_t)v:(int32_t)v;
}
static int32_t angle(int32_t v){if(v>720)v-=1440;if(v<=-720)v+=1440;return v<=-96?-96:v>=96?96:v;}
static void invalid(uint32_t v){((fn1)0x535899fc)(v);}
static void show(uint32_t v,uint32_t yes){((fn2)0x53589ab4)(v,yes);}
static void rail(uint32_t v,const int32_t *rect,int32_t position,uint32_t aligned,uint32_t visible){
 uint32_t table=m10v_level_frame_vtable(),old=w(v,0);uint8_t color=aligned?27:2;
 sw(v,0,table);((fn2)0x53587c3c)(v,(uint32_t)(uintptr_t)rect);
 if(old!=table||(int8_t)b(v,0xf6)!=position||b(v,0xf7)!=color){
  *(uint8_t*)(uintptr_t)(v+0xf6)=(uint8_t)(int8_t)position;*(uint8_t*)(uintptr_t)(v+0xf7)=color;invalid(v);
 }show(v,visible);
}
void m10v_level_callback(uint32_t owner,uint32_t index,uint32_t visible){
 ((fn3)0x5318d8f0)(owner,index,visible);
 if(!owner||index>=94)return;
 uint32_t view=w(owner,0x15c+4*index),source=w(owner,0x4ec),frames[2]={w(owner,0x2cc),w(owner,0x2d0)},table=m10v_level_frame_vtable();
 if(!view||!source||!frames[0]||!frames[1])return;
 for(uint32_t i=0;i<2;i++)if(w(frames[i],0)!=0x53e98890&&w(frames[i],0)!=table)return;
 if(!b(view,0x9e)||b(view,0x11f)!=2||(b(owner,0x2d4)&0xfe)==2){
  for(uint32_t i=0;i<2;i++)if(w(frames[i],0)==table){sw(frames[i],0,0x53e98890);invalid(frames[i]);}return;
 }
 static const int32_t horizontal[4]={218,388,284,44},vertical[4]={654,98,44,284};
 int32_t roll=m10v_level_quarter(w(view,0x108)),pitch=angle(m10v_level_quarter(w(view,0x110))),rotation=(int32_t)w(view,0x120),first,second;
 uint32_t fc,sc,fv,sv;
 if(rotation==90||rotation==-90){
  if(rotation==90){second=-angle(roll+360);first=pitch;}else{second=angle(roll-360);first=-pitch;}
  fc=b(view,0x119);sc=b(view,0x118);fv=b(view,0x11d);sv=1;
 }else{first=angle(roll+(rotation?720:0));second=pitch;if(rotation){first=-first;second=-second;}fc=b(view,0x118);sc=b(view,0x119);fv=1;sv=b(view,0x11d);}
 show(view,0);rail(frames[0],horizontal,first,fc,fv);rail(frames[1],vertical,second,sc,sv);
}
typedef struct{uint32_t context,surface;int32_t left,top,right,bottom;} canvas;
typedef struct{uint32_t surface;int32_t x,y,width,height;uint8_t color,pad[3];} command;
static void fill(const canvas*c,int32_t x,int32_t y,int32_t width,int32_t height,uint32_t color){
 int32_t right=x+width,bottom=y+height;if(x<c->left)x=c->left;if(y<c->top)y=c->top;if(right>c->right)right=c->right;if(bottom>c->bottom)bottom=c->bottom;
 if(right<=x||bottom<=y)return;command p={c->surface,x,y,right-x,bottom-y,(uint8_t)color,{0,0,0}};((fn2)0x5323c588)(c->context,(uint32_t)(uintptr_t)&p);
}
static void circle(const canvas*c,int32_t x,int32_t y,int32_t radius,uint32_t color){
 int32_t dx=radius;uint32_t bound=(uint32_t)(radius*(radius+1));
 for(int32_t dy=0;dy<=radius;dy++){while((uint32_t)(dx*dx+dy*dy)>bound)dx--;fill(c,x-dx,y-dy,2*dx+1,1,color);if(dy)fill(c,x-dx,y+dy,2*dx+1,1,color);}
}
void m10v_level_draw(uint32_t view,uint32_t surface){
 if(surface&&b(view,0x9e)&&((fn1)0x5323bbb8)(0)){
  uint32_t context=((fn1)0x5323bd30)(0);if(context){
   int32_t*clip=(int32_t*)(uintptr_t)(view+0x64),*g=(int32_t*)(uintptr_t)(view+0x30);canvas c={context,surface,clip[0],clip[1],clip[0]+clip[2],clip[1]+clip[3]};int32_t x=g[0]+g[2]/2,y=g[1]+g[3]/2;
   if(g[2]>g[3])fill(&c,g[0],y-2,g[2],5,16);else fill(&c,x-2,g[1],5,g[3],16);
   circle(&c,x,y,21,16);circle(&c,x,y,20,2);circle(&c,x,y,17,0);
   if(g[2]>g[3]){fill(&c,g[0],y-1,g[2],3,2);x+=(int8_t)b(view,0xf6);}else{fill(&c,x-1,g[1],3,g[3],2);y+=(int8_t)b(view,0xf6);}
   circle(&c,x,y,18,16);circle(&c,x,y,17,b(view,0xf7));
  }
 }((fn2)0x535880b0)(view,surface);
}
