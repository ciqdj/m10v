#include "m10v_effect_names.h"
#include "m10v_configuration.h"
#include "m10v_effect_names_contract.h"
static uint16_t names[5][96];
static uint32_t enabled;
static volatile uint32_t *cell(uint32_t language,uint32_t index){return (volatile uint32_t *)(uintptr_t)(gr2_text_rows[language]+4*(gr2_name_ids[index]-1));}
static int admissible(void){
    if(*(const volatile uint32_t *)(uintptr_t)GR2_TEXT_DIRECTORY_WORD!=GR2_TEXT_DIRECTORY)return 0;
    const volatile uint32_t *directory=(const volatile uint32_t *)(uintptr_t)GR2_TEXT_DIRECTORY;
    for(uint32_t language=0;language<21;language++){
        if(directory[language]!=gr2_text_rows[language])return 0;
        for(uint32_t index=0;index<7;index++){
            uint32_t actual=*cell(language,index),own=(uint32_t)(uintptr_t)names[gr2_name_slots[index]];
            if(actual!=gr2_name_preimages[language][index]&&(!enabled||actual!=own))return 0;
        }
    }
    return 1;
}
int gr2_effect_names_refresh(void){
    if(!admissible())return 0;
    uint16_t (*next)[96]=gr2_allocate(5*96*2);if(!next)return 0;
    if(!gr2_configuration_names(next)){gr2_release(next);return 0;}
    for(uint32_t slot=0;slot<5;slot++)for(uint32_t i=0;i<96;i++)names[slot][i]=next[slot][i];
    for(uint32_t language=0;language<21;language++)for(uint32_t index=0;index<7;index++)
        *cell(language,index)=(uint32_t)(uintptr_t)names[gr2_name_slots[index]];
    enabled=1;gr2_release(next);return 1;
}
int gr2_effect_names_restore(void){
    if(!enabled||!admissible())return 0;
    for(uint32_t language=0;language<21;language++)for(uint32_t index=0;index<7;index++)*cell(language,index)=gr2_name_preimages[language][index];
    enabled=0;return 1;
}
int gr2_effect_names_enabled(void){return enabled!=0;}
