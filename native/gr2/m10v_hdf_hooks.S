.syntax unified
.text
.arm
.balign 4
.global gr2_hdf_layout_chain
.type gr2_hdf_layout_chain,%function
gr2_hdf_layout_chain:
    /* The cold14-byte veneer saved the live incoming fourth argument. */
    ldr r3,[sp],#4
    b gr2_hdf_buffer_layout
.size gr2_hdf_layout_chain,.-gr2_hdf_layout_chain

.thumb
.balign 4
.global gr2_buffer_layout_original
.type gr2_buffer_layout_original,%function
.thumb_func
gr2_buffer_layout_original:
    push {r0-r7,lr}
    movs r5,r0
    movs r7,r3
    sub sp,#4
    ldr r3,.Llayout_getter
    bl .Llayout_call
    movs r4,r0
    ldr r3,.Llayout_continue
    bx r3
.Llayout_call:
    bx r3
.balign 4
.Llayout_getter: .word 0xA00DFDFF
.Llayout_continue: .word 0xA00E5DA1
.size gr2_buffer_layout_original,.-gr2_buffer_layout_original
