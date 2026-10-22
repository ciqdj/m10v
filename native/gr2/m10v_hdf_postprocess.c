#include "m10v_hdf_postprocess.h"
#include "m10v_hdf.h"
#include "m10v_hdf_layout.h"
#include "m10v_hdf_configuration.h"
#include "m10v_configuration.h"
extern uint32_t gr2_postprocess_original(uint8_t *);
static const char label[]="m10v-hdf";
static uint32_t word(const void *p){return *(const uint32_t *)p;}
static int range(uint32_t p,uint32_t n){return p&&n&&p<=UINT32_MAX-n;}
static int disjoint(uint32_t a,uint32_t an,uint32_t b,uint32_t bn){return a+an<=b||b+bn<=a;}
static int view(uint32_t handle,uint32_t *data,uint32_t *capacity){
 if((handle&3u)||!range(handle,24))return 0;
 const uint32_t *p=(const uint32_t *)(uintptr_t)handle;
 if(p[0]!=0x42554646u||!range(p[1],p[5]))return 0;
 *data=p[1];*capacity=p[5];return 1;
}
static uint32_t acquire(uint32_t tag){
 return ((uint32_t (*)(uint32_t,uint32_t,const char *,uint32_t))(uintptr_t)0xA029A94Fu)(tag,UINT32_MAX,label,1);
}
static void drop(uint32_t *handle){
 if(*handle)((void (*)(uint32_t *,const char *,uint32_t))(uintptr_t)0xA029AA1Bu)(handle,label,2);
}
static int contains(uint32_t base,uint32_t bytes,uint32_t pointer,uint32_t length){
 return range(pointer,length)&&pointer>=base&&length<=bytes&&pointer-base<=bytes-length;
}
static int planes(uint32_t *root,uint8_t *context,uint32_t base,uint32_t capacity){
 uint32_t geometry=word(context+0x258),width=geometry&65535u,height=geometry>>16;
 uint32_t ys=word(context+0x224),cs=word(context+0x228);
 if(width<4u||width>4928u||height<2u||height>3264u||(width&1u)||(height&1u)||ys<width||ys>16384u||cs>8192u)return 0;
 for(uint32_t i=0;i<19u;i++)((volatile uint32_t *)root)[i]=0;
 root[0]=0x0D000000u;root[1]=base;
 ((void (*)(uint32_t *,uint32_t *,uint32_t *,uint8_t *,int32_t,uint32_t))(uintptr_t)0xA02AD261u)(root+1,root+2,root+3,context,-1,3);
 uint32_t yn=ys*(height-1u)+width;
 if(!contains(base,capacity,root[1],yn))return 0;
 if(root[2]||root[3]){
  if(cs<width/2u||cs>8192u)return 0;
  uint32_t cn=cs*(height-1u)+width/2u;
  if(!contains(base,capacity,root[2],cn)||!contains(base,capacity,root[3],cn)||
     !disjoint(root[1],yn,root[2],cn)||!disjoint(root[1],yn,root[3],cn)||!disjoint(root[2],cn,root[3],cn))return 0;
 }
 root[4]=root[9]=ys;root[5]=root[10]=cs;
 for(uint32_t i=0;i<3u;i++)root[6u+i]=root[1u+i];
 root[11]=geometry;root[16]=(uint32_t)(uintptr_t)context;return 1;
}
uint32_t gr2_hdf_postprocess(uint8_t *context){
 gr2_hdf_frame frame;uint32_t primary=0,base=0,capacity=0,temp=0,held=0;int inserted=0,owned_temporary=0;
 int eligible=gr2_hdf_frame_read(context,&frame)&&(frame.control&3u)&&
              gr2_hdf_layout_supports_graph()&&context[0x408]<=20u&&context[0x408]!=16u&&context[0x408]!=19u;
 if(eligible){
  primary=word(context+0x1f0);eligible=view(primary,&base,&capacity);
 }
 if(eligible){
  temp=word(context+0x1f8);
  if(!temp){temp=acquire(0x17);if(temp){*(uint32_t *)(context+0x1f8)=temp;inserted=1;}}
  uint32_t data=0,bytes=0;
  if(view(temp,&data,&bytes)&&bytes==0x1f0e020u&&disjoint(base,capacity,data,bytes)){
   owned_temporary=1;
   held=((uint32_t (*)(uint32_t))(uintptr_t)0xA00E02ABu)(temp);
  }
 }
 /* Retain a metadata alias, not a third JPEG pixel block. Stock effects may
  * consume their original handle; the alias spans both synchronous graphs. */
 uint32_t original=gr2_postprocess_original(context);
 /* The valid early reservation belongs to this phase even if alias
  * metadata allocation fails. Stock effects may already have consumed it. */
 if((inserted||owned_temporary)&&word(context+0x1f8)==temp)drop((uint32_t *)(context+0x1f8));
 uint32_t small=0,large=0,temporary=0,temporary_bytes=0,root[19];
 gr2_hdf_frame current;
 if(!held||!gr2_hdf_frame_read(context,&current)||current.control!=frame.control||current.sequence!=frame.sequence||
    !gr2_hdf_layout_supports_graph()||word(context+0x1f0)!=primary||
    !view(primary,&base,&capacity)||!view(held,&temporary,&temporary_bytes)||temporary_bytes!=0x1f0e020u||
    !planes(root,context,base,capacity))goto done;
 small=acquire(0x20);if(!small)goto done;
 large=acquire(0x2e);if(!large)goto done;
 uint32_t small_data=0,small_bytes=0,large_data=0,large_bytes=0;
 if(!view(small,&small_data,&small_bytes)||small_bytes!=0xe5800u||gr2_hdf_workspace_bytes((const void *)(uintptr_t)small_data)!=small_bytes||
    !view(large,&large_data,&large_bytes)||large_bytes!=0x2000000u||
    !disjoint(base,capacity,small_data,small_bytes)||!disjoint(base,capacity,large_data,large_bytes)||
    !disjoint(temporary,temporary_bytes,small_data,small_bytes)||!disjoint(temporary,temporary_bytes,large_data,large_bytes))goto done;
 root[13]=small_data;root[14]=large_data;root[15]=temporary;
 ((void (*)(const uint32_t *))(uintptr_t)0xA0131281u)(root);
done:
 drop(&small);drop(&large);drop(&held);return original;
}

extern uint32_t gr2_production_original(uint8_t *);
uint32_t gr2_hdf_production_begin(uint8_t *context){
 gr2_configuration_begin(context);
 return gr2_production_original(context);
}
