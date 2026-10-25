.syntax unified
.arm
.fpu neon
.text
.macro entry name
.global m10v_zoom_\name
.type m10v_zoom_\name,%function
m10v_zoom_\name:
.endm
.macro jump addr
 movw ip,#:lower16:\addr
 movt ip,#:upper16:\addr
 bx ip
.endm
entry native_front_bits
 push {r4,lr}
 movw ip,#0x526c
 movt ip,#0x5324
 blx ip
 vmov r0,s0
 pop {r4,pc}
entry native_back_bits
 push {r4,lr}
 movw ip,#0xa7bc
 movt ip,#0x5354
 blx ip
 vmov r0,s0
 pop {r4,pc}
entry native_set_bits
 vmov s0,r1
 jump 0x53252684
/* Callsite replacements return resource ID in r0, preserving all callee-saved
 * registers. Native label callers allow caller-saved registers/flags clobber. */
entry label_live
 push {r4,lr}
 vmov r4,s0
 mov r0,r4
 bl m10v_zoom_camera_slot
 cmp r0,#2
 moveq r0,#2
 popeq {r4,pc}
 mov r0,r4
 bl m10v_zoom_caption
 pop {r4,pc}
entry label_menu
 mov r0,r5
 b m10v_zoom_label_slot
entry label_adj
 mov r0,r4
 b m10v_zoom_label_slot
entry label_slot
 cmp r0,#2
 moveq r0,#2
 bxeq lr
 push {r4,lr}
 bl m10v_zoom_camera_bits
 bl m10v_zoom_caption
 pop {r4,pc}

#if M10V_DEBUG_MODE
/* Record only failing native assertions; preserve the exact original call. */
entry assert_trace
 cmp r0,#0
 bne m10v_zoom_original_assert
 push {r0-r4,lr}
 vpush {d0-d7}
 sub sp,sp,#8
 ldr r1,[sp,#76]
 ldr r2,[sp,#80]
 ldr r3,[sp,#84]
 ldr ip,[sp,#92]
 str ip,[sp]
 mov r0,#212
 bl m10v_debug_log
 add sp,sp,#8
 vpop {d0-d7}
 pop {r0-r4,lr}
 b m10v_zoom_original_assert
#endif

/* Read-only rollback guard for persisted native ratios. Preserve all valid
 *28..50 ratios; finite larger values read as50, malformed/nonpositive as28.
 * No settings write or new display/AF/recipe hook. */
.macro guard_getter name
entry guard_\name
 push {r4,lr}
 bl m10v_zoom_original_\name\()_getter
 vmov r3,s0
 movw ip,#0
 movt ip,#0x3f80
 cmp r3,ip
 blo 1f
 movw ip,#0
 movt ip,#0x7f80
 cmp r3,ip
 bhs 1f
 movw ip,#0x9249
 movt ip,#0x3fe4
 cmp r3,ip
 vmovhi s0,ip
 pop {r4,pc}
1:
 vmov.f32 s0,#1.0
 pop {r4,pc}
.endm
guard_getter front
guard_getter back
