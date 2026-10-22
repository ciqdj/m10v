.syntax unified
.arm
.fpu vfpv3
.text
/* Incoming native ABI: s0 mag,r1 quality,r2 aspect,r3 width,[sp] height.
 * C helpers use soft-float bits r0. No VFP arithmetic inside C helpers. */
.global m10v_zoom_capture_resolution_hook
.type m10v_zoom_capture_resolution_hook,%function
m10v_zoom_capture_resolution_hook:
    push {r0-r4,lr}
    ldr r4,[sp,#24]
    vpush {d0}
    sub sp,sp,#8
    str r4,[sp]
    vmov r0,s0
    bl m10v_zoom_capture_resolution
    cmp r0,#0
    add sp,sp,#8
    vpop {d0}
    popeq {r0-r4,lr}
    beq m10v_zoom_original_resolution
    pop {r0-r4,pc}
/* Soft-float bridge to the ORIGINAL existing aspect-aware resolution route. */
.global m10v_zoom_capture_native_resolution
.type m10v_zoom_capture_native_resolution,%function
m10v_zoom_capture_native_resolution:
    vmov s0,r0
    b m10v_zoom_original_resolution
.global m10v_zoom_capture_raw_bits
.type m10v_zoom_capture_raw_bits,%function
m10v_zoom_capture_raw_bits:
    push {r4,lr}
    bl m10v_zoom_native_raw_mag
    vmov r0,s0
    pop {r4,pc}
.global m10v_zoom_capture_caption_hook
.type m10v_zoom_capture_caption_hook,%function
m10v_zoom_capture_caption_hook:
    push {r0-r4,lr}
    vpush {d0}
    vmov r0,s0
    bl m10v_zoom_capture_caption
    cmn r0,#1
    vpop {d0}
    popeq {r0-r4,lr}
    beq m10v_zoom_original_crop_caption
    str r0,[sp]
    pop {r0-r4,pc}
.global m10v_zoom_capture_icon_hook
.type m10v_zoom_capture_icon_hook,%function
m10v_zoom_capture_icon_hook:
    push {r0-r4,lr}
    vpush {d0}
    vmov r0,s0
    bl m10v_zoom_capture_custom
    cmp r0,#0
    vpop {d0}
    pop {r0-r4,lr}
    beq m10v_zoom_original_crop_icon
    mov r0,#0
    bx lr
