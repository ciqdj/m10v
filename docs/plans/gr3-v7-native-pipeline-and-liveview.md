# GR III V7: native pipeline and view recovery

User update2026-10-19: slot sequence800T,5207,Phoenix,RED,Gold200. First two responsive; Phoenix briefly black and recovers; RED/Gold remain black until half-press. User asks for end-to-end outcome, native effect reconstruction rather than preserving old CPU arithmetic at all costs. Preserve full photo resolution/quality, RAW, selected effects and visual character. Previous requirement to preserve byte-identical old arithmetic is superseded as an engineering gate; visually meaningful differences must be measured and calibrated, never silently drop a feature.

Evidence: exact V6 a50f5139 firmware,152 CRC-valid records, no rejected pages.5207 color25.590s(prefix partly overwritten),Phoenix24.539s(total; color20.743s),RED10.156s,Gold4.934s. All three LUT captures batch24MP/cache selected; bypass regression fixed. Gold main Store01000001 returns1 and Store return clock105375ms, not durable-media proof. This and half-press recovery require separate UI/LiveView ACK-state investigation.

Implementation tracks:
1. Original LiveView request/ACK/completion/QuickReview exit chain. Demonstrate transitions in original ARM, preserve still-save ownership. Fix only with identified missing/stale transition; never inject shutter events or blindly clear busy flags.
2. Native color profiles for all supported slot films, per-shot state/identity. Apply original frame writers after actual Still Make. A downstream completion mask prevents CPU color double application and explicitly identifies remaining software stages.
3. Native spatial effects use original owner graph/workspace/submit/wait/cleanup. Reconstruct grain/soft/halo/leak in native primitives; retain necessary bounded CPU field generation. No independent asynchronous graph without owner, guessed formats, disabled effects, or forced RAW free.
4. Renderer consumes verified completed stages; uncompleted effects remain active. Host/ARM tests cover partial completion, identity mismatch, original-mode isolation, failure/transaction rollback, unchanged raw/save calls, and full-resolution stride/capacity.
5. Integrate only substantiated paths, verify actual delivered firmware, and package only after material behavior improvement. Physical playback, effect appearance, sustained burst and JPEG/DNG integrity remain camera acceptance criteria; no local test claims them complete.

Architecture decision: synchronous24MP CPU rendering cannot meet native responsiveness. Continue CPU baseline for validation but do not publish another percent-only optimization as core resolution. Hardware-color and GUI recovery need independent proofs, then one integrated capture path. Native grayscale grain is not complete colored grain; negative Clarity is not the whole halo/leak model.
