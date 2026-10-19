#ifndef M10V_IIP_GRAPH_H
#define M10V_IIP_GRAPH_H
#include <stdint.h>
/* Isolated GR III 2.10 register-image preparation. All destinations are ordinary
 * caller-owned RAM, NEVER MMIO. These operations do not submit IIP work, establish
 * scheduler ownership, implement an image effect, or prove hardware pixel math.
 * Firmware basis SHA256 8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67.
 * The three preparation functions return 0 or -1 before writing; caller supplies aligned, disjoint spans. */
/* Equivalent to original 0x5376c314's data loop only: sign-extended signed16
 * samples into 32-bit words, stride in signed16 samples (zero repeats a sample).
 * No cache maintenance: output must pass through original owner upload path. */
int m10v_iip_lut_words(uint32_t *dst,uint32_t dst_words,const int16_t *src,
    uint32_t src_samples,uint32_t count,uint32_t stride);
/* Equivalent to the original GPC setters at 0x53776ad0, b18..b60,
 * b68..bb0, bb8..c04, c08. 'element' values are RAW 20-bit encodings;
 * signedness/binary point and numerical meaning of shift/round codes are NOT
 * established. Higher bits are truncated exactly as the original setters do.
 * flags[0..3]: bit24 per element; flags[4]: 4-bit field at element0 bits28..31.
 * The remaining bits of the 64-byte original register image are preserved. */
int m10v_iip_gpc_patch(uint8_t *image,uint32_t bytes,uint32_t alpha,
    const uint32_t element[4],const uint32_t round[4],const uint32_t flags[5]);
/* Four original SPF 17-value banks: 0x5377ae18, af70, b0c8, b264.
 * Copies low13 bits to original halfwords 0x84+bank*0x40+2*i, preserving
 * high3 bits. These are encodings, NOT a claimed 17-tap geometry/kernel.
 * Image covers original 0x284-byte register image. */
int m10v_iip_spf_bank_patch(uint8_t *image,uint32_t bytes,uint32_t bank,
    const uint32_t values[17]);
/* Executable ORIGINAL Loader->Store operation at 0x53681260, matching the
 * call at 0x53685f38. This copies; it does not implement/substitute any effect.
 * Caller MUST already be the original processing-task owner of context,
 * rectangle, native 0x50-byte image descriptors and all planes, with exclusive
 * IIP access and established task NEON context. These lifetimes cannot be
 * proved from pointers. Original routine constructs/registers/submits its graph,
 * waits via context+0xc, releases graph resources, and maintains output cache.
 * It also uses ORIGINAL heap allocations. This wrapper acquires no new owner.
 * Currently admits only original format6 single-plane descriptors; rectangle
 * may be NULL. Source/destination descriptors are mutable native objects.
 * Returns -3 on hosts; -1 preflight; 0 original success; -4 original failure
 * possibly after partial output. No fallback effect may use partial output. */
int m10v_iip_original_copy_owned(uint32_t context,const void *rectangle,
    void *destination,void *source);
/* Exact ORIGINAL synchronous stage route used at 0x53503ab4. The native
 * 0x34-byte parameter object MUST come from the original task (0x5350304c
 * populates its settings): +4/+8 original image descriptors, +0x10 settings,
 * +0x2c native workspace, +0x30 workspace capacity. This wrapper deliberately
 * passes NULL r2 so execution cannot accidentally become a sizing query.
 * Caller is already original task owner with exclusive graph/planes/workspace
 * and VFP/NEON state. No new graph, event, allocation or cleanup is introduced;
 * each stock substage owns its original completion and release path. It neither
 * inserts custom nodes nor accelerates our CPU effects. It MUST NOT be called
 * recursively from a stock stage callback. -4 retains original failure semantics,
 * NOT a proof of idle/reset: caller must not retry/fallback on partial output.
 * Returns -3 host, -1 structural preflight, 0 original success, -4 failure.
 * Not installed in the capture pipeline by this isolated module. */
int m10v_iip_original_stage_owned(uint32_t context,void *parameters);
/* Isolated math PROBE. No photo-plane pointer is accepted or derived. Caller
 * provides a NEW exclusively owned, 16-byte-aligned 6144-byte buffer and a real
 * original IIP context, at a point where its previous graph has completed and
 * released units. NO allocation, file I/O or production hook is performed.
 * Caller must not reuse capture scratch or existing image storage as workspace.
 * One basis coefficient (raw13 encoding) and one center impulse (raw14) feed
 * ORIGINAL Loader->SPF->Store, lowpass flags0x1fb00/mode0 copied from
 * 0x5367a7c0..0x5367a810; tap geometry/scale remain unproved until CAMERA
 * output is measured. No test double generates pixels. On success, full 32x32
 * uint16 output is workspace+0x1000. Header uint32[0..10]: magic SFP1, version,
 * coefficient index, raw coefficient, impulse, result, submit return, FNV1a
 * of output bytes, minimum, maximum, count different from 0xa55a sentinel. Header[11..13]: nonzero count,
 * sparse count (max16), first maximum index. workspace+0x7c0 has sparse
 * uint32[16] records (value<<16)|linear_index. This identifies impulse tap
 * displacement while retaining full raw output; count>16 means truncation.
 * Failure may leave output partial. Caller owns all RAM until return; this API currently lacks a proven abort/
 * quiescence contract on failure. It MUST NOT be installed in a live photo
 * pipeline. On -4, retain/quarantine workspace and do not reuse the IIP context
 * until its original owner has established reset/idle. Release returning does
 * NOT prove idle: 0x5376ed74 polls 0x53778490 and 0x53778474 up to5002
 * times each; timeout branches0x5376f13c/0x5376f118 call assertion lines348/
 * 354, then CONTINUE release. 0x536b93d0 logs and returns via0x536b9598.
 * A native ARM test confirms release can clear graph+40/+9c and return1
 * while both status test doubles remain busy; no abort is established.
 * On success the caller can drain header/full output outside IIP task. NEVER perform SD I/O inside it.
 * Suggested caller boundary: 0x53681050 success (r0!=0), context remains sb;
 * this is after Granulation's wait and release, and is conditional on grain.
 * HARDWARE ACTIVATION IS BLOCKED: unsafe_on_failure=true. A quarantined
 * buffer alone does NOT make later photos safe on this same context.
 * This API is NOT safe to call from JPEG completion or with a library context.
 * Returns -3 on host, -1 preflight, 0 original completion, -4 original failure.
 */
#define M10V_IIP_SPF_PROBE_BYTES 6144u
int m10v_iip_spf_probe_owned(uint32_t context,void *workspace,uint32_t bytes,
    uint32_t coefficient_index,uint32_t coefficient_bits,uint32_t impulse);
#endif
