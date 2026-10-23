// Seven sparse style LUTs (70,875 bytes), icons (44,800 bytes), and full
// native preview curves extend the previous 960 KiB bounded allowance.
// Basic SD runtime: 991,192 bytes RTOS growth, end 0x541a7598.
// Every final configuration still requires fresh section, instruction, full
// read-only MMU mapping and non-target-byte audits; this is no device proof.
// 1088 KiB is a finite ceiling, checked again after all-feature builds.
export const MAX_NATIVE_RTOS_GROWTH=1088*1024;
