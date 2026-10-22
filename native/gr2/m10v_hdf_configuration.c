#include "m10v_hdf_configuration.h"
#include "m10v_hdf.h"
#include "m10v_hdf_layout.h"
#include "m10v_capture.h"
static struct {uint32_t magic,strength,sequence;} cache;
static int32_t mutex_id;
static volatile uint32_t needs_bank0;
static int lock(void){return mutex_id>0&&((int32_t (*)(int32_t,int32_t))(uintptr_t)0xA0066D94u)(mutex_id,0)==0;}
static void unlock(void){((int32_t (*)(int32_t))(uintptr_t)0xA00671B8u)(mutex_id);}
static int create(void){
 if(mutex_id>0)return 1;
 const struct {uint16_t attribute,ceiling;uint32_t reserved;} descriptor={2,0,0};
 int32_t id=((int32_t (*)(const void *))(uintptr_t)0xA00665CCu)(&descriptor);
 if(id<=0)return 0;
 mutex_id=id;return 1;
}
static int disjoint(uintptr_t a,uint32_t an,uintptr_t b,uint32_t bn){return a+an<=b||b+bn<=a;}
static int output(const uint32_t *pointer){
 uintptr_t a=(uintptr_t)pointer;
 return a&&!(a&3u)&&a<=UINT32_MAX-4u&&disjoint(a,4,(uintptr_t)&cache,sizeof(cache))&&disjoint(a,4,(uintptr_t)&mutex_id,4);
}
int gr2_hdf_configuration_publish(uint32_t strength,uint32_t sequence){
 if(strength>3u||(strength&&!gr2_hdf_layout_supports_graph())||!create()||!lock())return 0;
 cache.strength=strength;cache.sequence=sequence;cache.magic=0x47324843u;needs_bank0=strength!=0;unlock();return 1;
}
int gr2_hdf_configuration_read(uint32_t *strength,uint32_t *sequence){
 if(!output(strength)||!output(sequence)||!disjoint((uintptr_t)strength,4,(uintptr_t)sequence,4)||!lock())return 0;
 int ok=cache.magic==0x47324843u&&cache.strength<=3u;
 if(ok){*strength=cache.strength;*sequence=cache.sequence;}
 unlock();return ok;
}
int gr2_hdf_configuration_freeze(uint8_t *context){
 if(gr2_image_owner_bytes(context)!=GR2_IMAGE_BODY_BYTES)return 0;
 gr2_hdf_frame existing;
 if(gr2_hdf_frame_read(context,&existing))return 1;
 uint32_t strength,sequence;
 if(!gr2_hdf_configuration_read(&strength,&sequence)||
    (strength&&!gr2_hdf_layout_supports_graph()))return 0;
 return gr2_hdf_frame_freeze(context,strength,sequence);
}
/* Preparation seals the recipe under the original stage6 mutex, before
 * JPEG reservations. Cache failure seals off against later publication. */
int gr2_hdf_configuration_begin(uint8_t *context){
 if(gr2_image_owner_bytes(context)!=GR2_IMAGE_BODY_BYTES)return 0;
 uint32_t strength=0,sequence=0;
 int ready=gr2_hdf_configuration_read(&strength,&sequence)&&(!strength||gr2_hdf_layout_supports_graph());
 for(uint32_t i=0;i<16u;i++)((volatile uint8_t *)context)[GR2_HDF_FRAME_OFFSET+i]=0;
 int sealed=gr2_hdf_frame_freeze(context,ready?strength:0,ready?sequence:0);
 return ready&&sealed;
}
int gr2_hdf_configuration_clear(void){
 if(mutex_id<=0)return 1;
 if(!lock())return 0;
 cache.magic=0;cache.strength=0;cache.sequence=0;needs_bank0=0;unlock();return 1;
}

/* Conservative pool hint only; never used as the per-frame setting value. */
uint32_t gr2_hdf_configuration_needs_bank0(void){return needs_bank0!=0;}

int gr2_hdf_reservation_required(uint8_t *context){
 gr2_hdf_frame frame;
 return gr2_hdf_frame_read(context,&frame)&&(frame.control&3u)&&gr2_hdf_layout_supports_graph();
}
