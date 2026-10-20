#include "m10v_ui.h"
const uint16_t *gr2_original_text(uint32_t text_id,uint32_t language){
    /* The original accessor bounds the text id but directly indexes language.
     * This identity-locked firmware contains 21 original language tables. */
    if(language>=21)return 0;
    typedef const uint16_t *(*lookup)(uint32_t,uint32_t);
    return ((lookup)(uintptr_t)0xA03A4AD1u)(text_id,language);
}
/* SYS_CREATE initializes embedded widgets in fresh detached storage. It does
 * not allocate/register a screen, enter the UI stack or draw anything. */
int gr2_effect_view_init(void *storage,uint32_t capacity){
    if(!storage||((uintptr_t)storage&3)||capacity<0x600u||(uintptr_t)storage>UINTPTR_MAX-0x600u)return 0;
    uint8_t *root=(uint8_t *)storage;
    for(uint32_t i=0;i<0x600u;i++)root[i]=0;
    const uint8_t *configuration=(const uint8_t *)(uintptr_t)0xA0411A18u;
    for(uint32_t i=0;i<64;i++)root[i]=configuration[i];
    const uint32_t event[3]={0x60000000u,0,0};
    typedef int (*event_fn)(void *,const uint32_t *);
    return ((event_fn)(uintptr_t)0xA03AD0C7u)(root,event);
}
