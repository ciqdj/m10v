# GR3 capture implementation and hardware debug candidate

User-authorized inline implementation. Preserve RAW+JPEG, full dimensions and all effects.

1. Lock prior device timings and current dirty checkout; retain existing unrelated GR4/bridge changes.
2. Implement independent, bounded native ISP parameter output writer. Never modify original cached Gamma objects or shared records. Test compiled ARM against original writers and object reuse. Production activation requires a per-frame backend decision and fidelity/ownership proof.
3. Generate stronger 5207/Phoenix color candidates with explicit input domain, provenance and heldout metrics. Keep complete color LUT for CPU fallback where native decomposition cannot preserve the target.
4. Integrate exact widening NEON blur only after ARM ABI and scalar equivalence tests. No replacement of existing spatial effects with unrelated stock grain or clarity.
5. Add call-owned save status tracing only at proven-safe boundaries; never perform filesystem logging recursively in save callbacks. Preserve original JPEG/save calls, fail paths and RAW ownership checks.
6. Rebuild source-bound SD contract and full debug firmware; run capture, rendering, ISP, log decoder, build/patch and artifact checks against final binary. Deliver configuration, FILMS.M10 export, hashes and scoped hardware test instructions.

Acceptance: no reduced image dimensions/bit depth, no effect disabled; stock mode/object reuse unchanged; full effects retained on fallback; distinguish CPU emulation, hardware parameters and real-camera timing. Device black-screen/file-loss resolution remains unverified until the user's new logs and file counts establish it.

## Follow-up after real f5ea39a0 precursor logs

Implemented and checked:
- Actual new device logs: build0ca2d5f3, 81 valid records, Phoenix27.893s (color/fused24.178s), then RAW0 skip and Gold15.264s. User confirmed recovery and matching DNG/JPG counts this run.
- Actual original Develop Still Make hook with exact SP and explicit source-recipe mapping; default observer changes no hardware parameters. Real still path stage0 is supported, not assumed stage1 fixture only.
- Producer snapshot after two original locks release; CPU consumes only validated observed snapshot with exact SI/tone. Queued UI edit and foreign-source tests pass.
- Actual recipe allocator/setter/allocator/release hooks, JPEG send-return/wait-return and callback payload/final service status hooks. No callback SD writes. Private trace ownership/free and optional allocation failure preserve original save semantics.
- f5ea39a0 candidate: runtime633688 bytes, 83 total audited patches including22 new lifecycle/snapshot hooks, original full image effects retained.

Pending objective, not marked complete:
- Exact full3D LUT and full spatial graph on original ISP/IIP with measured hardware pixel equivalence.
- Failure cancellation/DMA quiescence proof for a newly submitted graph. Real original ARM release can return after unsuccessful idle polls; no independent probe is activated on the photo path.
- Camera render/encode/file timing, concurrent buffer reuse/recovery, and old missing-photo reports verified with service traces and actual files. New package is a lifecycle/configuration debug candidate, not a latency fix claim.
