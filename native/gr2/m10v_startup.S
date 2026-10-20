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
