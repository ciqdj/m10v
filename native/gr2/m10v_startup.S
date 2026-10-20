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
