#include "m10v_storage.h"
#include "m10v_model.h"
typedef uint32_t (*open_fn)(const char *,uint32_t);
typedef int32_t (*transfer_fn)(uint32_t,void *,uint32_t);
static int same(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int custom_snapshot(const char *path){
    const char prefix[]="H:/M10VC";
    for(uint32_t i=0;i<8;i++)if(path[i]!=prefix[i])return 0;
    return path[8]>='0'&&path[8]<='4'&&path[9]>='0'&&path[9]<='1'&&same(path+10,".bin");
}
static int owned(const char *path,int writing){
    if(!path)return 0;
    if(same(path,"H:/M10V5A.bin")||same(path,"H:/M10V5B.bin")||
       same(path,"H:/M10VHD0.BIN")||same(path,"H:/M10VHD1.BIN")||custom_snapshot(path))return 1;
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
int32_t gr2_file_read_at(const char *path,uint32_t offset,uint8_t *out,uint32_t capacity){
    if(!owned(path,0)||!out||!capacity||capacity>0x1000000u||offset>0x7fffffffu||capacity>0x7fffffffu-offset)return -1;
    uint32_t handle=((open_fn)(uintptr_t)0xA002C70Fu)(path,0);if(!handle)return -1;
    typedef int32_t (*seek_fn)(uint32_t,int32_t,uint32_t);
    int32_t read=-1;
    if(((seek_fn)(uintptr_t)0xA002E491u)(handle,(int32_t)offset,0)==0)
        read=((transfer_fn)(uintptr_t)0xA002CA99u)(handle,out,capacity);
    int closed=close_owned(handle);return closed?read:-1;
}
int gr2_file_size(const char *path,uint32_t *out){
    if(!owned(path,0)||!out)return 0;
    uint32_t handle=((open_fn)(uintptr_t)0xA002C70Fu)(path,0);if(!handle)return 0;
    typedef int32_t (*seek_fn)(uint32_t,int32_t,uint32_t);
    typedef int32_t (*tell_fn)(uint32_t,uint32_t *);
    uint32_t position[2]={0,0};int valid=0;
    if(((seek_fn)(uintptr_t)0xA002E491u)(handle,0,2)==0&&
       ((tell_fn)(uintptr_t)0xA002E39Fu)(handle,position)==0&&position[0]==0)valid=1;
    if(!close_owned(handle))valid=0;
    if(valid)*out=position[1];
    return valid;
}

/* UI owner only. A failed fopen is not an absence proof: exact root-name
 * find-first runs the original mounted-volume/character/FAT search. Stock
 * FindClose frees its cursor and metadata without a separate SDK close. */
static int journals_absent(const char *const paths[2]){
    uint8_t *cursor=gr2_allocate(4096);if(!cursor)return -1;
    int result=1;
    typedef int32_t (*first_fn)(const char *,uint32_t,void *);
    typedef int32_t (*error_fn)(void);
    for(uint32_t i=0;i<2;i++){
        if(((first_fn)(uintptr_t)0xA00653BDu)(paths[i],0x77,cursor)==0){result=0;break;}
        if(((error_fn)(uintptr_t)0xA00652CFu)()!=3){result=-1;break;}
    }
    gr2_release(cursor);return result;
}

int gr2_journals_absent(void){
    const char *const paths[2]={"H:/M10V5A.bin","H:/M10V5B.bin"};return journals_absent(paths);
}
int gr2_hdf_journals_absent(void){
    const char *const paths[2]={"H:/M10VHD0.BIN","H:/M10VHD1.BIN"};return journals_absent(paths);
}

/* Bootstrap may create one initial journal only after both exact root names
 * were enumerated absent. Corrupt, unreadable or pre-existing journals never
 * become permission to reset. The existing verified journal path does all
 * serialization, readback and arbitration. Never call from capture tasks. */
int gr2_initialize_state(void){
    m10v_library_state state;
    if(gr2_load_state(&state))return 1;
    if(gr2_journals_absent()!=1)return 0;
    m10v_library_init(&state);
    return m10v_library_valid(&state)&&gr2_save_state(&state);
}
