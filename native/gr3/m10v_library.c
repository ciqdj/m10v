/* Original M10V runtime. Existing simulation tables are embedded losslessly
 * with their source notices; no third-party camera runtime or signed film
 * package is loaded. Camera services have separately verified ABI boundaries. */
#include "m10v_library.h"
#include "halation_core.h"
#include "film_5207.h"
#include <stddef.h>
#include "m10v_legacy_data.h"
#include "halation_energy.h"

typedef struct {
    char name[24];
    int16_t contrast, saturation, turn;
    int8_t lift, bend, cb, cr;
} film;

/* Original M10V looks, specified in a software Y/CbCr color domain.
 * Names describe these looks; they do not claim a measured film-stock match. */
static const film films[33] = {
    {"M10V Neutral",256,256,0,0,0,0,0},
    {"Amber Day",268,264,0,2,5,-8,10},
    {"Cool Dusk",252,238,0,4,-2,12,-5},
    {"Warm Fade",232,224,0,12,4,-6,8},
    {"Deep Street",294,244,0,-3,-4,3,1},
    {"Soft Portrait",238,226,0,8,6,-3,5},
    {"Ocean Blue",264,272,-8,0,3,10,-6},
    {"Autumn Copper",270,248,12,2,4,-10,12},
    {"Muted Olive",242,202,-12,8,1,-5,-3},
    {"Clear Morning",252,250,0,5,8,1,2},
    {"Night Cyan",286,236,-4,-2,-3,10,-3},
    {"Sunset Rose",254,258,8,4,5,-3,12},
    {"Bleached Noon",278,164,0,5,-2,-2,3},
    {"Pastel Sky",222,218,0,13,9,4,0},
    {"Dense Color",290,302,0,-1,1,0,0},
    {"Earth Tone",264,224,6,6,0,-8,5},
    {"Silver Mono",270,0,0,1,1,0,0},
    {"Soft Mono",222,0,0,12,6,0,0},
    {"Hard Mono",316,0,0,-5,-2,0,0},
    {"Warm Mono",252,0,0,6,3,-4,5},
    {"Cold Mono",266,0,0,3,-1,6,-3},
    {"Green Glass",256,246,-10,4,2,-6,-6},
    {"Lilac Haze",234,222,8,10,6,7,5},
    {"Desert Light",274,236,0,8,8,-10,5},
    {"Urban Steel",272,208,-3,2,-4,8,-4},
    {"Spring Leaf",246,280,-8,7,4,-3,-3},
    {"Red Brick",276,270,9,0,1,-5,10},
    {"Paper White",236,180,0,14,8,0,0},
    {"Blue Hour",268,216,-6,5,-2,14,-7},
    {"Golden Shade",244,242,4,10,4,-9,8},
    {"Low Key Color",304,250,0,-6,-4,2,3},
    {"High Key Color",230,230,0,17,10,-2,3},
    {"800T",264,238,0,1,3,10,-16}
};

