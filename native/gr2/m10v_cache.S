.syntax unified
.arm
.text
.balign 4
/* Stock MPU cache policy and physical DMA aliases still require hardware QA.
 * User tasks enter only through an identity-audited SVC5 callback branch or
 * the owned data-vector entry. With neither installation they fail closed. */
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
    mov r0,#0
    mcr p15,0,r0,c7,c6,0
    b .Lsuccess
.Ldrain:
    mov r0,#0
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
    beq .Linstalled
    ldr r1,=0xA00AF884
    ldr r1,[r1]
    ldr r2,=gr2_cache_svc_entry
    cmp r1,r2
    movne r0,#0
    bxne lr
.Linstalled:
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
    push {r1-r3,lr}
    mrs r1,cpsr
    and r1,r1,#31
    cmp r1,#19
    bne .Ldone
    ldr r1,=0x4D310001
    cmp r0,r1
    bne .Lsecond
    mov r1,#0
    mcr p15,0,r1,c7,c6,0
    b .Ldone
.Lsecond:
    add r1,r1,#1
    cmp r0,r1
    bne .Lthird
    mov r1,#0
    mcr p15,0,r1,c7,c10,4
    b .Ldone
.Lthird:
    add r1,r1,#1
    cmp r0,r1
    bleq .Lcode_sync_priv
.Ldone:
    pop {r1-r3,lr}
    bx lr
.size gr2_cache_gateway,.-gr2_cache_gateway
.ltorg

.balign 4
/* The original SVC dispatcher reads this handler address from its data table.
 * No callback instruction needs to be patched before first cache invalidation.
 * Preserve the original save/exception-return contract for all SVC5 callers. */
.global gr2_cache_svc_entry
.type gr2_cache_svc_entry,%function
gr2_cache_svc_entry:
    push {r0,lr}
    bl gr2_cache_gateway
    ldmia sp!,{r0,pc}^
.size gr2_cache_svc_entry,.-gr2_cache_svc_entry

.global gr2_code_sync
.type gr2_code_sync,%function
gr2_code_sync:
    push {r4,lr}
    ldr r4,=gr2_code_sync_status
    mov r0,#0
    str r0,[r4]
    mrs r1,cpsr
    and r1,r1,#31
    cmp r1,#16
    beq .Lsync_user
    cmp r1,#19
    cmpne r1,#31
    bne .Lsync_return
    ldr r0,=0x4d310003
    bl .Lcode_sync_priv
    b .Lsync_return
.Lsync_user:
    ldr r1,=0xA00AF884
    ldr r1,[r1]
    ldr r2,=gr2_cache_svc_entry
    cmp r1,r2
    bne .Lsync_return
    ldr r0,=0x4d310003
    svc #5
.Lsync_return:
    ldr r0,[r4]
    pop {r4,lr}
    bx lr
.size gr2_code_sync,.-gr2_code_sync

/* The exact original MPU setup uses nonbufferable region5 (A0000000..).
 * Refuse an unexpected bufferable/write-back policy rather than discard dirty
 * cache lines. CP15 behavior itself still requires real-device verification. */
.Lcode_sync_priv:
    mrc p15,0,r1,c3,c0,0
    tst r1,#32
    bxne lr
    mov r1,#0
    mcr p15,0,r1,c7,c10,4
    mcr p15,0,r1,c7,c5,0
    ldr r1,=gr2_code_sync_status
    mov r2,#1
    str r2,[r1]
    bx lr
.ltorg
