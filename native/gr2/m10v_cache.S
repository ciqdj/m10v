.syntax unified
.arm
.text
.balign 4
/* Stock MPU cache policy and physical DMA aliases still require hardware QA.
 * User tasks enter only through the identity-audited, installed SVC 5 callback.
 * Without that exact branch installation they fail closed. */
.global gr2_cache_before
.type gr2_cache_before,%function
gr2_cache_before:
    mov r0,#1
    b .Lcache
.size gr2_cache_before,.-gr2_cache_before
.global gr2_cache_after
.type gr2_cache_after,%function
gr2_cache_after:
    mov r0,#2
.Lcache:
    mrs r1,cpsr
    and r1,r1,#31
    cmp r1,#16
    beq .Luser
    cmp r1,#31
    cmpne r1,#19
    movne r0,#0
    bxne lr
    cmp r0,#1
    bne .Ldrain
    mcr p15,0,r0,c7,c6,0
    b .Lsuccess
.Ldrain:
    mcr p15,0,r0,c7,c10,4
.Lsuccess:
    mov r0,#1
    bx lr
.Luser:
    ldr r1,=0xA0044F4C
    ldr r1,[r1]
    ldr r2,=gr2_cache_gateway
    ldr r3,=0xA0044F54
    sub r2,r2,r3
    mov r2,r2,lsr #2
    bic r2,r2,#0xff000000
    orr r2,r2,#0xea000000
    cmp r1,r2
    movne r0,#0
    bxne lr
    ldr r1,=0x4D310000
    orr r0,r0,r1
    svc #5
    mov r0,#1
    bx lr
.size gr2_cache_after,.-gr2_cache_after
.balign 4
/* Stock A0044F4C is ARM BX LR. Original SVC 5 saves R0/LR, calls it,
 * then restores the caller via exception return. Preserve every register
 * for unrelated callers; the original dispatcher restores condition flags. */
.global gr2_cache_gateway
.type gr2_cache_gateway,%function
gr2_cache_gateway:
    push {r1}
    mrs r1,cpsr
    and r1,r1,#31
    cmp r1,#19
    bne .Ldone
    ldr r1,=0x4D310001
    cmp r0,r1
    bne .Lsecond
    mcr p15,0,r0,c7,c6,0
    b .Ldone
.Lsecond:
    add r1,r1,#1
    cmp r0,r1
    bne .Ldone
    mcr p15,0,r0,c7,c10,4
.Ldone:
    pop {r1}
    bx lr
.size gr2_cache_gateway,.-gr2_cache_gateway
.ltorg
