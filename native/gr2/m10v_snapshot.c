#include "m10v_storage.h"
#include "../../compat/gr2-v1/native/gr3/m10v_sd_library.h"
#define RECORD M10V_SD_RECORD_BYTES
static int disjoint(const void *a,uint32_t an,const void *b,uint32_t bn){
    uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    return av&&bv&&an<=UINTPTR_MAX-av&&bn<=UINTPTR_MAX-bv&&(av+an<=bv||bv+bn<=av);
}
static void path_name(uint32_t slot,uint32_t bank,char path[15]){
    const char base[]="H:/M10VC00.bin";
    for(uint32_t i=0;i<15;i++)path[i]=base[i];
    path[8]=(char)('0'+slot);path[9]=(char)('0'+bank);
}
static int inputs(const gr2_storage_io *io,const m10v_library_state *state,uint32_t slot,const uint8_t *record,uint8_t *work){
    return io&&!((uintptr_t)io&3)&&io->read&&state&&!((uintptr_t)state&3)&&slot<5&&m10v_library_valid(state)&&
           disjoint(work,RECORD+1,io,sizeof(*io))&&disjoint(work,RECORD+1,state,sizeof(*state))&&disjoint(work,RECORD+1,record,RECORD);
}
/* The selected bank and journal are never modified here. Caller publishes the
 * new bank only after this exact-size, validated, byte-for-byte readback. */
int gr2_custom_snapshot_store(const gr2_storage_io *io,const m10v_library_state *state,uint32_t slot,
                              const uint8_t *record,uint8_t *work,uint32_t *bank_out){
    if(!inputs(io,state,slot,record,work)||!io->write||!bank_out||((uintptr_t)bank_out&3)||
       !disjoint(bank_out,4,io,sizeof(*io))||!disjoint(bank_out,4,state,sizeof(*state))||
       !disjoint(bank_out,4,record,RECORD)||!disjoint(bank_out,4,work,RECORD+1))return 0;
    uint32_t id=m10v_sd_u32(record+8);
    if(id<=M10V_FILM_COUNT||id>M10V_CUSTOM_MAX_ID||m10v_sd_record(record,RECORD,id)!=id)return 0;
    uint32_t current=state->effects[slot].reserved[0],bank=current?2-current:0;
    char path[15];path_name(slot,bank,path);
    int same=io->read(path,work,RECORD+1)==RECORD;
    if(same)for(uint32_t i=0;i<RECORD;i++)if(work[i]!=record[i]){same=0;break;}
    if(!same){
        if(io->write(path,record,RECORD)!=RECORD||io->read(path,work,RECORD+1)!=RECORD||m10v_sd_record(work,RECORD,id)!=id)return 0;
        for(uint32_t i=0;i<RECORD;i++)if(work[i]!=record[i])return 0;
    }
    *bank_out=bank;return 1;
}
int gr2_custom_snapshot_read(const gr2_storage_io *io,const m10v_library_state *state,uint32_t slot,uint8_t *out,uint8_t *work){
    if(!inputs(io,state,slot,out,work)||!disjoint(out,RECORD,io,sizeof(*io))||!disjoint(out,RECORD,state,sizeof(*state)))return 0;
    uint32_t id=state->slots[slot].film,which=state->effects[slot].reserved[0];
    if(id<=M10V_FILM_COUNT||which<1||which>2)return 0;
    char path[15];path_name(slot,which-1,path);
    if(io->read(path,work,RECORD+1)!=RECORD||m10v_sd_record(work,RECORD,id)!=id)return 0;
    for(uint32_t i=0;i<RECORD;i++)out[i]=work[i];
    return 1;
}
