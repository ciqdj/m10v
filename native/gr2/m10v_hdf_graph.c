#include "m10v_hdf_graph.h"
#include "m10v_hdf.h"
#include "../../compat/gr2-v1/native/gr3/m10v_sd_library.h"
typedef struct {uint32_t magic,context,control,sequence,workspace,geometry,crc,reserved[9];} graph_owner;
_Static_assert(sizeof(graph_owner)==64,"HDF workspace header");
#define MAGIC 0x47324857u
static int packet(const uint32_t *p,uint32_t bytes){uintptr_t a=(uintptr_t)p;return a&&!(a&3u)&&a<=UINT32_MAX-bytes;}
int gr2_hdf_graph_prepare(const uint32_t *request,uint32_t hdr){
 if(!packet(request,64))return 0;
 uint32_t workspace=request[12];
 if(gr2_hdf_workspace_bytes((const void *)(uintptr_t)workspace)!=0xe5800u)return 0;
 graph_owner *header=(graph_owner *)(uintptr_t)(workspace+0xe000u);
 /* A recycled lease must never expose a previous photograph's curves, even
  * when the next graph is stock/HDR or its image snapshot cannot be read. */
 header->magic=0;
 gr2_hdf_frame frame;
 uint32_t context=request[15],geometry=request[10],width=geometry&65535u,height=geometry>>16;
 if(hdr||!gr2_hdf_frame_read((const uint8_t *)(uintptr_t)context,&frame)||
    !(frame.control&3u)||width<4u||width>4928u||height<2u||height>3264u||(width&1u)||(height&1u))return 0;
 uint16_t *curves[4];uint8_t thresholds[4];
 for(uint32_t i=0;i<4u;i++)curves[i]=(uint16_t *)(uintptr_t)(workspace+i*8192u);
 ((void (*)(uint16_t **,uint8_t *,uint32_t))(uintptr_t)0xa014d461u)(curves,thresholds,0);
 if(gr2_hdf_prepare_bands((uint16_t *)(uintptr_t)workspace,0xe5800u,frame.control&3u)!=1)return 0;
 graph_owner next;
 for(uint32_t i=0;i<16u;i++)((volatile uint32_t *)&next)[i]=0;
 next.magic=MAGIC;next.context=context;next.control=frame.control;next.sequence=frame.sequence;next.workspace=workspace;next.geometry=geometry;
 next.crc=m10v_sd_crc((const uint8_t *)&next,24);
 for(uint32_t i=1;i<16u;i++)((uint32_t *)header)[i]=((const uint32_t *)&next)[i];
 header->magic=MAGIC;return 1;
}
uint32_t gr2_hdf_graph_curve(uint32_t original,const uint32_t *level){
 if(!packet(level,0x60u)||level[0]<1u||level[0]>11u)return original;
 uint32_t workspace=level[0x4c/4];
 if(gr2_hdf_workspace_bytes((const void *)(uintptr_t)workspace)!=0xe5800u)return original;
 const graph_owner *header=(const graph_owner *)(uintptr_t)(workspace+0xe000u);
 if(header->magic!=MAGIC||header->workspace!=workspace||header->crc!=m10v_sd_crc((const uint8_t *)header,24))return original;
 gr2_hdf_frame frame;
 if(!gr2_hdf_frame_read((const uint8_t *)(uintptr_t)header->context,&frame)||
    frame.control!=header->control||frame.sequence!=header->sequence||!(frame.control&3u))return original;
 return workspace+GR2_HDF_CURVE_OFFSET+(level[0]-1u)*GR2_HDF_CURVE_BYTES;
}

extern uint32_t gr2_clarity_original(const uint32_t *,uint32_t);
uint32_t gr2_hdf_core(const uint32_t *request,uint32_t hdr){
 int prepared=gr2_hdf_graph_prepare(request,hdr);
 volatile uint32_t *strength=0;uint32_t previous=0;
 if(prepared){
  strength=(volatile uint32_t *)(uintptr_t)(request[15]+0x418u);
  previous=*strength;*strength=1;
 }
 uint32_t result=gr2_clarity_original(request,hdr);
 if(prepared)*strength=previous;
 gr2_hdf_graph_prepare(request,1); /* Retire the synchronous workspace header. */
 return result;
}
