/* Exact GR IV 1.04 original filesystem ABI. Only called from explicit menu
 * actions; no handles, buffers or SD dependencies survive into capture.
 * Read is BOOLEAN even on short reads: seek/tell deltas are mandatory. */
#include "m10v_sd_library.h"
#include "m10v_library.h"
typedef uint32_t (*get_fn)(void);
typedef void *(*alloc_fn)(uint32_t);
typedef void (*free_fn)(void *);
typedef int (*open_fn)(uint32_t,const char *,uint32_t,uint32_t *,uint32_t *);
typedef int (*io_fn)(uint32_t,uint32_t,void *,uint32_t,uint32_t *);
typedef int (*seek_fn)(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t *);
typedef int (*tell_fn)(uint32_t,uint32_t,uint32_t *,uint32_t *);
typedef int (*size_fn)(uint32_t,uint32_t,uint32_t *,uint32_t *);
typedef int (*close_fn)(uint32_t,uint32_t,uint32_t *);
static const char path[]="C:\\M10V\\FILMS.M10";
static int ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
static int code(uint32_t p,uint32_t n){return !(p&3)&&p>=0x53000000u&&p<0x543d2ac0u&&n<=0x543d2ac0u-p;}
static int exact(uint32_t fs,const uint32_t *v,uint32_t handle,uint32_t at,uint8_t *out,uint32_t n){
 uint32_t error=0,position=0;
 if(!((seek_fn)v[11])(fs,handle,at,0,&error)||error)return 0;
 if(!((tell_fn)v[13])(fs,handle,&position,&error)||error||position!=at)return 0;
 if(!((io_fn)v[9])(fs,handle,out,n,&error)||error)return 0;
 return ((tell_fn)v[13])(fs,handle,&position,&error)&&!error&&position==at+n;
}
/* Return selected ID after closing the file, with the complete record in out
 * when requested. Fixed 16 KiB scratch; header bounds all index arithmetic. */
static uint32_t fetch(uint32_t page,uint32_t row,uint8_t *memory,int full){
 if(page>=32||row>=8||!memory)return 0;
 uint32_t manager=((get_fn)0x53798938u)();if(!ram(manager,24))return 0;
 uint32_t fs=((const uint32_t *)(uintptr_t)manager)[5];if(!ram(fs,4))return 0;
 uint32_t vt=*(const uint32_t *)(uintptr_t)fs;if(!code(vt,56))return 0;
 const uint32_t *v=(const uint32_t *)(uintptr_t)vt;
 for(uint32_t i=7;i<=13;++i)if(i!=10&&!code(v[i],4))return 0;
 uint32_t size=0,error=0,handle=0,id=0;
 int opened=((open_fn)v[7])(fs,path,1,&handle,&error);
 if(!handle)return 0;
 /* v[12] queries an OPEN HANDLE: v[21] reads handle[1] as the device
  * index. Passing a path here turns ASCII into an out-of-bounds index. */
 if(opened&&!error&&((size_fn)v[12])(fs,handle,&size,&error)&&!error&&
    size>=4096&&size<=4096+M10V_SD_MAX_FILMS*M10V_SD_RECORD_BYTES&&
    exact(fs,v,handle,0,memory,4096)){
  uint32_t count=m10v_sd_header(memory,size),index=page*8+row;
  if(count&&index<count){
   id=m10v_sd_u32(memory+64+index*12);
   if(full){uint32_t expected=m10v_sd_u32(memory+68+index*12);uint8_t *record=memory+4096;
    if(!exact(fs,v,handle,4096+index*M10V_SD_RECORD_BYTES,record,M10V_SD_RECORD_BYTES)||
       m10v_sd_u32(record+M10V_SD_RECORD_BYTES-4)!=expected||!m10v_sd_record(record,M10V_SD_RECORD_BYTES,id))id=0;
   }
  }
 }
 error=0;if(!((close_fn)v[8])(fs,handle,&error)||error)id=0;
 return id;
}
static uint8_t *allocate(void){void *p=((alloc_fn)0x538e09b0u)(4096+M10V_SD_RECORD_BYTES);return ram((uint32_t)(uintptr_t)p,4096+M10V_SD_RECORD_BYTES)?p:0;}
uint32_t m10v_sd_camera_item(uint32_t page,uint32_t row){
 if(page>=32||row>=8)return 0;
 uint8_t *memory=allocate();if(!memory)return 0;
 uint32_t id=fetch(page,row,memory,0);((free_fn)0x538e09ecu)(memory);return id;
}
/* The stock AppData reader blindly copies the requested size. Instead use its
 * original file loader and header validator and check BOTH sizes before copy.
 * A failed snapshot can never invalidate the old ROM-backed slot identity. */
