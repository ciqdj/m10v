/* Original square artwork. Glyph coverage is generated from OFL Noto Sans. */
#include "m10v_film_card.h"
#include "m10v_film_card_data.h"
static uint32_t rgba(uint32_t c){return (c&0xff00ff00u)|((c&255u)<<16)|((c>>16)&255u);}
/* Lossless expansion of the existing Noto glyphs; no heap allocation. */
static void glyph(uint8_t *pixels,uint32_t ch){
 uint32_t at=0,i=glyph_offsets[ch],end=glyph_offsets[ch+1];
 while(i<end&&at<320){
  uint32_t token=glyph_data[i++],run=(token&127u)+1u;
  uint32_t repeated=token&128u,value=repeated?glyph_data[i++]:0;
  for(uint32_t n=0;n<run&&at<320;n++)pixels[at++]=(uint8_t)(repeated?value:glyph_data[i++]);
 }
}
static void caption_pixel(uint32_t *p,uint32_t at,uint32_t a){
 if(!a)return;
 uint32_t old=rgba(p[at]),out=0xff000000u;
 for(uint32_t shift=0;shift<24;shift+=8)out|=((((0xffeff7f5u>>shift)&255)*a+((old>>shift)&255)*(255-a)+127)/255)<<shift;
 p[at]=rgba(out);
}
static void caption(uint32_t *p,uint32_t index){
 uint32_t at=120*120,i=caption_offsets[index],end=caption_offsets[index+1];
 while(i<end&&at<M10V_CARD_PIXELS){
  uint32_t token=caption_rle[i++],run=(token&127u)+1u;
  uint32_t repeated=token&128u,value=repeated?caption_rle[i++]:0;
  for(uint32_t n=0;n<run&&at<M10V_CARD_PIXELS;n++){
   uint32_t packed=repeated?value:caption_rle[i++];
   for(uint32_t bit=0;bit<8&&at<M10V_CARD_PIXELS;bit+=2,at++)caption_pixel(p,at,((packed>>bit)&3u)*85u);
  }
 }
}
static void custom_caption(uint32_t *p,const char *name){
 uint32_t width=0;for(uint32_t i=0;name[i];i++)width+=smooth_width[(uint8_t)name[i]-32];
 if(!width)return;
 uint32_t scale=width>114?width:114,draw_width=width>114?114:width,height=0;
 while((height+1)*scale<=20*114)height++;
 if(!height)height=1;
 uint32_t x=(120-draw_width)/2,y=120+(28-height)/2;
 uint32_t offset=0,k=0,loaded=~0u;uint8_t pixels[320];
 for(uint32_t i=0;i<draw_width;i++){
  uint32_t source=i*scale/114;
  while(name[k]&&source>=offset+smooth_width[(uint8_t)name[k]-32])offset+=smooth_width[(uint8_t)name[k++]-32];
  if(!name[k]||source-offset>=16)continue;
  if(loaded!=k){glyph(pixels,(uint8_t)name[k]-32);loaded=k;}
  for(uint32_t j=0;j<height;j++)caption_pixel(p,(y+j)*120+x+i,pixels[(j*scale/114)*16+source-offset]);
 }
}
static void rect(uint32_t *p,uint32_t x,uint32_t y,uint32_t w,uint32_t h,uint32_t c){
 for(uint32_t j=y;j<y+h&&j<M10V_CARD_HEIGHT;j++)for(uint32_t i=x;i<x+w&&i<M10V_CARD_WIDTH;i++)p[j*M10V_CARD_WIDTH+i]=rgba(c);
}
static void text(uint32_t *p,const char *s,uint32_t y,uint32_t color){
 uint32_t width=0;for(uint32_t k=0;s[k];k++)if((uint8_t)s[k]>=32&&(uint8_t)s[k]<127)width+=smooth_width[(uint8_t)s[k]-32];
 uint32_t x=width<M10V_CARD_WIDTH?(M10V_CARD_WIDTH-width)/2:0;
 for(uint32_t k=0;s[k];k++){
  uint32_t ch=(uint8_t)s[k];if(ch<32||ch>=127)continue;ch-=32;
  uint8_t pixels[320];glyph(pixels,ch);
  for(uint32_t j=0;j<20&&y+j<M10V_CARD_HEIGHT;j++)for(uint32_t i=0;i<16&&x+i<M10V_CARD_WIDTH;i++){
   uint32_t a=pixels[j*16+i];if(!a)continue;
   uint32_t *v=&p[(y+j)*M10V_CARD_WIDTH+x+i],old=rgba(*v),out=0xff000000u;
   for(uint32_t shift=0;shift<24;shift+=8)out|=((((color>>shift)&255)*a+((old>>shift)&255)*(255-a)+127)/255)<<shift;
   *v=rgba(out);
  }
  x+=smooth_width[ch];
 }
}
static int render(uint32_t *p,const char *main,const char *sub,uint32_t c,uint32_t ink,const char *brand,uint32_t header,uint32_t accent,uint32_t slot,uint32_t selected){
 if(!p||slot>=10)return -1;
 for(uint32_t i=0;i<M10V_CARD_PIXELS;i++)p[i]=rgba(0xff20271fu);
 rect(p,6,5,108,108,0xff92968bu);rect(p,8,7,104,104,c);
 rect(p,8,7,104,27,header);rect(p,8,35,104,1,0xfff3eedcu);
 text(p,brand,15,header==0xffffcf32u?0xffae2636u:0xfffff8e5u);
 text(p,main,48,ink);text(p,sub,73,ink);rect(p,8,104,104,7,accent);
 if(selected)for(uint32_t y=0;y<16;y++)rect(p,102+y,2+y,16-y,1,0xffe9dc45u);
 return 0;
}
int m10v_film_card_render(uint32_t *p,uint32_t film,uint32_t slot,uint32_t selected){
 uint32_t i;if(film>=1&&film<=78)i=film-1;else if(film>=289&&film<=298)i=78+film-289;else return -1;
 int result=render(p,box_cards[i].main,box_cards[i].sub,box_cards[i].color,box_cards[i].ink,box_cards[i].brand,box_cards[i].header,box_cards[i].accent,slot,selected);
 if(!result){if(i<32)custom_caption(p,legacy_caption_names[i]);else caption(p,i);}
 return result;
}
int m10v_film_card_custom(uint32_t *p,const char *name,uint32_t slot,uint32_t selected){
 if(!p||!name||slot>=10)return -1;
 char main[10]={0};uint32_t n=0,hash=2166136261u,length=0;
 for(;length<24&&name[length];length++){
  uint32_t c=(uint8_t)name[length];if(c<32||c>126)return -1;if(c>='a'&&c<='z')c-=32;
  hash=(hash^c)*16777619u;if(n<8&&((c>='A'&&c<='Z')||(c>='0'&&c<='9')))main[n++]=(char)c;
 }
 if(!length||length==24)return -1;if(!n){main[0]='L';main[1]='U';main[2]='T';}
 static const uint32_t colors[]={0xff508b9du,0xffa484adu,0xffc78d48u,0xff669c7au,0xffc94c47u,0xff667fa7u,0xffb47787u,0xff917b61u};
 int result=render(p,main,"LUT",0xffeee9d9u,0xff25363bu,"M10V",colors[hash&7],colors[hash&7],slot,selected);
 if(!result)custom_caption(p,name);
 return result;
}
