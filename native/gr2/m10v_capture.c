#include "m10v_capture.h"
#include "../gr3/m10v_sd_library.h"
_Static_assert(sizeof(m10v_gr2_frame)==128,"GR II inline frame ABI changed");
static int valid(uint32_t p,uint32_t n){return p&&n&&n<=UINT32_MAX-p;}
static int overlaps(uint32_t a,uint32_t an,uint32_t b,uint32_t bn){return a<b+bn&&b<a+an;}
static int hits(uint32_t p,uint32_t n,uint32_t y,uint32_t yn,uint32_t c,uint32_t cn){
    return !valid(p,n)||overlaps(p,n,y,yn)||overlaps(p,n,c,cn);
}
int gr2_render_planar(const m10v_gr2_image *im,const m10v_library_state *state,uint32_t slot,
                      const m10v_library_date *date,uint32_t seed,uint8_t *scratch,uint32_t scratch_bytes){
    if(!im||!m10v_library_valid(state)||slot>=5||im->format!=0x422||im->width<2||im->width>4928||
       im->height<2||im->height>3264||(im->width&1)||(im->height&1)||im->y_stride<im->width||
       im->y_stride>16384||im->chroma_stride>8192||im->chroma_stride*2!=im->y_stride)return -1;
    uint32_t yn=im->y_stride*im->height,cn=im->chroma_stride*im->height;
    uint32_t y=(uint32_t)(uintptr_t)im->y,u=(uint32_t)(uintptr_t)im->u,v=(uint32_t)(uintptr_t)im->v;
    if(im->y_bytes<yn||im->u_bytes!=cn||im->v_bytes!=cn||!valid(y,yn)||!valid(u,2*cn)||u+cn!=v||overlaps(y,yn,u,2*cn))return -1;
    if(hits((uint32_t)(uintptr_t)im,sizeof(*im),y,yn,u,2*cn)||
       hits((uint32_t)(uintptr_t)state,sizeof(*state),y,yn,u,2*cn)||
       (date&&hits((uint32_t)(uintptr_t)date,sizeof(*date),y,yn,u,2*cn))||
       (scratch_bytes&&hits((uint32_t)(uintptr_t)scratch,scratch_bytes,y,yn,u,2*cn)))return -1;
    m10v_library_image paired={im->y,im->u,yn,2*cn,im->width,im->height,im->y_stride};
    if(!gr2_chroma_shuffle(im->u,cn,0))return -1;
    int result=m10v_library_render(&paired,state,slot,date,seed,scratch,scratch_bytes);
    gr2_chroma_shuffle(im->u,cn,1);
    return result;
}
static uint32_t be32(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
/* Caller retains the image reference throughout this synchronous check. This
 * validates allocation identity, not a lock against concurrent retirement. */
uint32_t gr2_image_owner_bytes(const uint8_t *context){
    uint32_t owner=(uint32_t)(uintptr_t)context;
    if((owner&3)||owner<8)return 0;
    const uint8_t *pool=(const uint8_t *)(uintptr_t)0xa05fb0e8u;
    if(be32((const uint8_t *)(uintptr_t)0xa0129c54u)!=(uint32_t)(uintptr_t)pool||
       be32(pool)!=0x4d504c20u)return 0;
    uint32_t body=be32((const uint8_t *)(uintptr_t)0xa01137ecu),block=be32(pool+8);
    if(body<0xfb0cu||body>0x1000u+0xfb0cu||(body&3)||block!=body+8||be32(pool+12)!=60*block)return 0;
    uint32_t id=((uint32_t)pool[20]<<8)|pool[21];
    const uint8_t *maximum=(const uint8_t *)(uintptr_t)0xa00b5bfcu;
    if(!id||id>(((uint32_t)maximum[0]<<8)|maximum[1]))return 0;
    uint32_t table=be32((const uint8_t *)(uintptr_t)0xa00b5bdcu);
    if((table&3)||!valid(table,24*id))return 0;
    const uint8_t *record=(const uint8_t *)(uintptr_t)(table+24*(id-1));
    if(record[0]!=255||record[1]!=255||be32(record+16)!=block||be32(record+12)!=60*block)return 0;
    uint32_t base=be32(record+20);
    if(!valid(base,60*block)||owner-8<base)return 0;
    uint32_t candidate=base;
    for(uint32_t i=0;i<60;i++,candidate+=block){
        if(candidate==owner-8)return be32(context-8)==0x494d4720u&&!be32(context-4)?body:0;
    }
    return 0;
}
static void copy_bytes(void *destination,const void *source,uint32_t bytes){
    for(uint32_t i=0;i<bytes;i++)((uint8_t *)destination)[i]=((const uint8_t *)source)[i];
}
int gr2_frame_freeze(uint8_t *context,const m10v_library_state *source,uint32_t slot,uint32_t seed){
    if(slot>=5||!source||gr2_image_owner_bytes(context)!=0xfb8cu)return 0;
    uint32_t address=(uint32_t)(uintptr_t)source,owner=(uint32_t)(uintptr_t)context-8;
    if(!valid(address,sizeof(*source))||overlaps(address,sizeof(*source),owner,0xfb94u))return 0;
    m10v_gr2_frame frame;frame.reserved=0;frame.magic=0x47324652u;frame.version=1;frame.slot=slot;frame.seed=seed;
    copy_bytes(&frame.state,source,sizeof(frame.state));
    if(!m10v_library_valid(&frame.state))return 0;
    uint8_t *tail=context+0xfb0c;
    for(uint32_t i=0;i<sizeof(frame);i++)if(tail[i])return 0;
    frame.crc=m10v_sd_crc((const uint8_t *)&frame,120);
    copy_bytes(tail+4,(const uint8_t *)&frame+4,sizeof(frame)-4);
    copy_bytes(tail,&frame,4);return 1;
}
int gr2_frame_read(const uint8_t *context,m10v_gr2_frame *out){
    if(!out||gr2_image_owner_bytes(context)!=0xfb8cu)return 0;
    uint32_t address=(uint32_t)(uintptr_t)out,owner=(uint32_t)(uintptr_t)context-8;
    if(!valid(address,sizeof(*out))||overlaps(address,sizeof(*out),owner,0xfb94u))return 0;
    m10v_gr2_frame frame;copy_bytes(&frame,context+0xfb0c,sizeof(frame));
    if(frame.magic!=0x47324652u||frame.version!=1||frame.slot>=5||frame.reserved||
       frame.crc!=m10v_sd_crc((const uint8_t *)&frame,120)||!m10v_library_valid(&frame.state))return 0;
    copy_bytes(out,&frame,sizeof(frame));return 1;
}
static int span(uint32_t handle,uint32_t *address,uint32_t *bytes,int used){
    if((handle&3)||!valid(handle,24))return 0;
    const uint8_t *p=(const uint8_t *)(uintptr_t)handle;
    if(be32(p)!=0x42554646u)return 0;
    *address=be32(p+4);uint32_t capacity=be32(p+0x14);
    *bytes=used?be32(p+8):capacity;
    return valid(*address,capacity)&&*bytes<=capacity&&*bytes;
}
static int contains(uint32_t base,uint32_t bytes,uint32_t address,uint32_t length){
    return valid(address,length)&&address>=base&&length<=bytes&&address-base<=bytes-length;
}
int gr2_capture_admit(const uint8_t *context,uint32_t kind,const uint8_t *request,m10v_gr2_image *out){
    if(!context||!request||!out||kind<1||kind>3)return 0;
    uint32_t owner=(uint32_t)(uintptr_t)context,request_address=(uint32_t)(uintptr_t)request;
    uint32_t body=gr2_image_owner_bytes(context);
    if(!body||!valid(owner-8,body+8)||!valid(request_address,48))return 0;
    static const uint16_t sources[3]={0x1f4,0x1fc,0x200};
    uint32_t source=0,source_bytes=0,output=0,output_bytes=0;
    uint32_t source_handle=be32(context+sources[kind-1]),output_handle=be32(context+0x200+4*kind);
    if(!span(source_handle,&source,&source_bytes,1)||
       !span(output_handle,&output,&output_bytes,0)||be32(request+4)!=output||
       be32(request+8)!=be32(context+0x3e0+4*kind))return 0;
    m10v_gr2_image image;
    if(!gr2_capture_decode(request,&image))return 0;
    uint32_t addresses[3]={(uint32_t)(uintptr_t)image.y,(uint32_t)(uintptr_t)image.u,(uint32_t)(uintptr_t)image.v};
    uint32_t sizes[3]={image.y_bytes,image.u_bytes,image.v_bytes};
    /* The producer input (1E0) and RAW-for-DNG (1E4) have distinct lifetimes.
     * Protect either handle while the stock context still retains it. */
    uint32_t raw[2]={0,0},raw_bytes[2]={0,0};
    uint32_t protected[6][2]={{owner-8,body+8},{request_address,48},{source_handle,24},{output_handle,24},{0,24},{0,24}};
    for(uint32_t i=0;i<2;i++){
        uint32_t handle=be32(context+0x1e0+4*i);protected[4+i][0]=handle;
        if(handle&&!span(handle,&raw[i],&raw_bytes[i],0))return 0;
    }
    for(uint32_t i=0;i<3;i++){
        if(!contains(source,source_bytes,addresses[i],sizes[i])||overlaps(addresses[i],sizes[i],output,output_bytes))return 0;
        for(uint32_t j=0;j<2;j++)if(raw_bytes[j]&&overlaps(addresses[i],sizes[i],raw[j],raw_bytes[j]))return 0;
        for(uint32_t j=0;j<6;j++)if(protected[j][0]&&overlaps(addresses[i],sizes[i],protected[j][0],protected[j][1]))return 0;
    }
    /* Reject a caller trying to place the result in any protected buffer. */
    uint32_t destination=(uint32_t)(uintptr_t)out;
    if(!valid(destination,sizeof(*out))||overlaps(destination,sizeof(*out),source,source_bytes)||
       overlaps(destination,sizeof(*out),output,output_bytes))return 0;
    for(uint32_t i=0;i<6;i++)if(protected[i][0]&&overlaps(destination,sizeof(*out),protected[i][0],protected[i][1]))return 0;
    for(uint32_t i=0;i<2;i++)if(raw_bytes[i]&&overlaps(destination,sizeof(*out),raw[i],raw_bytes[i]))return 0;
    uint8_t *dst=(uint8_t *)out;const uint8_t *src=(const uint8_t *)&image;
    for(uint32_t i=0;i<sizeof(image);i++)dst[i]=src[i];
    return 1;
}
static int process(const uint8_t *context,uint32_t kind,const uint8_t *request,
                        const m10v_library_state *source_state,uint32_t slot,int frozen){
    if(!frozen&&(!source_state||slot>=5))return -1;
    if(!gr2_cache_before())return -3;
    m10v_gr2_image image;
    if(!gr2_capture_admit(context,kind,request,&image)||image.format!=0x422)return -1;
    m10v_library_state state;uint32_t seed;
    if(frozen){
        m10v_gr2_frame frame;
        if(!gr2_frame_read(context,&frame))return -1;
        copy_bytes(&state,&frame.state,sizeof(state));slot=frame.slot;seed=frame.seed;
    }else{
        copy_bytes(&state,source_state,sizeof(state));seed=state.sequence^(uint32_t)(uintptr_t)image.y;
    }
    if(!m10v_library_valid(&state))return -1;
    uint32_t gw=image.width,gh=image.height,shift=0;
    while(gw>384||gh>256){shift++;uint32_t mask=(1u<<shift)-1;gw=(image.width+mask)>>shift;gh=(image.height+mask)>>shift;}
    uint32_t film=state.slots[slot].film;
    uint32_t required=((film==33||film==67)&&state.slots[slot].halo_gain)?6*gw*gh:0;
    uint32_t bytes=required+65536u;uint8_t *scratch=gr2_allocate(bytes);
    if(!scratch){bytes=required;if(required)scratch=gr2_allocate(required);}
    if(required&&!scratch)return -2;
    m10v_library_date date;uint16_t fields[6];const m10v_library_date *stamp=0;
    if(state.stamp){
        if(gr2_read_clock(fields)){date.year=fields[0];date.month=(uint8_t)fields[1];date.day=(uint8_t)fields[2];date.hour=(uint8_t)fields[3];date.minute=(uint8_t)fields[4];stamp=&date;}
        else {state.stamp=0;state.crc=m10v_sd_crc((const uint8_t *)&state,100);}
    }
    int result=gr2_render_planar(&image,&state,slot,stamp,seed,scratch,bytes);
    if(!gr2_cache_after())result=-3;
    gr2_release(scratch);return result;
}

int gr2_capture_process(const uint8_t *context,uint32_t kind,const uint8_t *request,
                        const m10v_library_state *state,uint32_t slot){
    return process(context,kind,request,state,slot,0);
}
int gr2_capture_frozen(const uint8_t *context,uint32_t kind,const uint8_t *request){
    return process(context,kind,request,0,0,1);
}
