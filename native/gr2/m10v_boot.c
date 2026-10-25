#include "m10v_boot.h"
#include "m10v_model.h"
#include "m10v_hdf.h"
#define WORD(address) (*(volatile uint32_t *)(uintptr_t)(address))
#define BYTE(address) (*(volatile uint8_t *)(uintptr_t)(address))
#define HALF(address) (*(volatile uint16_t *)(uintptr_t)(address))
volatile uint32_t gr2_activation_ready;
volatile uint32_t gr2_startup_complete;
extern void gr2_finalize_chain(void);
extern void gr2_hdf_layout_chain(void),gr2_hdf_core_chain(void),gr2_hdf_band_chain(void),gr2_hdf_postprocess_chain(void),gr2_hdf_production_chain(void);
extern void gr2_hdf_preparation_chain(void),gr2_hdf_reservation_chain(void),gr2_hdf_policy_chain(void);
extern void gr2_startup_chain(void),gr2_producer_chain(void),gr2_jpeg_chain(void);
extern void gr2_ui_event_chain(void),gr2_menu_route_chain(void),gr2_menu_descriptor_chain(void);
extern uint32_t *gr2_menu_categories(uint32_t);
extern void gr2_cache_svc_entry(void);
typedef struct {uint32_t address;uintptr_t target;} hook;
static const hook hooks[]={
    {0xA0020AB4u,(uintptr_t)gr2_startup_chain},
    {0xA02AD48Cu,(uintptr_t)gr2_producer_chain},
    {0xA02ADC98u,(uintptr_t)gr2_jpeg_chain},
    {0xA0394950u,(uintptr_t)gr2_ui_event_chain},
    {0xA03948C4u,(uintptr_t)gr2_menu_route_chain},
    {0xA03C1380u,(uintptr_t)gr2_menu_categories},
    {0xA039D168u,(uintptr_t)gr2_menu_descriptor_chain}
};
static int prepared(void){
    /* Unaligned Thumb BL at the original final-return pair; read halfwords. */
    if(HALF(0xA0020AD2u)!=0xF0A4u||HALF(0xA0020AD4u)!=0xF80Du||
       WORD(0xA00C4AF0u)!=0x4B004718u||WORD(0xA00C4AF4u)!=(uint32_t)(uintptr_t)gr2_finalize_chain)return 0;
    if(HALF(0xA00E5D92u)!=0xB408u||HALF(0xA00E5D94u)!=0x4B01u||HALF(0xA00E5D96u)!=0x4718u||
       WORD(0xA00E5D98u)!=0x46C046C0u||WORD(0xA00E5D9Cu)!=(uint32_t)(uintptr_t)gr2_hdf_layout_chain)return 0;
    if(HALF(0xA014ADEEu)!=0x4B01u||HALF(0xA014ADF0u)!=0x4718u||HALF(0xA014ADF2u)!=0x46C0u||
       WORD(0xA014ADF4u)!=(uint32_t)(uintptr_t)gr2_hdf_core_chain||
       WORD(0xA014ACECu)!=0xB4084B01u||WORD(0xA014ACF0u)!=0x471846C0u||
       WORD(0xA014ACF4u)!=(uint32_t)(uintptr_t)gr2_hdf_band_chain)return 0;
    if(HALF(0xA02AF6CEu)!=0x4B01u||HALF(0xA02AF6D0u)!=0x4718u||HALF(0xA02AF6D2u)!=0x46C0u||
       WORD(0xA02AF6D4u)!=(uint32_t)(uintptr_t)gr2_hdf_postprocess_chain)return 0;
    if(HALF(0xA02ADEA6u)!=0x4B01u||HALF(0xA02ADEA8u)!=0x4718u||HALF(0xA02ADEAAu)!=0x46C0u||
       WORD(0xA02ADEACu)!=(uint32_t)(uintptr_t)gr2_hdf_production_chain)return 0;
    if(HALF(0xA02AE7F6u)!=0xB408u||WORD(0xA02AE7F8u)!=0x4B014718u||
       WORD(0xA02AE7FCu)!=0x46C046C0u||WORD(0xA02AE800u)!=(uint32_t)(uintptr_t)gr2_hdf_preparation_chain||
       HALF(0xA02AE83Eu)!=0xF616u||HALF(0xA02AE840u)!=0xF95Bu||
       WORD(0xA00C4AF8u)!=0xB4084B01u||WORD(0xA00C4AFCu)!=0x471846C0u||
       WORD(0xA00C4B00u)!=(uint32_t)(uintptr_t)gr2_hdf_reservation_chain)return 0;
    if(WORD(0xA029DEB8u)!=0x4B004718u||WORD(0xA029DEBCu)!=(uint32_t)(uintptr_t)gr2_hdf_policy_chain)return 0;
    if(WORD(0xA0023154u)!=0xA0800000u||WORD(0xA01137ECu)!=GR2_IMAGE_BODY_BYTES||
       WORD(0xA05F5400u)!=0x47700000u||WORD(0xA0044F4Cu)!=0xE12FFF1Eu||
       HALF(0xA039D60Eu)!=0x2D6Bu)return 0;
    for(uint32_t i=0;i<sizeof(hooks)/sizeof(hooks[0]);i++)
        if(WORD(hooks[i].address)!=0x4B004718u||WORD(hooks[i].address+4)!=(uint32_t)hooks[i].target)return 0;
    static const uint8_t modules[]={0,1,4,2,3,5,10,11,8,9,6,12,13,14};
    typedef uint32_t (*loaded_fn)(uint32_t);
    for(uint32_t i=0;i<sizeof(modules);i++)if(!((loaded_fn)(uintptr_t)0xA0040DC1u)(modules[i]))return 0;
    const uint32_t heads=0xA05FB0CCu,pool=WORD(0xA0129C54u),max=HALF(0xA00B5BFCu);
    if(!max||max>64u||pool<heads+28u||pool>heads+28u*max||(pool-heads)%28u||
       WORD(pool)!=0x4D504C20u||BYTE(pool+4)!=1u||HALF(pool+20)!=(pool-heads)/28u||
       WORD(pool+8)!=(GR2_IMAGE_BODY_BYTES+8u)||WORD(pool+12)!=60u*(GR2_IMAGE_BODY_BYTES+8u))return 0;
    uint32_t id=(pool-heads)/28u,table=WORD(0xA00B5BDCu),total=60u*(GR2_IMAGE_BODY_BYTES+8u);
    if(table!=0xA05F8E30u)return 0;
    uint32_t record=table+24u*(id-1u),base=WORD(record+20),pixel_end=WORD(0xA0129C2Cu);
    if(HALF(record)!=0xFFFFu||WORD(record+12)!=total||WORD(record+16)!=(GR2_IMAGE_BODY_BYTES+8u)||
       pixel_end<0xA0900000u||pixel_end>0xBFDC0000u||base<pixel_end||base>0xBFDC0000u-total)return 0;
    return 1;
}
int gr2_native_ready(void){return gr2_activation_ready==1u;}
int gr2_native_activate(void){
    if(!prepared())return 0;
    uint32_t state=gr2_cpu_state(),mode=state&31u,masks=state&0xC0u;
    if((mode!=0x10u&&mode!=0x13u&&mode!=0x1Fu)||(masks!=0u&&masks!=0xC0u))return 0;
    uint32_t previous=WORD(0xA00AF884u),owned=(uint32_t)(uintptr_t)gr2_cache_svc_entry;
    if(previous!=0xA00AF8A8u&&previous!=owned)return 0;
    if(gr2_activation_ready)return previous==owned;
    typedef void (*cpu_fn)(void);
    if(!masks)((cpu_fn)(uintptr_t)0xA00AF6F4u)();
    if((gr2_cpu_state()&0xC0u)!=0xC0u){if(!masks)((cpu_fn)(uintptr_t)0xA00AF728u)();return 0;}
    if(WORD(0xA00AF884u)!=previous){if(!masks)((cpu_fn)(uintptr_t)0xA00AF728u)();return 0;}
    WORD(0xA00AF884u)=owned;
    int synchronized=gr2_code_sync();
    if(synchronized)gr2_activation_ready=1;
    else WORD(0xA00AF884u)=previous;
    if(!masks)((cpu_fn)(uintptr_t)0xA00AF728u)();
    return synchronized;
}
