#include "m10v_hdf_configuration.h"
#include "m10v_hdf.h"
#include "m10v_configuration.h"
extern uint32_t gr2_clone_policy_original(uint8_t *);
/* Exact original E040 scheduling arms. E1F2 evaluates the parent but later
 * enqueues both the already-created sibling and parent; E25A has no sibling.
 * Freeze the complete main family before deciding on its auxiliary clone. */
uint32_t gr2_hdf_clone_policy(uint8_t *parent,uint8_t *sibling,uint32_t caller){
 if(caller==0xA029E1F7u){
  if(!sibling)return gr2_clone_policy_original(parent);
 }else if(caller!=0xA029E25Fu||sibling)return gr2_clone_policy_original(parent);
 if(!gr2_hdf_configuration_policy(parent,sibling))return gr2_clone_policy_original(parent);
 /* The five owned film modes finish in the JPEG renderer. An auxiliary
  * RAW clone made here predates their producer snapshot; use the original
  * postprocessed-image thumbnail path, as for native postprocess effects. */
 if(gr2_configuration_is_carrier(parent[0x408])||
    (sibling&&gr2_configuration_is_carrier(sibling[0x408])))return 0;
 gr2_hdf_frame frame;
 if(gr2_hdf_frame_read(parent,&frame)&&(frame.control&3u))return 0;
 return gr2_clone_policy_original(parent);
}
