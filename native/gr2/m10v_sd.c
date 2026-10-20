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
