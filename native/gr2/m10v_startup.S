.syntax unified
.arm
.text
.balign 4
.global gr2_startup_chain
.type gr2_startup_chain,%function
gr2_startup_chain:
    stmdb sp!,{r0-r12,lr}
    bl gr2_post_load
    ldmia sp!,{r0-r12,lr}
    mvn r0,#0
    adds r1,r0,#1
    ldr ip,1f
    bx ip
.balign 4
1:  .word 0xA0020ABD
.size gr2_startup_chain,.-gr2_startup_chain

/* Aligned GR II pre-JPEG site A02ADC98. r5 is the retained IMG owner,
 * r7 the image kind, and original sp+18 the complete 48-byte request.
 * Always replay the original JPEG call and post-call result load. */
.balign 4
.global gr2_jpeg_chain
.type gr2_jpeg_chain,%function
gr2_jpeg_chain:
    stmdb sp!,{r0-r3,ip,lr}
    mov r0,r5
    mov r1,r7
    add r2,sp,#48
    bl gr2_capture_frozen
    ldmia sp!,{r0-r3,ip,lr}
    add r0,sp,#24
    ldr ip,2f
    adr lr,3f
    bx ip
3:  ldr r0,[sp,#40]
    ldr ip,4f
    bx ip
.balign 4
2:  .word 0xA01324BB
4:  .word 0xA02ADCA1
.size gr2_jpeg_chain,.-gr2_jpeg_chain

/* Exact original producer prelude; callable independently of a future entry
 * interception, so the original body remains reachable without recursion. */
.thumb
.balign 4
.global gr2_producer_original
.type gr2_producer_original,%function
.thumb_func
gr2_producer_original:
    push {r4-r7,lr}
    movs r4,r0
    movs r5,r1
    sub sp,#180
    movs r1,#152
    ldr r3,5f
    bx r3
.balign 4
5:  .word 0xA02AD495
.size gr2_producer_original,.-gr2_producer_original

/* A0394950 follows the stock 16-byte PUSH. Preserve its provider/message and
 * original callee-saved register contract; consume private raw keys before
 * the state watchers queue converted SPEC events. All other events replay
 * the exact displaced prelude and original conditional continuation. */
.arm
.balign 4
.global gr2_ui_event_chain
.type gr2_ui_event_chain,%function
gr2_ui_event_chain:
    stmdb sp!,{r0-r3,ip,lr}
    mov r0,r1
    bl gr2_settings_raw_event
    cmp r0,#0
    ldmia sp!,{r0-r3,ip,lr}
    bne 7f
    mov r6,r0
    mov r5,r1
    mov r4,#0
    cmp r1,#0
    ldr ip,6f
    bx ip
7:  mov r4,#1
    ldr ip,8f
    bx ip
.balign 4
6:  .word 0xA0394959
8:  .word 0xA03949D3
.size gr2_ui_event_chain,.-gr2_ui_event_chain

/* The aligned A02AD48C site follows stock PUSH {r4-r7,lr}. Undo only that
 * prelude, then tail-enter the active C adapter with original SP/LR/r0/r1.
 * Its original-body trampoline bypasses this hook and preserves the return. */
.arm
.balign 4
.global gr2_producer_chain
.type gr2_producer_chain,%function
gr2_producer_chain:
    ldmia sp!,{r4-r7,lr}
    b gr2_producer_active
.size gr2_producer_chain,.-gr2_producer_chain

/* A03948C4 follows stock PUSH {r4-r6,lr}; r6 has already become zero.
 * Private routes finish at the original caller; ordinary routes replay the
 * displaced prelude and real tick getter before resuming stock conversion. */
.arm
.balign 4
.global gr2_menu_route_chain
.type gr2_menu_route_chain,%function
gr2_menu_route_chain:
    stmdb sp!,{r0-r3,ip,lr}
    bl gr2_settings_menu_route
    cmp r0,#0
    ldmia sp!,{r0-r3,ip,lr}
    beq 9f
    mov r0,#0
    ldmia sp!,{r4-r6,lr}
    bx lr
9:  mov r4,r0
    sub sp,sp,#16
    ldr ip,10f
    adr lr,11f
    bx ip
11: ldr ip,12f
    bx ip
.balign 4
10: .word 0xA0027D97
12: .word 0xA03948CD
.size gr2_menu_route_chain,.-gr2_menu_route_chain

.thumb
.balign 4
.global gr2_menu_categories_original
.type gr2_menu_categories_original,%function
.thumb_func
gr2_menu_categories_original:
    push {r0,r4-r7,lr}
    ldr r5,14f
    movs r6,#1
    sub sp,#16
    ldr r3,15f
    bx r3
.balign 4
14: .word 0xA0439790
15: .word 0xA03C1389
.size gr2_menu_categories_original,.-gr2_menu_categories_original

.thumb
.balign 4
.global gr2_menu_descriptor_original
.type gr2_menu_descriptor_original,%function
.thumb_func
gr2_menu_descriptor_original:
    push {r4-r7,lr}
    movs r7,r0
    movs r5,r1
    ldr r6,[r1,#20]
    ldr r0,[r1,#16]
    ldr r3,16f
    bx r3
.balign 4
16: .word 0xA039D171
.size gr2_menu_descriptor_original,.-gr2_menu_descriptor_original
.arm
.balign 4
.global gr2_menu_descriptor_chain
.type gr2_menu_descriptor_chain,%function
gr2_menu_descriptor_chain:
    ldmia sp!,{r4-r7,lr}
    b gr2_menu_descriptor
.size gr2_menu_descriptor_chain,.-gr2_menu_descriptor_chain

/* Tail of original startup: its finalizer has returned. Replay MOVS 0 and
 * POP {r4,pc} while retaining ARM/Thumb interworking and the original flags. */
.arm
.balign 4
.global gr2_finalize_chain
.type gr2_finalize_chain,%function
gr2_finalize_chain:
    push {ip}
    ldr ip,=gr2_startup_complete
    mov r0,#1
    str r0,[ip]
    pop {ip}
    movs r0,#0
    ldmia sp!,{r4,lr}
    bx lr
.size gr2_finalize_chain,.-gr2_finalize_chain
.ltorg
