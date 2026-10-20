#include "m10v_sd.h"
#include "m10v_model.h"
#include "m10v_storage.h"
#include "../gr3/m10v_sd_library.h"
static const char path[]="H:/M10V/FILMS.M10";
uint32_t gr2_pack_fetch(const gr2_pack_io *io,uint32_t index,uint32_t expected,uint8_t *memory,uint32_t full){
    if(!io||!io->size||!io->read_at||!memory||index>=M10V_SD_MAX_FILMS||full>1||
       (expected&&(expected<33||expected>M10V_CUSTOM_MAX_ID))||(full&&!expected))return 0;
    uint32_t size=0;
    if(!io->size(path,&size)||size<M10V_SD_HEADER_BYTES||size>M10V_SD_HEADER_BYTES+M10V_SD_MAX_FILMS*M10V_SD_RECORD_BYTES||
       io->read_at(path,0,memory,M10V_SD_HEADER_BYTES)!=M10V_SD_HEADER_BYTES)return 0;
    uint32_t count=m10v_sd_header(memory,size);
    if(!count||index>=count)return 0;
    uint32_t id=m10v_sd_u32(memory+64+index*12);
    if(expected&&id!=expected)return 0;
    if(full){
        uint32_t crc=m10v_sd_u32(memory+68+index*12);uint8_t *record=memory+M10V_SD_HEADER_BYTES;
        if(io->read_at(path,M10V_SD_HEADER_BYTES+index*M10V_SD_RECORD_BYTES,record,M10V_SD_RECORD_BYTES)!=M10V_SD_RECORD_BYTES||
           m10v_sd_u32(record+M10V_SD_RECORD_BYTES-4)!=crc||m10v_sd_record(record,M10V_SD_RECORD_BYTES,id)!=id)return 0;
    }
    return id;
}
static const gr2_pack_io io={gr2_file_size,gr2_file_read_at};
uint32_t gr2_sd_item(uint32_t index){
    if(index>=M10V_SD_MAX_FILMS)return 0;
    uint8_t *memory=gr2_allocate(M10V_SD_HEADER_BYTES);if(!memory)return 0;
    uint32_t id=gr2_pack_fetch(&io,index,0,memory,0);
    if(gr2_release(memory))return 0;
    return id;
}
uint32_t gr2_sd_record(uint32_t index,uint32_t expected,uint8_t *out,uint32_t capacity){
    if(!out||capacity<M10V_SD_RECORD_BYTES||index>=M10V_SD_MAX_FILMS||expected<33||expected>M10V_CUSTOM_MAX_ID)return 0;
    uint8_t *memory=gr2_allocate(M10V_SD_HEADER_BYTES+M10V_SD_RECORD_BYTES);if(!memory)return 0;
    uint32_t id=gr2_pack_fetch(&io,index,expected,memory,1);
    if(id)for(uint32_t i=0;i<M10V_SD_RECORD_BYTES;i++)out[i]=memory[M10V_SD_HEADER_BYTES+i];
    if(gr2_release(memory))return 0;
    return id;
}
int gr2_sd_catalog_name(uint32_t index,uint32_t expected,char *out,uint32_t capacity){
    if(!out||!capacity||index>=M10V_SD_MAX_FILMS||expected<33||expected>M10V_CUSTOM_MAX_ID)return 0;
    uint8_t *memory=gr2_allocate(M10V_SD_HEADER_BYTES+M10V_SD_RECORD_BYTES);if(!memory)return 0;
    uint32_t id=gr2_pack_fetch(&io,index,expected,memory,1),length=0;int valid=0;
    const uint8_t *name=memory+M10V_SD_HEADER_BYTES+16;
    if(id){
        while(length<24&&name[length])length++;
        if(length&&length<24&&capacity>length){for(uint32_t i=0;i<=length;i++)out[i]=(char)name[i];valid=1;}
    }
    if(gr2_release(memory))return 0;
    return valid;
}
_Static_assert(sizeof(gr2_pack_manifest)==4108,"GR II catalog manifest ABI");
#define GR2_MANIFEST_MAGIC 0x4752324du
static int disjoint(const void *a,uint32_t an,const void *b,uint32_t bn){
    uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    return av&&bv&&an<=UINTPTR_MAX-av&&bn<=UINTPTR_MAX-bv&&(av+an<=bv||bv+bn<=av);
}
int gr2_pack_manifest_load(const gr2_pack_io *io,gr2_pack_manifest *out,uint8_t *memory){
    if(!io||!io->size||!io->read_at||!out||((uintptr_t)out&3)||
       !disjoint(out,sizeof(*out),memory,4096)||!disjoint(io,sizeof(*io),memory,4096)||!disjoint(io,sizeof(*io),out,sizeof(*out)))return 0;
    uint32_t size=0;
    if(!io->size(path,&size)||size<4096||size>4096+M10V_SD_MAX_FILMS*M10V_SD_RECORD_BYTES||io->read_at(path,0,memory,4096)!=4096)return 0;
    uint32_t count=m10v_sd_header(memory,size);if(!count)return 0;
    for(uint32_t i=0;i<4096;i++)out->header[i]=memory[i];
    out->size=size;out->count=count;out->magic=GR2_MANIFEST_MAGIC;
    return 1;
}
int32_t gr2_pack_fetch_frozen(const gr2_pack_io *io,const gr2_pack_manifest *manifest,uint32_t index,uint32_t expected,uint8_t *memory){
    if(!io||!io->size||!io->read_at||!manifest||((uintptr_t)manifest&3)||
       !disjoint(manifest,sizeof(*manifest),memory,4096+M10V_SD_RECORD_BYTES)||!disjoint(io,sizeof(*io),memory,4096+M10V_SD_RECORD_BYTES)||
       manifest->magic!=GR2_MANIFEST_MAGIC||!manifest->count||m10v_sd_header(manifest->header,manifest->size)!=manifest->count||
       index>=manifest->count||expected<33||expected>M10V_CUSTOM_MAX_ID||m10v_sd_u32(manifest->header+64+12*index)!=expected)return GR2_PACK_INVALID;
    uint32_t size=0;if(!io->size(path,&size))return GR2_PACK_IO_ERROR;
    if(size!=manifest->size)return GR2_PACK_CHANGED;
    if(io->read_at(path,0,memory,4096)!=4096)return GR2_PACK_IO_ERROR;
    for(uint32_t i=0;i<4096;i++)if(memory[i]!=manifest->header[i])return GR2_PACK_CHANGED;
    uint8_t *record=memory+4096;
    if(io->read_at(path,4096+index*M10V_SD_RECORD_BYTES,record,M10V_SD_RECORD_BYTES)!=M10V_SD_RECORD_BYTES)return GR2_PACK_IO_ERROR;
    if(m10v_sd_u32(record+M10V_SD_RECORD_BYTES-4)!=m10v_sd_u32(manifest->header+68+12*index)||
       m10v_sd_record(record,M10V_SD_RECORD_BYTES,expected)!=expected)return GR2_PACK_INVALID;
    return (int32_t)expected;
}

int gr2_sd_catalog_open(gr2_pack_manifest *manifest){
    if(!manifest||((uintptr_t)manifest&3))return 0;
    uint8_t *work=gr2_allocate(4096);if(!work)return 0;
    int result=gr2_pack_manifest_load(&io,manifest,work);
    if(gr2_release(work))return 0;
    return result;
}
uint32_t gr2_sd_frozen_record(const gr2_pack_manifest *manifest,uint32_t index,uint32_t expected,uint8_t *out,uint32_t capacity){
    if(!manifest||!out||capacity<M10V_SD_RECORD_BYTES||
       !disjoint(out,M10V_SD_RECORD_BYTES,manifest,sizeof(*manifest)))return 0;
    uint8_t *work=gr2_allocate(4096+M10V_SD_RECORD_BYTES);if(!work)return 0;
    int32_t result=gr2_pack_fetch_frozen(&io,manifest,index,expected,work);
    if(result>0)for(uint32_t i=0;i<M10V_SD_RECORD_BYTES;i++)out[i]=work[4096+i];
    if(gr2_release(work))return 0;
    return result>0?(uint32_t)result:0;
}
