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
