/* Original raster artwork: no fonts, files, floating point or heap allocation. */
#include "m10v_film_card.h"
#include "m10v_film_card_data.h"
static uint32_t rgba(uint32_t c){return (c&0xff00ff00u)|((c&255u)<<16)|((c>>16)&255u);}
static void rect(uint32_t *p,uint32_t x,uint32_t y,uint32_t w,uint32_t h,uint32_t c){
 for(uint32_t j=y;j<y+h;j++)for(uint32_t i=x;i<x+w;i++)p[j*M10V_CARD_WIDTH+i]=rgba(c);
}
static void lettering(uint32_t *p,const char *s,uint32_t x,uint32_t y,uint32_t scale,uint32_t rotate,uint32_t c){
 uint32_t n=0;while(s[n])n++;
 for(uint32_t k=0;k<n;k++){
  uint32_t g=(uint32_t)(s[k]<='9'?s[k]-'0':s[k]-'A'+10);
  uint32_t width=rotate?5:3,height=rotate?7:5;
  for(uint32_t j=0;j<height;j++)for(uint32_t i=0;i<width;i++)if((rotate?card_large_glyphs[g][j]:card_glyphs[g][j])&(1u<<(width-1-i))){
   uint32_t xx=rotate?j*scale:(k*4+i)*scale;
   uint32_t yy=rotate?((n-1-k)*6+4-i)*scale:j*scale;
   rect(p,x+xx,y+yy,scale,scale,c);
  }
 }
}
static int render(uint32_t *p,const char *main,const char *sub,uint32_t c,uint32_t ink,uint32_t slot,uint32_t selected){
 if(!p||slot>=5)return -1;
 for(uint32_t y=0;y<M10V_CARD_HEIGHT;y++)for(uint32_t x=0;x<M10V_CARD_WIDTH;x++){
  uint32_t rail=y<24||y>=172,hole=(y>=6&&y<18)||(y>=178&&y<190);
  p[y*M10V_CARD_WIDTH+x]=rgba(rail?hole&&x%24>=6&&x%24<18?0xff11191cu:0xff344349u:0xff182327u);
 }
 rect(p,25,37,80,122,0xff080f12u);
 rect(p,20,34,80,118,c);
 rect(p,20,29,80,5,0xff080f12u);rect(p,20,152,80,6,0xff080f12u);
 rect(p,23,38,15,110,ink==0xff244975u?0xfff47b22u:0xffd6cb50u);
 rect(p,27,112,7,13,0xfff8ed83u);rect(p,27,131,7,13,0xfff8ed83u);
 const char *s=main;uint32_t n=0;while(s[n])n++;
 uint32_t scale=4,height=(n*6-1)*scale;
 lettering(p,s,52,34+(118-height)/2,scale,1,ink);
 s=sub;n=0;while(s[n])n++;
 if(n)lettering(p,s,(120-(n*4-1))/2,160,1,0,0xffd4e2e2u);
 for(uint32_t i=0;i<=slot;i++)rect(p,8+i*9,168,5,3,selected?0xfff1e450u:0xff9cb8bfu);
 return 0;
}

int m10v_film_card_render(uint32_t *p,uint32_t film,uint32_t slot,uint32_t selected){
 if(film==290)return render(p,"PIXEL","WORLD",0xff76a849u,0xff152c1cu,slot,selected);
 if(film==289)return render(p,"CHARM","KODAK",0xfffad84eu,0xff101010u,slot,selected);
 if(!film||film>78)return -1;
 return render(p,cards[film-1].main,cards[film-1].sub,cards[film-1].color,cards[film-1].ink,slot,selected);
}
int m10v_film_card_custom(uint32_t *p,const char *name,uint32_t slot,uint32_t selected){
 if(!p||!name||slot>=5)return -1;
 char main[6]={0};uint32_t n=0,hash=2166136261u,length=0;
 for(;length<24&&name[length];length++){
  uint32_t c=(uint8_t)name[length];if(c<32||c>126)return -1;
  if(c>='a'&&c<='z')c-=32;
  hash=(hash^c)*16777619u;
  if(n<5&&((c>='A'&&c<='Z')||(c>='0'&&c<='9')))main[n++]=(char)c;
 }
 if(!length||length==24)return -1;
 if(!n){main[0]='L';main[1]='U';main[2]='T';}
 static const uint32_t palette[]={0xff508b9du,0xffa484adu,0xffc78d48u,0xff669c7au,0xffc94c47u,0xff667fa7u,0xffb47787u,0xff917b61u};
 return render(p,main,"LUT",palette[hash&7],0xfff3faf9u,slot,selected);
}
