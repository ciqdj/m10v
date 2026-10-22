#include "m10v_hdf_layout.h"
#include "m10v_hdf_configuration.h"
#include "m10v_boot.h"
static volatile uint32_t preparing;
extern uint32_t gr2_buffer_layout_original(uint32_t,uint32_t,uint32_t,uint32_t);
uint32_t gr2_hdf_buffer_layout(uint32_t mode,uint32_t drive,uint32_t auxiliary,uint32_t variant){
 uint32_t selected=gr2_buffer_layout_original(mode,drive,auxiliary,variant);
 /* Only the original still-mode decision1 needs its additional JPEG block.
  * This is a pure decision: stock manager/preflight retain busy admission. */
 if(selected==1u&&(mode==6u||mode==7u)&&(preparing||gr2_hdf_configuration_needs_bank0()))return 0;
 return selected;
}

int gr2_hdf_layout_supports_graph(void){
 uint32_t bank=*(const volatile uint8_t *)(uintptr_t)0xA0129C20u;
 const uint8_t *definition=(const uint8_t *)(uintptr_t)(0xA0112048u+23u*44u);
 if(bank>4u||definition[0]!=0x17u||*(const uint32_t *)(definition+4)!=0x1f0e020u)return 0;
 uint32_t count=*(const uint32_t *)(definition+20u+4u*bank);
 return count>=2u&&count<=3u;
}

int gr2_hdf_prepare_pool(uint32_t strength){
 if(strength>3u||preparing||!gr2_ui_storage_ready())return 0;
 /* Off never releases a bank before the old effective setting is replaced. */
 if(!strength||gr2_hdf_layout_supports_graph())return 1;
 preparing=1;
 ((void (*)(void))(uintptr_t)0xA00E4095u)();
 preparing=0;
 return gr2_hdf_layout_supports_graph();
}