static uint32_t checksum(const m10v_library_state *state) {
    const uint8_t *bytes = (const uint8_t *)state;
    uint32_t crc = 0xffffffffu;
    for (uint32_t i = 0; i < offsetof(m10v_library_state, crc); ++i) {
        crc ^= bytes[i];
        for (uint32_t bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}
static void copy_state(m10v_library_state *dst, const m10v_library_state *src) {
    for (uint32_t i = 0; i < sizeof(*src); ++i)
        ((uint8_t *)dst)[i] = ((const uint8_t *)src)[i];
}
void m10v_library_init(m10v_library_state *state) {
    if (!state) return;
    for (uint32_t i = 0; i < sizeof(*state); ++i) ((uint8_t *)state)[i] = 0;
#ifdef M10V_INITIAL_STATE_BYTES
    static const uint8_t initial[104] = {M10V_INITIAL_STATE_BYTES};
    for (uint32_t i = 0; i < sizeof(*state); ++i) ((uint8_t *)state)[i] = initial[i];
#else
    state->magic = 0x5630314du; state->version = 4; state->size = sizeof(*state);
    for (uint32_t i = 0; i < M10V_SLOT_COUNT; ++i) {
        state->slots[i].film = (uint16_t)(i == 4 ? 33 : i + 34);
        state->slots[i].halo_gain=3; state->slots[i].halo_spread=3;
        state->effects[i].grain_size=1;state->effects[i].leak_spread=4;
        state->slots[i].halo_threshold=5; state->slots[i].halo_profile=2;
    }
    state->crc = checksum(state);
#endif
}
int m10v_library_valid(const m10v_library_state *state) {
    if (!state || state->magic != 0x5630314du || state->version != 4 ||
        state->size != sizeof(*state) || state->reserved || state->stamp > 2 ||
        state->format > 3 || state->corner > 3 || state->color > 3 || state->crc != checksum(state)) return 0;
    for (uint32_t i = 0; i < M10V_SLOT_COUNT; ++i)
        if (!state->slots[i].film || state->slots[i].film > M10V_FILM_COUNT ||
            state->slots[i].grain > 3 || state->slots[i].soft > 3 || state->slots[i].halo_gain>8 || state->slots[i].halo_spread>8 ||
            state->slots[i].halo_threshold>8 || state->slots[i].halo_profile>3) return 0;
    for(uint32_t i=0;i<5;i++){const m10v_film_effects *e=&state->effects[i];
        if(e->grain_size>2||e->leak_gain>8||e->leak_position>5||e->leak_spread>8||e->leak_variation>1||e->film_exposure>2||(state->slots[i].film!=68&&e->film_exposure)||e->reserved[0]||e->reserved[1])return 0;}
    return 1;
}
const char *m10v_library_name(uint32_t id) {
    static const char appended_names[3][12]={"5207","Phoenix II","HARMAN RED"};
    return !id || id>M10V_FILM_COUNT ? (const char *)0 : id>=66 ? appended_names[id-66] : id<=33 ? films[id-1].name : legacy_records[id-34].name;
}
static int commit(m10v_library_state *state, m10v_library_state *next,
                  m10v_library_store store, void *context) {
    if (!store || state->sequence == 0xffffffffu) return M10V_LIBRARY_INVALID;
    next->sequence = state->sequence + 1; next->crc = checksum(next);
    if (store(context, next) != 0) return M10V_LIBRARY_STORE_FAILED;
    copy_state(state, next); return M10V_LIBRARY_OK;
}
int m10v_library_reset(m10v_library_state *state,uint32_t slot,m10v_library_store store,void *context){
    if(!m10v_library_valid(state)||slot>=M10V_SLOT_COUNT)return M10V_LIBRARY_INVALID;
    m10v_library_state next,defaults;copy_state(&next,state);m10v_library_init(&defaults);
    uint32_t id=state->slots[slot].film;
    if(defaults.slots[slot].film!=id){
        m10v_slot *v=&defaults.slots[slot];v->film=(uint16_t)id;
        v->grain=id==68?2:id==66||id==67?1:0;v->soft=0;
        v->halo_gain=id==33?3:id==67?2:0;v->halo_spread=3;v->halo_threshold=5;v->halo_profile=id==66?1:2;
        m10v_film_effects e={id==67?0:1,0,0,4,0,0,{0,0}};defaults.effects[slot]=e;
    }
    next.slots[slot]=defaults.slots[slot];next.effects[slot]=defaults.effects[slot];
    return commit(state,&next,store,context);
}
int m10v_library_select(m10v_library_state *state, uint32_t slot, uint32_t id,
                        m10v_library_store store, void *context) {
    if (!m10v_library_valid(state) || slot >= M10V_SLOT_COUNT || !id || id > M10V_FILM_COUNT)
        return M10V_LIBRARY_INVALID;
    m10v_library_state next; copy_state(&next, state); next.slots[slot].film = (uint16_t)id;
    if(id==66&&state->slots[slot].film!=66){next.slots[slot].grain=1;next.slots[slot].soft=0;next.slots[slot].halo_gain=0;next.slots[slot].halo_spread=3;next.slots[slot].halo_threshold=5;next.slots[slot].halo_profile=1;
        m10v_film_effects e={1,0,0,4,0,0,{0,0}};next.effects[slot]=e;}
    if((id==67||id==68)&&state->slots[slot].film!=id){
        m10v_slot *v=&next.slots[slot];v->grain=id==67?1:2;v->soft=0;v->halo_gain=id==67?2:0;v->halo_spread=3;v->halo_threshold=5;v->halo_profile=2;
        m10v_film_effects e={id==67?0:1,0,0,4,0,0,{0,0}};next.effects[slot]=e;
    }
    if(id!=68)next.effects[slot].film_exposure=0;
    return commit(state, &next, store, context);
}
int m10v_library_texture(m10v_library_state *state, uint32_t slot, uint32_t grain, uint32_t soft,
                         m10v_library_store store, void *context) {
    if (!m10v_library_valid(state) || slot >= M10V_SLOT_COUNT || grain > 3 || soft > 3)
        return M10V_LIBRARY_INVALID;
    m10v_library_state next; copy_state(&next, state);
    next.slots[slot].grain = (uint8_t)grain; next.slots[slot].soft = (uint8_t)soft;
    return commit(state, &next, store, context);
}
int m10v_library_halation(m10v_library_state *state,uint32_t slot,uint32_t gain,uint32_t spread,uint32_t threshold,uint32_t profile,m10v_library_store store,void *context) {
    if(!m10v_library_valid(state)||slot>=5||(state->slots[slot].film==66||state->slots[slot].film==68)||gain>8||spread>8||threshold>8||profile>3)return M10V_LIBRARY_INVALID;
    m10v_library_state next;copy_state(&next,state);
    next.slots[slot].halo_gain=(uint8_t)gain;next.slots[slot].halo_spread=(uint8_t)spread;
    next.slots[slot].halo_threshold=(uint8_t)threshold;next.slots[slot].halo_profile=(uint8_t)profile;
    return commit(state,&next,store,context);
}
int m10v_library_detail(m10v_library_state *state,uint32_t slot,uint32_t gain,uint32_t spread,uint32_t threshold,uint32_t grain,uint32_t soft,m10v_library_store store,void *context) {
    if(!m10v_library_valid(state)||slot>=5||state->slots[slot].film!=33||gain>8||spread>8||threshold>8||grain>3||soft>3)return M10V_LIBRARY_INVALID;
    m10v_library_state next;copy_state(&next,state);
    m10v_slot *v=&next.slots[slot];v->halo_gain=(uint8_t)gain;v->halo_spread=(uint8_t)spread;
    v->halo_threshold=(uint8_t)threshold;v->grain=(uint8_t)grain;v->soft=(uint8_t)soft;v->halo_profile=2;
    return commit(state,&next,store,context);
}
int m10v_library_stamp(m10v_library_state *state, uint32_t enabled, uint32_t format,
                       uint32_t corner, uint32_t color, m10v_library_store store, void *context) {
    if (!m10v_library_valid(state) || enabled > 2 || format > 3 || corner > 3 || color > 3)
        return M10V_LIBRARY_INVALID;
    m10v_library_state next; copy_state(&next, state);
    next.stamp = (uint8_t)enabled; next.format = (uint8_t)format;
    next.corner = (uint8_t)corner; next.color = (uint8_t)color;
    return commit(state, &next, store, context);
}
int m10v_library_effects(m10v_library_state *state,uint32_t slot,uint32_t field,uint32_t value,m10v_library_store store,void *ctx){
    static const uint8_t limits[5]={2,8,5,8,1};
    if(!m10v_library_valid(state)||slot>=5||field>6)return M10V_LIBRARY_INVALID;
    if(field==6?(state->slots[slot].film!=68||value>2):field==5?value!=0:value>limits[field])return M10V_LIBRARY_INVALID;
    m10v_library_state next;copy_state(&next,state);
    if(field==5){
        m10v_film_effects e={next.slots[slot].film==67?0:1,0,0,4,0,next.effects[slot].film_exposure,{0,0}};next.effects[slot]=e;
        next.slots[slot].grain=next.slots[slot].film==68?2:(next.slots[slot].film==66||next.slots[slot].film==67)?1:0;next.slots[slot].soft=0;
    } else if(field==6)next.effects[slot].film_exposure=(uint8_t)value;
    else ((uint8_t *)&next.effects[slot])[field]=(uint8_t)value;
    return commit(state,&next,store,ctx);
}
static uint8_t clamp(int value) { return (uint8_t)(value < 0 ? 0 : value > 255 ? 255 : value); }
static int overlap(const void *a, uint32_t an, const void *b, uint32_t bn) {
    uintptr_t x = (uintptr_t)a, z = (uintptr_t)b;
    return x <= UINTPTR_MAX - an && z <= UINTPTR_MAX - bn && x < z + bn && z < x + an;
}
static int date_valid(const m10v_library_date *date) {
    static const uint8_t days[12] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (!date || date->year < 1980 || date->year > 2199 || !date->month || date->month > 12 ||
        !date->day || date->hour > 23 || date->minute > 59) return 0;
    uint32_t max = days[date->month - 1];
    if (date->month == 2 && date->year % 4 == 0 && (date->year % 100 != 0 || date->year % 400 == 0)) ++max;
    return date->day <= max;
}
static void digits(char *dst, uint32_t value, uint32_t count) {
    while (count) { --count; dst[count] = (char)('0' + value % 10); value /= 10; }
}
static uint32_t date_text(char *text, const m10v_library_date *date, uint32_t format, uint32_t mode) {
    uint32_t n = format == 3 ? 8 : 10;
    if (format == 1) { digits(text, date->day, 2); text[2] = '.'; digits(text + 3, date->month, 2);
        text[5] = '.'; digits(text + 6, date->year, 4); }
    else { uint32_t y = format == 3 ? 2 : 4; digits(text, date->year, y);
        text[y] = format == 2 ? '-' : '.'; digits(text + y + 1, date->month, 2);
        text[y + 3] = text[y]; digits(text + y + 4, date->day, 2); }
    if (mode == 2) { text[n++] = ' '; digits(text + n, date->hour, 2); n += 2;
        text[n++] = ':'; digits(text + n, date->minute, 2); n += 2; }
    return n;
}
/* Original five-by-seven bitmap glyphs for decimal date/time notation. */
static const uint8_t glyphs[10][7] = {
    {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},
    {30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},
    {14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},
    {14,17,17,15,1,1,14}
};
static uint32_t glyph(char c, uint32_t row) {
    if (c >= '0' && c <= '9') return glyphs[c - '0'][row];
    if (c == '.') return row == 6 ? 4u : 0u;
    if (c == '-') return row == 3 ? 14u : 0u;
    if (c == ':') return row == 2 || row == 4 ? 4u : 0u;
    return 0;
}
static void stamp(m10v_library_image *image, const m10v_library_state *state,
                   const m10v_library_date *date) {
    char text[24]; uint32_t count = date_text(text, date, state->format, state->stamp);
    uint32_t scale = image->width / 1200u; if (!scale) scale = 1;
    uint32_t tw = count * 6 * scale, th = 8 * scale;
    uint32_t margin = image->width / 100 + 2;
    if (tw + margin * 2 >= image->width || th + margin * 2 >= image->height) return;
    uint32_t left = (state->corner & 1) ? image->width - margin - tw : margin;
    uint32_t top = (state->corner & 2) ? image->height - margin - th : margin;
    static const uint8_t colors[4][3] = {{235,128,128},{180,80,185},{82,90,240},{210,16,146}};
    for (uint32_t pass = 0; pass < 2; ++pass)
        for (uint32_t i = 0; i < count; ++i)
            for (uint32_t row = 0; row < 7; ++row)
                for (uint32_t col = 0; col < 5; ++col) {
                    if (!(glyph(text[i], row) & (1u << (4 - col)))) continue;
                    for (uint32_t dy = 0; dy < scale; ++dy) for (uint32_t dx = 0; dx < scale; ++dx) {
                        uint32_t x = left + (i * 6 + col) * scale + dx + (pass ? 0 : scale);
                        uint32_t y = top + row * scale + dy + (pass ? 0 : scale);
                        image->y[y * image->stride + x] = pass ? colors[state->color][0] : 16;
                        uint32_t at = y * image->stride + (x & ~1u);
                        image->chroma[at] = pass ? colors[state->color][1] : 128;
                        image->chroma[at + 1] = pass ? colors[state->color][2] : 128;
                    }
                }
}
/* Existing tables are decoded exactly; RGB evaluation is an explicitly new
 * saved-JPEG path, not a claim that it reproduces the stock ISP pixel-for-pixel. */
int m10v_library_tables(uint32_t id,int16_t *matrix,int16_t *post,uint16_t *curves,uint16_t *knots){
    if(id<34||id>65||!matrix||!post||!curves||!knots)return -1;
    const m10v_legacy_record *record=&legacy_records[id-34];
    uint32_t at=record->offset,end=at+record->size;
    if(end>sizeof(legacy_bytes))return -1;
    for(uint32_t i=0;i<9;++i){matrix[i]=record->matrix[i];post[i]=record->post[i];}
    for(uint32_t bank=0;bank<2;++bank)for(uint32_t channel=0;channel<3;++channel){
        uint32_t value=0,count=bank?33:256;
        for(uint32_t i=0;i<count;++i){
            if(at>=end)return -1;uint32_t byte=legacy_bytes[at++],delta=byte&127;
            if(byte&128){if(at>=end||legacy_bytes[at]&128)return -1;delta|=(uint32_t)legacy_bytes[at++]<<7;}
            value+=delta;if(value>16383)return -1;
            if(bank)knots[channel*33+i]=(uint16_t)value;else curves[channel*256+i]=(uint16_t)value;
        }
    }
    return at==end?0:-1;
}
static int rounded(int value,uint32_t shift){
    int half=1<<(shift-1);return value>=0?(value+half)>>shift:-((-value+half)>>shift);
}
static int curve14(const uint16_t *curve,int input){
    if(input<=0)return curve[0];if(input>=255*8192)return curve[255];
    uint32_t index=(uint32_t)input>>13,fraction=(uint32_t)input&8191;
    return curve[index]+rounded((int)(curve[index+1]-curve[index])*(int)fraction,13);
}
static void legacy_rgb(uint8_t y,uint8_t cb,uint8_t cr,const int16_t *m,const int16_t *p,const uint16_t *curves,int *out){
    int u=(int)cb-128,v=(int)cr-128;
    int rgb[3]={clamp((int)y+rounded(91881*v,16)),clamp((int)y-rounded(22554*u+46802*v,16)),clamp((int)y+rounded(116130*u,16))};
    int mapped[3];
    for(uint32_t row=0;row<3;++row)mapped[row]=curve14(curves+256*row,rgb[0]*m[row*3]+rgb[1]*m[row*3+1]+rgb[2]*m[row*3+2]);
    for(uint32_t row=0;row<3;++row){
        int color=rounded(mapped[0]*p[row*3]+mapped[1]*p[row*3+1]+mapped[2]*p[row*3+2],9);
        if(color<0)color=0;if(color>16383)color=16383;out[row]=(color*255+8191)/16383;
    }
}
static int legacy_color(m10v_library_image *image,uint32_t id){
    int16_t matrix[9],post[9];uint16_t curves[768],knots[99];
    if(m10v_library_tables(id,matrix,post,curves,knots))return -1;
    for(uint32_t row=0;row<image->height;++row)for(uint32_t x=0;x<image->width;x+=2){
        uint32_t at=row*image->stride+x;int a[3],b[3];
        uint8_t cb=image->chroma[at],cr=image->chroma[at+1];
        legacy_rgb(image->y[at],cb,cr,matrix,post,curves,a);legacy_rgb(image->y[at+1],cb,cr,matrix,post,curves,b);
        image->y[at]=clamp(rounded(19595*a[0]+38470*a[1]+7471*a[2],16));
        image->y[at+1]=clamp(rounded(19595*b[0]+38470*b[1]+7471*b[2],16));
        int r=a[0]+b[0],g=a[1]+b[1],blue=a[2]+b[2];
        image->chroma[at]=clamp(128+rounded(-11059*r-21709*g+32768*blue,17));
        image->chroma[at+1]=clamp(128+rounded(32768*r-27439*g-5329*blue,17));
    }
    return 0;
}

static void soft_diffusion(m10v_library_image *image,const m10v_slot *choice,uint8_t *scratch,uint32_t cells,uint32_t gw,uint32_t gh,uint32_t shift){

        uint8_t *temp = scratch + cells;
        for (uint32_t i = 0; i < cells; ++i) scratch[i] = 0;
        for (uint32_t row = 0; row < image->height; ++row) for (uint32_t x = 0; x < image->width; ++x) {
            uint8_t v = image->y[row * image->stride + x]; uint32_t at = (row >> shift) * gw + (x >> shift);
            v = v > 192 ? (uint8_t)(v - 192) : 0; if (v > scratch[at]) scratch[at] = v;
        }
        for (uint32_t y = 0; y < gh; ++y) for (uint32_t x = 0; x < gw; ++x) {
            uint32_t total = 0;
            for (int dx = -2; dx <= 2; ++dx) { int xx = (int)x + dx; if (xx >= 0 && xx < (int)gw) total += scratch[y * gw + (uint32_t)xx]; }
            temp[y * gw + x] = (uint8_t)(total / 5);
        }
        for (uint32_t y = 0; y < gh; ++y) for (uint32_t x = 0; x < gw; ++x) {
            uint32_t total = 0;
            for (int dy = -2; dy <= 2; ++dy) { int yy = (int)y + dy; if (yy >= 0 && yy < (int)gh) total += temp[(uint32_t)yy * gw + x]; }
            scratch[y * gw + x] = (uint8_t)(total / 5);
        }
        for (uint32_t row = 0; row < image->height; ++row) for (uint32_t x = 0; x < image->width; ++x) {
            uint32_t at = row * image->stride + x; uint32_t v = image->y[at];
            uint32_t bloom = scratch[(row >> shift) * gw + (x >> shift)];
            image->y[at] = clamp((int)(v + bloom * choice->soft * 3 * (255 - v) / 255));
        }
}
/* Assumed Phoenix II orange/red scatter, weaker than the 800T grade. Build
 * the source from ORIGINAL luminance, then composite after colour rendering.
 * The vendor provides no measured PSF or hue: these are bounded design choices. */
static void phoenix_halation_source(const m10v_library_image *im,const m10v_slot *v,uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    uint16_t *a=(uint16_t *)scratch,*b=a+gw*gh;
    uint32_t step=1u<<shift,gate=176+8u*v->halo_threshold;
    for(uint32_t gy=0;gy<gh;++gy)for(uint32_t gx=0;gx<gw;++gx){
        uint32_t sum=0,peak=0;
        for(uint32_t dy=0;dy<step;++dy){
            uint32_t row=(gy<<shift)+dy;if(row>=im->height)break;
            for(uint32_t dx=0;dx<step;++dx){
                uint32_t x=(gx<<shift)+dx;if(x>=im->width)break;
                uint32_t light=im->y[row*im->stride+x];
                uint32_t excess=light>gate?light-gate:0,energy=excess*excess*8;
                sum+=energy;if(energy>peak)peak=energy;
            }
        }
        /* Preserve tiny lamps at step16 without another image scan. A small
         * bounded peak contribution supplements integrated cell energy; it
         * is not a claim of calibrated source area or a measured near PSF.
         * Max 49928 + 49928/16 < 65536, including partial edge cells. */
        a[gy*gw+gx]=(uint16_t)((sum>>(2*shift))+(shift?peak>>4:0));
    }
    energy_blur(a,b,gw,gh,1+v->halo_spread,1);
}
static void phoenix_halation_compose(m10v_library_image *im,const m10v_slot *v,const uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    const uint16_t *a=(const uint16_t *)scratch;
    for(uint32_t row=0;row<im->height;++row)for(uint32_t x=0;x<im->width;x+=2){
        uint32_t at=row*im->stride+x,y0=im->y[at],y1=im->y[at+1],peak=y0>y1?y0:y1;
        /* Shared chroma must not tint either member of a clipped bright pair. */
        if(peak>=240)continue;
        uint32_t protect=(255-peak)*4;if(protect>255)protect=255;
        uint32_t red=(energy_sample(a,gw,gh,x,row,shift)*v->halo_gain*protect)>>12;
        uint32_t limit=6u*v->halo_gain;if(red>limit)red=limit;
        /* Orange shoulder: more green than 800T, with a six-level red cap
         * per gain step (800T permits 192). All products fit uint32_t. */
        uint32_t green=red>>2,lift=(77*red+150*green+128)>>8;
        im->y[at]=clamp((int)(y0+lift));im->y[at+1]=clamp((int)(y1+lift));
        im->chroma[at]=clamp((int)im->chroma[at]-(int)((43*red+85*green+128)>>8));
        im->chroma[at+1]=clamp((int)im->chroma[at+1]+(int)((128*red-107*green+128)>>8));
    }
}
int m10v_library_render(m10v_library_image *image, const m10v_library_state *state,
                        uint32_t slot, const m10v_library_date *date, uint32_t seed,
                        uint8_t *scratch, uint32_t scratch_bytes) {
    if (!image || !m10v_library_valid(state) || slot >= M10V_SLOT_COUNT ||
        !image->y || !image->chroma || image->width < 2 || image->width > 6144 ||
        (image->width & 1) || !image->height || image->height > 4096 ||
        image->stride < image->width || image->stride > 16384 || (image->stride & 1))
        return M10V_LIBRARY_INVALID;
    uint32_t bytes = image->stride * image->height;
    if (bytes > image->y_bytes || bytes > image->chroma_bytes ||
        (uintptr_t)image->y > UINTPTR_MAX - bytes || (uintptr_t)image->chroma > UINTPTR_MAX - bytes ||
        overlap(image->y, bytes, image->chroma, bytes) ||
        overlap(image->y, bytes, state, sizeof(*state)) || overlap(image->chroma, bytes, state, sizeof(*state)) ||
        overlap(image->y, bytes, image, sizeof(*image)) || overlap(image->chroma, bytes, image, sizeof(*image)) ||
        (state->stamp && (!date_valid(date) || overlap(image->y, bytes, date, sizeof(*date)) ||
          overlap(image->chroma, bytes, date, sizeof(*date))))) return M10V_LIBRARY_INVALID;
    const m10v_slot *choice = &state->slots[slot];
    uint32_t shift = 0, gw = image->width, gh = image->height;
    /* Power-of-two sampling must not depend on an ARM division runtime. */
    while (gw > 384 || gh > 256) {
        ++shift;
        uint32_t mask = (1u << shift) - 1;
        gw = (image->width + mask) >> shift; gh = (image->height + mask) >> shift;
    }
    uint32_t cells = gw * gh;
    uint32_t use_halo = (choice->film == 33 || choice->film == 67) && choice->halo_gain;
    uint32_t needed = ((((choice->film == 33 || choice->film == 67) ? 6 : 2)) * cells + 3) & ~3u;
    if ((choice->soft || use_halo) && (!scratch || ((uintptr_t)scratch & 3) || scratch_bytes < needed ||
        (uintptr_t)scratch > UINTPTR_MAX - needed || overlap(scratch, needed, image->y, bytes) ||
        overlap(scratch, needed, image->chroma, bytes) || overlap(scratch, needed, state, sizeof(*state)) ||
        overlap(scratch, needed, image, sizeof(*image)) ||
        (state->stamp && overlap(scratch, needed, date, sizeof(*date))))) return M10V_LIBRARY_INVALID;
    if (use_halo) {
        /* Keep the previous full-capacity preflight without linking the
         * retired halation renderer; the energy model below owns 800T. */
        if((uintptr_t)image->y>UINTPTR_MAX-image->y_bytes ||
           (uintptr_t)image->chroma>UINTPTR_MAX-image->chroma_bytes ||
           overlap(image->y,image->y_bytes,image->chroma,image->chroma_bytes))return M10V_LIBRARY_INVALID;
        if ((uintptr_t)scratch > UINTPTR_MAX-scratch_bytes ||
            overlap(scratch,scratch_bytes,image->y,image->y_bytes) ||
            overlap(scratch,scratch_bytes,image->chroma,image->chroma_bytes) ||
            overlap(scratch,scratch_bytes,state,sizeof(*state)) ||
            overlap(scratch,scratch_bytes,image,sizeof(*image)) ||
            (state->stamp && overlap(scratch,scratch_bytes,date,sizeof(*date)))) return M10V_LIBRARY_INVALID;
    }
    if(choice->film==33 && (use_halo || choice->soft))m10v_800t_effects(image,choice,scratch,gw,gh,shift);
    if(choice->film==67&&use_halo)phoenix_halation_source(image,choice,scratch,gw,gh,shift);
    if(choice->film==66&&choice->soft)soft_diffusion(image,choice,scratch,cells,gw,gh,shift);
    if(choice->film==66){m10v_5207_render(image,&state->effects[slot],choice->grain,seed);}
    else if(choice->film>=67){
        uint32_t exposure=state->effects[slot].film_exposure;
        m10v_5207_texture_q8(image,&state->effects[slot],choice->grain*(choice->film==68?(exposure==1?218:exposure==2?307:256):256),seed,choice->film==67?2:3+exposure);
    }
    else if(choice->film>33){if(legacy_color(image,choice->film))return M10V_LIBRARY_INVALID;}
    else {
    const film *look = &films[choice->film - 1];
    uint8_t curve[256];
    for (int v = 0; v < 256; ++v) curve[v] = clamp(128 + ((v - 128) * look->contrast) / 256 +
        (look->lift * (255 - v)) / 255 + (look->bend * v * (255 - v)) / 16384);
    for (uint32_t row = 0; row < image->height; ++row) for (uint32_t x = 0; x < image->width; x += 2) {
        uint32_t at = row * image->stride + x;
        int light = (image->y[at] + image->y[at + 1]) / 2;
        int weight = 255 - (light > 127 ? 2 * light - 255 : 255 - 2 * light);
        int cb = image->chroma[at] - 128, cr = image->chroma[at + 1] - 128;
        image->chroma[at] = clamp(128 + (cb * look->saturation + cr * look->turn) / 256 + look->cb * weight / 255);
        image->chroma[at + 1] = clamp(128 + (cr * look->saturation - cb * look->turn) / 256 + look->cr * weight / 255);
        image->y[at] = curve[image->y[at]]; image->y[at + 1] = curve[image->y[at + 1]];
    }
    }
    if(choice->film==67&&use_halo)phoenix_halation_compose(image,choice,scratch,gw,gh,shift);
    if (choice->soft && choice->film!=66 && choice->film!=33)soft_diffusion(image,choice,scratch,cells,gw,gh,shift);
    if(choice->film<66)m10v_5207_texture(image,&state->effects[slot],choice->grain,seed,0);
    if (state->stamp) stamp(image, state, date);
    return M10V_LIBRARY_OK;
}
