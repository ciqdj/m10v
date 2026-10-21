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

.arm
.balign 4
.global gr2_hdf_core_chain
.type gr2_hdf_core_chain,%function
gr2_hdf_core_chain:
    b gr2_hdf_core
.size gr2_hdf_core_chain,.-gr2_hdf_core_chain

.global gr2_hdf_band_chain
.type gr2_hdf_band_chain,%function
gr2_hdf_band_chain:
    /* The cold12-byte band veneer preserves live r3 before using it. */
    ldr r3,[sp],#4
    stmdb sp!,{r0-r12,lr}
    mrs r0,cpsr
    stmdb sp!,{r0,r1}
    ldr r0,[sp,#8]
    mov r1,r4
    bl gr2_hdf_graph_curve
    str r0,[sp,#8]
    ldmia sp!,{r0,r1}
    msr cpsr_fs,r0
    ldmia sp!,{r0-r12,lr}
    /* Original function saved LR in its prologue and calls again below. */
    ldr lr,.Lband_replay
    bx lr
.Lband_replay: .word gr2_hdf_band_replay
.size gr2_hdf_band_chain,.-gr2_hdf_band_chain

.thumb
.balign 4
.global gr2_clarity_original
.type gr2_clarity_original,%function
.thumb_func
gr2_clarity_original:
    push {r0,r1,r4-r7,lr}
    movs r4,r0
    movs r0,#0
    sub sp,#0xdc
    str r0,[sp,#0xd8]
    ldr r3,.Lclarity_continue
    bx r3
.balign 4
.Lclarity_continue: .word 0xA014ADF9
.size gr2_clarity_original,.-gr2_clarity_original

.balign 4
.type gr2_hdf_band_replay,%function
.thumb_func
gr2_hdf_band_replay:
    add r1,sp,#0xa0
    str r0,[sp,#0xa0]
    movs r0,#1
    strb r0,[r1,#0xe]
    add r1,sp,#0x80
    strh r0,[r1,#0x30]
    push {r3}
    ldr r3,.Lband_continue
    mov lr,r3
    pop {r3}
    bx lr
.balign 4
.Lband_continue: .word 0xA014ACF9
.size gr2_hdf_band_replay,.-gr2_hdf_band_replay
