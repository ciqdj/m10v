#include "m10v_hdf_control.h"
#include "m10v_hdf_configuration.h"
#include "m10v_hdf_storage.h"
#include "m10v_hdf_layout.h"
#include "m10v_boot.h"
#include "m10v_settings_page.h"
int gr2_hdf_reload(void){
 uint32_t strength,sequence;
 if(gr2_ui_storage_ready()&&gr2_hdf_initialize_state()&&
    gr2_hdf_load_state(&strength,&sequence)&&gr2_hdf_prepare_pool(strength)&&
    gr2_hdf_configuration_publish(strength,sequence))return 1;
 /* An unreadable journal or failed admission is not a new effective value.
  * Already queued images retain their immutable snapshots. */
 gr2_hdf_configuration_clear();return 0;
}
int gr2_hdf_update(uint32_t strength){
 if(strength>3u||!gr2_ui_storage_ready())return 0;
 if(!gr2_hdf_initialize_state()){
  gr2_hdf_configuration_clear();return 0;
 }
 /* Original busy admission precedes persistence; do not save a grade that
  * the current pool cannot execute. Off does not rebuild/release the bank. */
 if(!gr2_hdf_prepare_pool(strength))return 0;
 int saved=gr2_hdf_save_state(strength);
 /* Close/verification failure can still leave a newer valid bank. Reload
  * even on failure so UI and future captures share the same actual value. */
 if(!gr2_hdf_reload())return 0;
 uint32_t actual,sequence;
 return saved&&gr2_hdf_configuration_read(&actual,&sequence)&&actual==strength;
}

/* Independent UI restoration never disables film/stamp settings. Wait for
 * original capture busy admission before touching the HDF journal; after an
 * I/O/admission failure only MENU/OK or ADJ retries, not every display tick. */
volatile uint32_t gr2_hdf_ui_boot_state;
int gr2_hdf_ui_bootstrap(const uint32_t *message){
 if(gr2_hdf_ui_boot_state==3u)return 1;
 if(!message||((uintptr_t)message&3u)||gr2_hdf_ui_boot_state==1u)return 0;
 if(gr2_hdf_ui_boot_state==2u&&message[0]!=0x6000100au&&message[0]!=0x60001016u)return 0;
 if(!gr2_ui_storage_ready()||!gr2_menu_hdf_enable(1))return 0;
 if(((uint32_t (*)(uint32_t))(uintptr_t)0xA00E0E2Fu)(0x344u))return 0;
 gr2_hdf_ui_boot_state=1;
 int ready=gr2_hdf_reload();gr2_hdf_ui_boot_state=ready?3u:2u;return ready;
}
