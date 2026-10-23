/* Original square artwork. Glyph coverage is generated from OFL Noto Sans. */
#include "m10v_film_card.h"
#include "m10v_film_card_data.h"
static uint32_t rgba(uint32_t c){return (c&0xff00ff00u)|((c&255u)<<16)|((c>>16)&255u);}
static void rect(uint32_t *p,uint32_t x,uint32_t y,uint32_t w,uint32_t h,uint32_t c){
 for(uint32_t j=y;j<y+h&&j<M10V_CARD_HEIGHT;j++)for(uint32_t i=x;i<x+w&&i<M10V_CARD_WIDTH;i++)p[j*M10V_CARD_WIDTH+i]=rgba(c);
}
static void text(uint32_t *p,const char *s,uint32_t y,uint32_t color){
 uint32_t width=0;for(uint32_t k=0;s[k];k++)if((uint8_t)s[k]>=32&&(uint8_t)s[k]<127)width+=smooth_width[(uint8_t)s[k]-32];
 uint32_t x=width<M10V_CARD_WIDTH?(M10V_CARD_WIDTH-width)/2:0;
 for(uint32_t k=0;s[k];k++){
  uint32_t ch=(uint8_t)s[k];if(ch<32||ch>=127)continue;ch-=32;
  for(uint32_t j=0;j<20&&y+j<M10V_CARD_HEIGHT;j++)for(uint32_t i=0;i<16&&x+i<M10V_CARD_WIDTH;i++){
   uint32_t a=smooth_glyph[ch][j*16+i];if(!a)continue;
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
 if(selected){rect(p,102,2,16,16,0xffe9dc45u);for(uint32_t i=0;i<5;i++)rect(p,105+i,9+i,2,2,0xff20271du);for(uint32_t i=0;i<8;i++)rect(p,109+i,13-i,2,2,0xff20271du);}
 return 0;
}
int m10v_film_card_render(uint32_t *p,uint32_t film,uint32_t slot,uint32_t selected){
 uint32_t i;if(film>=1&&film<=78)i=film-1;else if(film>=289&&film<=297)i=78+film-289;else return -1;
 return render(p,box_cards[i].main,box_cards[i].sub,box_cards[i].color,box_cards[i].ink,box_cards[i].brand,box_cards[i].header,box_cards[i].accent,slot,selected);
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
 return render(p,main,"LUT",0xffeee9d9u,0xff25363bu,"M10V",colors[hash&7],colors[hash&7],slot,selected);
}
