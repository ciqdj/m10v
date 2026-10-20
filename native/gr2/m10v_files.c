#include "m10v_storage.h"
typedef uint32_t (*open_fn)(const char *,uint32_t);
typedef int32_t (*transfer_fn)(uint32_t,void *,uint32_t);
static int same(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int owned(const char *path,int writing){
    if(!path)return 0;
    if(same(path,"H:/M10V5A.bin")||same(path,"H:/M10V5B.bin"))return 1;
    return !writing&&same(path,"H:/M10V/FILMS.M10");
}
static int close_owned(uint32_t handle){
    uint32_t *header=(uint32_t *)(uintptr_t)handle;
    if(!handle||header[0]!=0x46494C45u)return 0;
    /* Stock close discards fclose's status. Preserve it for private journals,
     * then perform the same FILE-magic invalidation and metadata-pool free. */
    int32_t status=((int32_t (*)(uint32_t))(uintptr_t)0xA00652E3u)(header[1]);
    header[0]=0;
    const uint32_t *control=(const uint32_t *)(uintptr_t)0xA00C2C6Cu;
    ((void (*)(uint32_t,uint32_t))(uintptr_t)0xA0024D77u)(control[7],handle);
    return status==0;
}
int32_t gr2_file_read(const char *path,uint8_t *out,uint32_t capacity){
    if(!owned(path,0)||!out||!capacity||capacity>0x1000000)return -1;
    uint32_t handle=((open_fn)(uintptr_t)0xA002C70Fu)(path,0);if(!handle)return -1;
    int32_t read=((transfer_fn)(uintptr_t)0xA002CA99u)(handle,out,capacity);
    int closed=close_owned(handle);return closed?read:-1;
}
int32_t gr2_file_write(const char *path,const uint8_t *bytes,uint32_t count){
    if(!owned(path,1)||!bytes||!count||count>0x1000000)return -1;
    uint32_t handle=((open_fn)(uintptr_t)0xA002C70Fu)(path,1);if(!handle)return -1;
    int32_t written=((transfer_fn)(uintptr_t)0xA002CC4Bu)(handle,(void *)bytes,count);
    int closed=close_owned(handle);return closed&&written==(int32_t)count?written:-1;
}
static const gr2_storage_io io={gr2_file_read,gr2_file_write};
int gr2_load_state(m10v_library_state *state){return gr2_journal_load(&io,state);}
int gr2_save_state(const m10v_library_state *state){return gr2_journal_store(&io,state);}
