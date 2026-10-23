#include "m10v_zoom.h"
/* Resource builder verifies this base before appending the seven editor
 * captions and 73 focal labels. Existing film IDs remain unchanged. */
uint32_t m10v_zoom_title(void){return 1024;}
uint32_t m10v_zoom_caption(uint32_t bits){
 uint32_t mm=m10v_zoom_mm(bits);return mm?1031+mm-28:2;
}
uint32_t m10v_zoom_bits(uint32_t mm){
 if(mm<M10V_ZOOM_MIN_MM||mm>M10V_ZOOM_MAX_MM)return 0;
 uint32_t exponent=mm>=56?1u:0u;
 uint32_t mantissa=((mm<<(23-exponent))+14)/28;
 return ((127+exponent)<<23)|(mantissa-0x800000u);
}
uint32_t m10v_zoom_mm(uint32_t bits){
 if(bits<0x3f800000u||bits>0x40649249u)return 0;
 uint32_t exponent=(bits>>23)-127u,shift=23-exponent;
 uint32_t mm=(((bits&0x7fffffu)|0x800000u)*28u+(1u<<(shift-1)))>>shift;
 return m10v_zoom_bits(mm)==bits?mm:0;
}
static uint32_t get(const uint8_t *b){
 return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);
}
static void put(uint8_t *b,uint32_t v){for(unsigned i=0;i<4;i++)b[i]=(uint8_t)(v>>(8*i));}
static uint32_t crc(const uint8_t *b){
 uint32_t c=~0u;
 for(unsigned i=0;i<20;i++){
  c^=b[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));
 }
 return ~c;
}
static int focal(uint32_t mm){return mm>=M10V_ZOOM_MIN_MM&&mm<=M10V_ZOOM_MAX_MM;}
static int decode(m10v_zoom_state *s,const uint8_t *b){
 if(get(b)!=0x315a304du||get(b+4)!=1||get(b+20)!=crc(b)||
    !focal(get(b+12))||!focal(get(b+16)))return 0;
 s->sequence=get(b+8);s->mm[0]=(uint16_t)get(b+12);s->mm[1]=(uint16_t)get(b+16);return 1;
}
static void encode(uint8_t *b,const m10v_zoom_state *s){
 put(b,0x315a304du);put(b+4,1);put(b+8,s->sequence);
 put(b+12,s->mm[0]);put(b+16,s->mm[1]);put(b+20,crc(b));
}
int m10v_zoom_load(m10v_zoom_state *s,const m10v_zoom_io *io){
 if(!s||!io||!io->read)return -1;
 uint8_t b[M10V_ZOOM_BYTES];m10v_zoom_state candidate;int found=0,failed=0;
 s->sequence=0;s->mm[0]=35;s->mm[1]=50;
 for(unsigned p=0;p<2;p++){
  int result=io->read(io->context,p,b,sizeof(b));
  if(result<0)failed=1;
  if(result==1&&decode(&candidate,b)&&
     (!found||(candidate.sequence-s->sequence!=0&&candidate.sequence-s->sequence<0x80000000u))){
   *s=candidate;found=1;
  }
 }
 return found?1:failed?-1:0;
}
void m10v_zoom_open(m10v_zoom_editor *e,const m10v_zoom_state *s,unsigned slot){
 if(!e)return;
 e->slot=2;e->sequence=0;e->value=0;
 if(s&&slot<2&&focal(s->mm[slot])){e->slot=slot;e->value=s->mm[slot];e->sequence=s->sequence;}
}
void m10v_zoom_adjust(m10v_zoom_editor *e,int direction){
 if(!e||e->slot>=2||!focal(e->value))return;
 if(direction<0&&e->value>M10V_ZOOM_MIN_MM)e->value--;
 if(direction>0&&e->value<M10V_ZOOM_MAX_MM)e->value++;
}
int m10v_zoom_replace(m10v_zoom_state *s,uint32_t first,uint32_t second,const m10v_zoom_io *io){
 if(!s||!io||!io->read||!io->write||!focal(first)||!focal(second)||!focal(s->mm[0])||!focal(s->mm[1]))return -1;
 if(s->mm[0]==first&&s->mm[1]==second)return 0;
 m10v_zoom_state next=*s,check;uint8_t b[M10V_ZOOM_BYTES],back[M10V_ZOOM_BYTES];
 next.sequence++;next.mm[0]=(uint16_t)first;next.mm[1]=(uint16_t)second;encode(b,&next);
 unsigned page=next.sequence&1u;
 if(io->write(io->context,page,b,sizeof(b))!=1||io->read(io->context,page,back,sizeof(back))!=1||!decode(&check,back))return -1;
 for(unsigned i=0;i<sizeof(b);i++)if(b[i]!=back[i])return -1;
 *s=next;return 0;
}
int m10v_zoom_save(m10v_zoom_state *s,const m10v_zoom_editor *e,const m10v_zoom_io *io){
 if(!s||!e||e->slot>=2||!focal(e->value))return -1;
 if(e->sequence!=s->sequence)return M10V_ZOOM_STALE;
 return m10v_zoom_replace(s,e->slot==0?e->value:s->mm[0],e->slot==1?e->value:s->mm[1],io);
}
