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

.arm
.balign 4
.global gr2_hdf_postprocess_chain
.type gr2_hdf_postprocess_chain,%function
gr2_hdf_postprocess_chain:
    b gr2_hdf_postprocess
.size gr2_hdf_postprocess_chain,.-gr2_hdf_postprocess_chain

.thumb
.balign 4
.global gr2_postprocess_original
.type gr2_postprocess_original,%function
.thumb_func
gr2_postprocess_original:
    push {r4-r7,lr}
    movs r4,r0
    sub sp,#0x6c
    movs r0,#0
    movs r1,#0xd
    ldr r3,.Lpostprocess_continue
    bx r3
.balign 4
.Lpostprocess_continue: .word 0xA02AF6D9
.size gr2_postprocess_original,.-gr2_postprocess_original

.arm
.balign 4
.global gr2_hdf_production_chain
.type gr2_hdf_production_chain,%function
gr2_hdf_production_chain:
    b gr2_hdf_production_begin
.size gr2_hdf_production_chain,.-gr2_hdf_production_chain

.thumb
.balign 4
.global gr2_production_original
.type gr2_production_original,%function
.thumb_func
gr2_production_original:
    push {r4-r7,lr}
    movs r4,r0
    movs r6,#0
    movs r0,#5
    sub sp,#0xac
    ldr r3,.Lproduction_continue
    bx r3
.balign 4
.Lproduction_continue: .word 0xA02ADEB1
.size gr2_production_original,.-gr2_production_original

/* Both sites are inside original preparation, after its stage6 lock. */
.arm
.balign 4
.global gr2_hdf_preparation_chain
.type gr2_hdf_preparation_chain,%function
gr2_hdf_preparation_chain:
    ldr r3,[sp],#4
    stmdb sp!,{r0-r12,lr}
    mrs r0,cpsr
    stmdb sp!,{r0,r1}
    mov r0,r4
    bl gr2_hdf_configuration_prepare
    ldmia sp!,{r0,r1}
    msr cpsr_fs,r0
    ldmia sp!,{r0-r12,lr}
    ldr lr,.Lpreparation_replay
    bx lr
.Lpreparation_replay: .word gr2_hdf_preparation_replay
.size gr2_hdf_preparation_chain,.-gr2_hdf_preparation_chain

.global gr2_hdf_reservation_chain
.type gr2_hdf_reservation_chain,%function
gr2_hdf_reservation_chain:
    ldr r3,[sp],#4
    stmdb sp!,{r0-r12,lr}
    mrs r0,cpsr
    stmdb sp!,{r0,r1}
    mov r0,r4
    bl gr2_hdf_reservation_required
    cmp r0,#0
    movne r0,#1
    strne r0,[sp,#28]
    ldmia sp!,{r0,r1}
    msr cpsr_fs,r0
    ldmia sp!,{r0-r12,lr}
    /* Preserve BL return to original AE842 for nonzero r5. */
    push {r3}
    ldr r3,.Lreservation_replay
    bx r3
.Lreservation_replay: .word gr2_hdf_reservation_replay
.size gr2_hdf_reservation_chain,.-gr2_hdf_reservation_chain

.thumb
.balign 4
.thumb_func
gr2_hdf_preparation_replay:
    movs r6,r4
    adds r6,#0xff
    movs r0,#9
    adds r6,#0xc1
    lsls r0,r0,#6
    ldr r1,[r6,#0x20]
    adds r0,r4,r0
    push {r3}
    ldr r3,.Lpreparation_continue
    mov lr,r3
    pop {r3}
    bx lr
.balign 4
.Lpreparation_continue: .word 0xA02AE805

.thumb_func
gr2_hdf_reservation_replay:
    pop {r3}
    cmp r5,#0
    beq .Lreservation_skip
    bx lr
.Lreservation_skip:
    push {r3}
    ldr r3,.Lreservation_continue
    mov lr,r3
    pop {r3}
    bx lr
.balign 4
.Lreservation_continue: .word 0xA02AE87F

.arm
.balign 4
.global gr2_hdf_policy_chain
.type gr2_hdf_policy_chain,%function
gr2_hdf_policy_chain:
    mov r1,r5
    mov r2,lr
    b gr2_hdf_clone_policy
.size gr2_hdf_policy_chain,.-gr2_hdf_policy_chain

.thumb
.balign 4
.global gr2_clone_policy_original
.type gr2_clone_policy_original,%function
.thumb_func
gr2_clone_policy_original:
    push {r3-r7,lr}
    movs r4,r0
    movs r0,#0xd
    lsls r0,r0,#6
    ldr r3,.Lpolicy_continue
    bx r3
.balign 4
.Lpolicy_continue: .word 0xA029DEC1
.size gr2_clone_policy_original,.-gr2_clone_policy_original
