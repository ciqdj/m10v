#include "m10v_ui.h"
const uint16_t *gr2_original_text(uint32_t text_id,uint32_t language){
    /* The original accessor bounds the text id but directly indexes language.
     * This identity-locked firmware contains 21 original language tables. */
    if(language>=21)return 0;
    typedef const uint16_t *(*lookup)(uint32_t,uint32_t);
    return ((lookup)(uintptr_t)0xA03A4AD1u)(text_id,language);
}
