/* GR III 2.10 crop extension. Identity 5 is private to 6x7; old photos
 * retain their identities and geometry. No RAW pixel data is accessed. */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#define WORD(p,o) (*(u32 *)((p)+(o)))
#define BYTE(p,o) (*(u8 *)((p)+(o)))
#define CALL(a,t) ((t)(a))

/* Recognizable immutable record, rebound after the film resource range. */
__attribute__((used)) const volatile u32 m10v_aspect_id_record[3]={0x36523741,811,785};
const u8 m10v_aspect_values[5]={0,3,1,4,5};
const u8 m10v_aspect_classes[5]={2,1,3,4,0};

u32 m10v_aspect_id(void) { return m10v_aspect_id_record[1]; }
u32 m10v_aspect_count(void) { return 5; }
u32 m10v_aspect_next(u32 value) {
    for(u32 i=0;i<5;i++) if(m10v_aspect_values[i]==value)
        return m10v_aspect_values[i==4?0:i+1];
    return 0;
}
u32 m10v_aspect_current(void) {
    u32 root=CALL(0x53525d5c,u32 (*)(void))();
    return root && WORD(root,0) ? CALL(0x5354a778,u32 (*)(u32))(WORD(root,0)) : 0;
}
u32 m10v_aspect_mask_active(void) {
    u32 ratio=m10v_aspect_current();
    if(ratio!=4 && ratio!=5) return 0;
    u32 root=CALL(0x53525d5c,u32 (*)(void))();
    if(!root || !WORD(root,0) || CALL(0x53549958,u32 (*)(u32))(WORD(root,0))==1) return 0;
    u32 manager=CALL(0x53654150,u32 (*)(void))();
    return manager && !CALL(0x53654220,u32 (*)(u32,u32))(manager,0x4a);
}

void m10v_aspect_resolution(u32 mag,u32 quality,u16 *width,u16 *height) {
    static const u16 sizes[4][2]={{4672,4000},{3728,3200},{2608,2240},{1488,1280}};
    if(quality>3 || !width || !height) return;
    u32 index=quality;
    if(mag==0x3fa00000 && index<1) index=1;
    else if((mag==0x3fe3d70a || mag==0x3fe49249) && index<2) index=2;
    else if(mag!=0x3f800000 && mag!=0x3fa00000 && mag!=0x3fe3d70a && mag!=0x3fe49249) return;
    *width=sizes[index][0]; *height=sizes[index][1];
}
/* Native filter radius follows the diagonal of the output, normalized by
 * the uncropped 6000x4000 frame, as in the existing wide crop adapter. */
u32 m10v_aspect_filter(u32 mag,u32 crop_enabled) {
    if(crop_enabled) return 0x3f5a583c;
    if(mag==0x3fa00000) return 0x3f2e6ac0;
    if(mag==0x3fe3d70a || mag==0x3fe49249) return 0x3ef418fc;
    return 0x3f5a583c;
}
u32 m10v_aspect_live_width(u32 a,u32 b,u32 c,u32 d,u32 ratio) {
    u32 width=CALL(0x540b8678,u32 (*)(u32,u32,u32,u32,u32))(a,b,c,d,0);
    return ratio==5 && !m10v_aspect_mask_active()?2*((width*7+9)/18):width;
}
u32 m10v_aspect_live_height(u32 a,u32 b,u32 c,u32 d,u32 ratio) {
    u32 height=CALL(0x540b8680,u32 (*)(u32,u32,u32,u32,u32))(a,b,c,d,0);
    return ratio==4 && !m10v_aspect_mask_active()?2*((height*69+125)/250):height;
}
u32 m10v_aspect_write_active(u32 context,u32 unused,u32 mag) {
    (void)unused;
    /* Quantized JPEG dimensions mapped into the native 45x30 Q16 sensor
     * coordinates: width,height,left,top. Crop origins are centered in the
     * complete 6000x4000 sensor, including the native crop magnification.
     */
    static const u32 rects[3][4]={
        {2296381,1966080,326369,0},
        {1832387,1572864,558367,196608},
        {1281884,1101005,833618,432538}
    };
    u32 index=CALL(0x540b62f8,u32 (*)(u32))(mag);
    if(index>2) index=0;
    CALL(0x53665c2c,void (*)(u32))(context);
    for(u32 i=0;i<4;i++) WORD(context,0x64+4*i)=rects[index][i];
    /* Notification can return zero after a valid write. Publish only after
     * the final geometry is stored and retain its native return convention.
     */
    return CALL(0x536ae870,u32 (*)(u32))(context+0x24bc);
}

/* Masked live view keeps the native 3:2 focal crop underneath the mask.
 * Both AF and common refresh must publish the SAME source rectangle. Native
 * +24 is recomputed for crop/AF; fixed still-JPEG rectangles cannot replace it.
 * Outside this view (magnified focus/movie), retain the existing adapters. */
u32 m10v_aspect_live_region(u32 context,u32 mode,u32 ratio,u32 mag) {
    if(m10v_aspect_mask_active())
        return CALL(0x53666770,u32 (*)(u32,u32))(context,mag==0x2000?0:1);
    if(ratio==5) return m10v_aspect_write_active(context,mode,mag);
    return CALL(0x540b6240,u32 (*)(u32,u32,u32))(context,4,mag);
}

void m10v_aspect_draw(u32 view,u32 surface) {
    if(m10v_aspect_current()!=5) { CALL(0x540b8000,void (*)(u32,u32))(view,surface); return; }
    if(!view || !surface || !BYTE(view,0x9e)) return;
    u32 *canvas=(u32 *)(view+0x30),*clip=(u32 *)(view+0x64);
    if(canvas[0] || canvas[1] || !((canvas[2]==720&&canvas[3]==480)||(canvas[2]==360&&canvas[3]==240))) return;
    u32 graphics=CALL(0x5320804c,u32 (*)(void))();
    if(!graphics) return;
    graphics=CALL(0x532081ec,u32 (*)(u32))(graphics);
    if(!graphics) return;
    u32 scale=canvas[2]==720?2:1, mask=40*scale;
    typedef void (*Draw)(u32,u32,u32 *,u32 *,u32,u32,u32,u32,u32);
    Draw draw=CALL(0x540b88b4,Draw);
    draw(graphics,surface,canvas,clip,0,0,mask,canvas[3],16);
    draw(graphics,surface,canvas,clip,canvas[2]-mask,0,mask,canvas[3],16);
    draw(graphics,surface,canvas,clip,mask-scale,0,scale,canvas[3],2);
    draw(graphics,surface,canvas,clip,canvas[2]-mask,0,scale,canvas[3],2);
}

/* AF retains the native safety inset and follows all three crop magnifications. */
u32 m10v_aspect_af_bounds(u32 ratio,u32 crop,u32 *out) {
    if(ratio!=5) return CALL(0x540b6458,u32 (*)(u32,u32,u32 *))(ratio,crop,out);
    static const u16 rects[3][4]={{120,60,600,420},{136,60,584,420},{203,106,517,374}};
    if(!out) return 0;
    if(crop>2) crop=0;
    for(u32 i=0;i<4;i++) out[i]=rects[crop][i];
    return 1;
}
