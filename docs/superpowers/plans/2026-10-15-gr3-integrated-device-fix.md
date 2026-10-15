# GR III integrated device fix implementation plan

**Goal:** Fix ADJ private-tone leakage and date-dependent capture abort, then deliver one audited experimental GR III firmware with the native library, 800T controls, grain, timestamp, aspect and slider level.

**Spec/evidence:** `docs/research/gr3-device-regression-2026-10-15.md`, followed by the user's explicit request to implement that repair order and generate a camera test candidate.

**Architecture:** Native runtime owns the five-slot state, film selection and JPEG processing. Reuse the verified aspect/level implementation as explicit optional components, with disjoint code allocation and exact patch ownership. Build from the official baseline once, validate every final section and preserve all selected options across UI tabs.

**Constraints:** Preserve existing uncommitted 800T changes. No private IDs enter stock tone storage. Clock failure must not suppress unrelated effects; no invented timestamps. Final receipt binds configuration, component sources, final bytes, hook counts and hardware-test limitations. No deployment/flash. Work in current checkout so existing native changes remain included.

## Tasks

- [x] ADJ: add failing real ARM callback regression; protect ADJ list and all global index consumers; keep MENU library reachable; verify boundary/cancel behavior.
- [x] Capture: add failing clock-unavailable and invalid-date combination tests; separate grain seed from date availability; use a verified date source or skip timestamp only with diagnostics; validate full render reaches pixels.
- [x] Composition: inspect existing aspect/level patches and extensions; add failing configuration and final binary conflict/tamper tests; assemble one final candidate with exact source/component provenance and memory mapping checks.
- [x] UI/API: preserve the native film selection when toggling aspect/level/negative grain; carry options through prepare/build hashes and receipts; reject unsupported/conflicting combinations explicitly.
- [x] Verification: run focused ARM tests, native host tests, Node suites, final candidate machine-code tests and configuration readback. Verify debug and non-debug paths and selected/unselected feature combinations.
- [x] Delivery: write fwdc239b.bin, configuration, build receipt, SHA256, logging decoder output contract, and specific camera test checklist into a new builds folder. Keep input originals intact.

## Review focus

- Main MENU vs ADJ share model functions but not callbacks.
- Date getter failure and invalid dates must leave other render effects running.
- Aspect extension and native module must never occupy the same addresses or overwrite one another's resource hooks.
- Existing persistent M10V state overrides firmware defaults; delivery must state how to select actual test values.
- GR IIIx cannot silently receive GR III-only component patches.

## Delivery evidence

Final candidate: `builds/gr3-integrated-device-test/fw/fwdc239b.bin`, SHA256 `0fa862bd06991537332eba52b7bb310f94f9bf346e3acc54daa3530a6ce9c02a`, debug build `0607500c`. See that folder’s Chinese camera-test guide and verification record. 94 native/ARM tests, final artifact ADJ9/capture9/resources2, and16 debug/release extension compositions passed. Hardware acceptance and imaging remain pending.
