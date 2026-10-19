# Latest GR III device evidence and implementation

Input firmware SHA256: 080d7dc64c3262eb90c9bae61baa718dbd7f07453937e0d2d4c5be3404a7f002 (build 0ca2d5f3).
CP0 SHA256 7d044154fe4a8c85a1a66ea87437757383a9ed8ea1ff9035e8494cf2a56ac508; CP1 SHA256 7645ef222f5463eb84195bf22509d3ca09acd33ec4c13d90fcdb597de3ef5022.
Both pages CRC-valid; overlapping history reconstructs 81 records, no rejected/unmerged pages. Inputs copied read-only into ignored builds/gr3-third-shot-failure.

| Actual recorded film | Adapter milliseconds | Pre-spatial | Color/fused texture | Post-spatial |
|---|---:|---:|---:|---:|
|800T 33|13215|9567|3638|0|
|5207 66|28684|0|28681|0|
|Phoenix II 67|27893|1491|24178|2221|
|unidentified rejected task|0|not run|not run|not run|
|Gold 200 35|15264|0|15260|0|

All four rendered tasks have adapter exit. Following Phoenix, recipe 0x5c00d720 (context 0x5c00e0d8) rejects guard12 for RAW source0, length49678336; original encoder remains chained. Settings journal source/sequence380 remains unchanged. Phoenix/800T/Gold use the same Y/C plane addresses on separate tasks; this is reuse, not proof of simultaneous aliasing. Current logs do not cover encoding completion or file service status.

User additionally confirmed this run's black screen later recovered and final DNG/JPG counts matched. Therefore this run establishes long processing/recovery, not permanent deadlock or lost files. Historical lost-photo reports still need separate validation. Do not label RAW zero an allocation failure: stock ownership transfer can legally clear it.

Implementation in this turn:
- Extend proven recipe factory allocation for per-frame owned trace/config, with same allocator/free family and explicit no-FS hot hooks.
- Checked JPEG submit-return and wait-return tracing without relocating outgoing stack arguments or changing original wait/call.
- Optional caller-owned file trace: 16B outer stack extension stores optional656B heap pointer; synchronous callback payload preserved, flush only after original inner cleanup, then free. Allocation/clock failure continues original save.
- Independent IO CRC pages M10VIO0/1 retain lifecycle history separately from CP rendering timings. Decoder never equates adapter exit, transport return, or callback r0 with a durable JPEG/DNG file.
- ISP native color/graph work remains independently verified and not represented as full LUT/spatial hardware equivalence. Actual develop metadata uses stage0 in the traced path; stage1-only offline fixtures are insufficient to prove an installed still hook triggers.

Hardware save latencies/queue pressure and all-effects native ISP completion remain unverified. No reduced dimensions, effect-disable fallback, skipped RAW protection, altered buffer-release policy or invented timeout fix is used.

Additional implementation and constraints after user clarification:
- 22 installed, independently preimage-checked hooks:13 owned recipe diagnostics,2 JPEG borders,4 synchronous file-owner hooks,3 queue snapshot/ISP observer hooks. Recipe allocation0x50c0 (2376 additional bytes per recipe, including4 bytes alignment padding) retains all original object offsets; color extent1716 and trace656 bytes.
- Producer snapshots after the original RecipeManager and BE owner+a74 locks have released; never performs FS calls inside factory or ISP Make. CPU snapshot use requires observed status7 and exact ShootingInfo+tone identity. Source/destination recipe distinction is tested, not inferred by C-970.
- Original R2Y Still Make is called at original SP. Default observer leaves the entire0x9000 output byte-identical to stock, and complete CPU effects remain. Experimental applying color parameters is not activated in this candidate.
- The isolated SPF graph is implemented but NOT activated. Real original ARM release polls two driver busy states5002 times each, logs assertions on timeout, then returns success anyway; original failed assertion also returns. RAM quarantine alone does not prevent stale completion events affecting later photos. Independent module manifest sets hardware_activation_blocked/unsafe_on_failure true. This prevents calling an unproved full-effects hardware graph a complete fix.
- RAW44d0 is not an authoritative substitute for source0: target transfer overrides60 after setter computes44d0. Existing RAW guard remains. New capture.request.identity identifies the previously anonymous rejected task without guessing film IDs.
