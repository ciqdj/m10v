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
/* One bounded line through the camera's initialized UTF-16/font service.
 * Colors are stock symbolic UI colors, not RGBA or guessed palette entries.
 * The caller runs on the existing UI owner; this does not initialize global
 * graphics/font services or publish a screen. */
static int text_draw(const uint16_t *text,uint32_t count,const int16_t rectangle[4],uint32_t color,uint32_t full){
    if(!text||((uintptr_t)text&1)||!count||count>96||!rectangle||((uintptr_t)rectangle&1)||
       (uintptr_t)text>UINTPTR_MAX-2*(count+1)||(uintptr_t)rectangle>UINTPTR_MAX-8||
       color<0x20000u||color>0x20101u)return 0;
    for(uint32_t i=0;i<count;i++)if(!text[i])return 0;
    if(text[count])return 0;
    int16_t left=rectangle[0],top=rectangle[1],right=rectangle[2],bottom=rectangle[3];
    if(left<0||top<0||right<left||bottom<top||right>=(full?720:640)||bottom>=480)return 0;
    typedef uint8_t *(*context_fn)(uint32_t);
    uint8_t *context=((context_fn)(uintptr_t)0xA039DA57u)(full?0:2);
    const uint16_t *geometry=(const uint16_t *)(const void *)context;
    if(!context||geometry[2]!=720||geometry[3]!=480||geometry[4]!=(full?720:640)||geometry[5]!=480)return 0;
    const uint32_t *words=(const uint32_t *)(const void *)context;
    if(!words[4]||!words[5])return 0;
    const uint32_t *fonts=(const uint32_t *)(uintptr_t)0xA077D70Cu;
    if(!fonts[4]||!fonts[5]||!fonts[8])return 0;
    uint32_t descriptor[11]={1,0x001c001au,0x00080009u,(uint32_t)(uintptr_t)text,
                             0x20000u,color,0x20000u,0,0,0,0};
    int16_t *box=(int16_t *)(void *)((uint8_t *)descriptor+0x24);
    box[0]=left;box[1]=top;box[2]=right;box[3]=bottom;
    typedef void (*draw_fn)(void *,void *);
    ((draw_fn)(uintptr_t)0xA03BC4DDu)(context,descriptor);
    return 1;
}
int gr2_text_draw(const uint16_t *text,uint32_t count,const int16_t rectangle[4],uint32_t color){
    return text_draw(text,count,rectangle,color,0);
}
int gr2_text_draw_full(const uint16_t *text,uint32_t count,const int16_t rectangle[4],uint32_t color){
    return text_draw(text,count,rectangle,color,1);
}
_Static_assert(sizeof(gr2_overlay)==36,"GR II overlay prefix ABI");
static int overlay_registered(const gr2_overlay *overlay){
    typedef int (*member_fn)(const void *);
    return ((member_fn)(uintptr_t)0xA0399183u)(overlay)!=0;
}
int gr2_overlay_attach(gr2_overlay *overlay){
    if(!overlay||((uintptr_t)overlay&3)||(uintptr_t)overlay>UINTPTR_MAX-sizeof(*overlay)||
       !overlay->event||!overlay->destroy||overlay->event_table||overlay->children||overlay->count||overlay->reserved||overlay->flags)return 0;
    const uint32_t *views=(const uint32_t *)(uintptr_t)*(const uint32_t *)(uintptr_t)0xA0398DC4u;
    if(!views||!views[0]||overlay_registered(overlay))return 0;
    uint32_t available=0;
    for(uint32_t i=1;i<=5;i++)if(!views[i])available=1;
    if(!available)return 0;
    typedef void (*attach_fn)(void *,uint32_t,uint32_t,uint32_t,uint32_t);
    ((attach_fn)(uintptr_t)0xA0399095u)(overlay,0,0,1,0);
    return overlay_registered(overlay);
}
int gr2_overlay_detach(gr2_overlay *overlay){
    if(!overlay||((uintptr_t)overlay&3)||!overlay_registered(overlay))return 0;
    typedef void (*detach_fn)(void *,uint32_t);
    ((detach_fn)(uintptr_t)0xA0398A5Fu)(overlay,0);
    /* The destructor may already have released its owner. Only compare the
     * address against stock registration slots; never read overlay again. */
    return !overlay_registered(overlay);
}
int gr2_fill_rect(uint32_t index,const int16_t rectangle[4],uint32_t color){
    if(index>1||!rectangle||((uintptr_t)rectangle&1)||(uintptr_t)rectangle>UINTPTR_MAX-8||
       color<0x20000u||color>0x20101u)return 0;
    int16_t box[4];for(uint32_t i=0;i<4;i++)box[i]=rectangle[i];
    if(box[0]<0||box[1]<0||box[2]<box[0]||box[3]<box[1]||box[2]>=720||box[3]>=480)return 0;
    typedef uint8_t *(*context_fn)(uint32_t);
    uint8_t *context=((context_fn)(uintptr_t)0xA039DA57u)(index);
    const uint16_t *geometry=(const uint16_t *)(const void *)context;
    if(!context||geometry[2]!=720||geometry[3]!=480||geometry[4]!=720||geometry[5]!=480||
       !((const uint32_t *)(const void *)context)[4])return 0;
    /* The high-level helper rescales against the stock 640-wide reference.
     * This bridge accepts physical coordinates, like the stock bitmap blitter,
     * so use the context's original bounded rectangle implementation directly. */
    const uint32_t *methods=(const uint32_t *)(const void *)context;
    if(!methods[0x44/4])return 0;
    uint32_t style[4]={0x01000000u,color,color,0};
    typedef void (*fill_fn)(void *,uint32_t,const void *,const void *);
    ((fill_fn)(uintptr_t)methods[0x44/4])(context,0,box,style);
    return 1;
}
