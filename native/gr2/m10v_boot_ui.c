#include "m10v_boot.h"
#include "m10v_configuration.h"
#include "m10v_effect_names.h"
#include "m10v_settings_page.h"
#include "m10v_storage.h"
#define WORD(address) (*(volatile uint32_t *)(uintptr_t)(address))
#define HALF(address) (*(volatile uint16_t *)(uintptr_t)(address))
#define BYTE(address) (*(volatile uint8_t *)(uintptr_t)(address))
/* A snapshot only: actual SDK operations still check media change/readiness.
 * Never initialize the filesystem, mount media, allocate or do I/O here. */
int gr2_ui_storage_ready(void){
    const uint32_t control=0xA00C2C6Cu,volume=0xA06AA6A0u,heads=0xA05FA9CCu;
    if(!gr2_native_ready()||gr2_startup_complete!=1u||WORD(0xA061EAD0u)!=1u||
       WORD(control+0x20)||WORD(control+0x24)||!WORD(control+8)||
       (WORD(volume+0x61A8)&3u)!=3u||BYTE(volume+0x61AC)!='H')return 0;
    uint32_t pool=WORD(control+0x1C),max=HALF(0xA00B5BFEu);
    if(!max||pool<heads+28u||pool>heads+28u*max||(pool-heads)%28u)return 0;
    uint32_t id=(pool-heads)/28u;
    return WORD(pool)==0x4D504C20u&&!BYTE(pool+4)&&HALF(pool+0x14)==id;
}
/* 0 waits for live services; 1 is a reentrancy guard; 2 requires an explicit
 * MENU/OK or ADJ retry; 3 has published the owned configuration and labels.
 * Called by the existing UI event owner, never startup/capture workers. */
volatile uint32_t gr2_ui_boot_state;
int gr2_ui_bootstrap(const uint32_t *message){
    if(gr2_ui_boot_state==3u)return 1;
    if(!message||((uintptr_t)message&3u)||gr2_ui_boot_state==1u)return 0;
    if(gr2_ui_boot_state==2u&&message[0]!=0x6000100Au&&message[0]!=0x60001016u)return 0;
    if(!gr2_ui_storage_ready())return 0;
    gr2_ui_boot_state=1;
    int ready=gr2_initialize_state()&&gr2_configuration_reload();
    if(ready){
        ready=gr2_menu_entries_enable(1);
        if(ready&&!gr2_effect_names_refresh()){
            gr2_menu_entries_enable(0);ready=0;
        }
    }
    gr2_ui_boot_state=ready?3u:2u;
    return ready;
}