static int snapshot_read(uint32_t fs,const char *path_name,const uint8_t *expected){
 typedef void (*load_fn)(uint32_t,const char *,uint32_t *,uint32_t *);
 typedef int (*check_fn)(uint32_t,uint32_t,uint32_t,uint32_t *,uint32_t *);
 typedef void (*release_fn)(uint32_t,uint32_t);
 typedef uint32_t (*stat_fn)(uint32_t,const char *,void *);
 uint32_t file_manager=((const uint32_t *)(uintptr_t)fs)[11];
 if(!ram(file_manager,4))return 0;
 if(((stat_fn)0x5383b154u)(file_manager,path_name,0)!=M10V_SD_RECORD_BYTES+8)return 0;
 uint32_t n=0,raw=0;((load_fn)0x5383b288u)(file_manager,path_name,&raw,&n);
 if(!raw)return 0;
 int ok=0;uint32_t bytes=0,content=0;
 if(n==M10V_SD_RECORD_BYTES+8&&ram(raw,n)&&
    ((check_fn)0x53a7ee80u)(fs,n,raw,&bytes,&content)&&bytes==M10V_SD_RECORD_BYTES&&ram(content,bytes)&&content==raw+8){
  const uint8_t *p=(const uint8_t *)(uintptr_t)content;ok=1;
  for(uint32_t i=0;i<bytes;++i)if(p[i]!=expected[i]){ok=0;break;}
 }
 ((release_fn)0x53838afcu)(file_manager,raw);return ok;
}
static int persist(const uint8_t *record,uint32_t id){
 uint32_t manager=((get_fn)0x53a81480u)();if(!ram(manager,12))return 0;
 uint32_t app=((const uint32_t *)(uintptr_t)manager)[2];if(!ram(app,8))return 0;
 uint32_t fs=((const uint32_t *)(uintptr_t)app)[1];if(!ram(fs,0x50)||!((const uint8_t *)(uintptr_t)fs)[0x4c])return 0;
 char name[]="M10VS00.bin",primary[]="F:\\M10VS00.bin";
 name[5]=primary[8]=(char)('0'+id/10);name[6]=primary[9]=(char)('0'+id%10);
 if(snapshot_read(fs,primary,record))return 1;
 typedef int (*write_fn)(uint32_t,const char *,uint32_t,const void *);
 return ((write_fn)0x53a7fb1cu)(fs,name,M10V_SD_RECORD_BYTES,record)&&snapshot_read(fs,primary,record);
}
int m10v_sd_camera_install(uint32_t page,uint32_t row,uint32_t expected_id,uint32_t slot){
 if(page>=32||row>=8||expected_id<33||expected_id>M10V_FILM_COUNT||slot>=5)return -1;
 uint8_t *memory=allocate();if(!memory)return -1;
 int result=-1;uint32_t id=fetch(page,row,memory,1);
 if(id==expected_id){
  m10v_library_state state;
  if(m10v_camera_library_load(&state)>=0&&persist(memory+4096,id))result=m10v_camera_library_select(&state,slot,id);
 }
 ((free_fn)0x538e09ecu)(memory);return result;
}
