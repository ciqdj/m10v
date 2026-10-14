/* Research call seam for the explicit software ABI, NOT a camera descriptor
 * adapter. No firmware address, original call, or injection site is patched. */
.syntax unified
.arm
.text
.global m10v_halation_preserving
.type m10v_halation_preserving,%function
m10v_halation_preserving:
    push {r0-r12,lr}
    mrs r12,cpsr
    sub sp,sp,#8
    str r12,[sp]
    bl m10v_halation
    ldr r12,[sp]
    msr APSR_nzcvqg,r12
    add sp,sp,#8
    pop {r0-r12,pc}
.size m10v_halation_preserving,.-m10v_halation_preserving
