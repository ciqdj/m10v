# GR III / GR IIIx Feature Parity Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task.

**Goal:** Give GR III and IIIx the same features, configuration and native ISP pipeline.
**Architecture:** Shared runtime and product capability contract; exact-model differential port preserves CPU and identity. Parameterize only lens geometry in the existing focal module.
**Tech Stack:** Node ESM, Python, ARM C/assembly, native LLVM and Unicorn.
**Spec:** docs/superpowers/specs/2026-10-27-gr3-gr3x-feature-parity-design.md (approved by user: 同步一下，要求一模一样).

## Global Constraints

Keep exact official identities, CPU sections, protected words, storage ABI, ordinary-film zero-pixel-work and independent per-camera device acceptance. No push, merge or deployment before candidate validation. GR III remains 28–50mm (current source contract); IIIx uses its 40mm lens and 50/71mm stock defaults, with 40–71mm editor. Native crop geometry must use the matching lens base.

## Review Focus

- Model switches retain selected effects and ten slots without silently dropping settings.
- IIIx grain/new filters use real ISP Still Make and completion admission.
- IIIx crop ratios, labels and metadata reflect 40mm, never 28mm.
- Image resource replacements preserve all unrelated bytes including IIIx CPU.
- Stale approvals and invalid camera-specific crop input remain rejected.

### Task 1: Shared pipeline and capability contract
Files: web/gr3/model-capabilities.mjs, node/gr3-native-library.mjs, node/gr3-integrated-components.mjs, node/gr3-model-parity.test.mjs.
- [x] Add failing tests comparing plan fields for both exact official models, including ten slots, new films, grain, HDF, halation and standalone HDF.
- [x] Run node --test node/gr3-model-parity.test.mjs and observe old IIIx gates fail.
- [x] Share capabilities and remove obsolete model gates while preserving invalid combination checks and fingerprint binding.
- [x] Run focused preflight tests and inspect actual manifest/receipt contracts.

### Task 2: Model-aware focal runtime
Files: native/gr3/m10v_zoom*, scripts/build_gr3_zoom.py, scripts/build_gr3_m10v_library.py, node/gr3-zoom.mjs, web/gr3/native-library-state.mjs, tests/test_gr3x_zoom.py.
- [x] Add failing host tests for every integer IIIx focal ratio, 50/71 defaults, transactional persistence, marker and image geometry.
- [x] Parameterize existing C/assembly and builder with --camera-model, keeping GR III default byte semantics and resource IDs.
- [x] Bind model, lens base, range and seed into manifest/readback checks; run host and ARM focal checks.

### Task 3: Both web editors and power images
Files: web/gr3/studio.js, native-library.js, zoom-controls.mjs, power-images.js; node/gr3-power-images.mjs; related UI and resource tests.
- [x] Add failing tests for same controls, preserved selections on model switch and IIIx resource replacement.
- [x] Consume shared capabilities, validate model-specific lens range, enable IIIx image resources with existing independent full readback.
- [x] Verify source identity and CPU preservation after image replacement; retain bridge/version adapters.

### Task 4: Candidate verification and delivery
Files: scripts/check_gr3x_release.mjs, candidate builds under builds/, docs/testing/gr3-gr3x-parity-20261027.md.
- [x] Update obsolete IIIx-specific rejection tests to the approved shared behavior.
- [x] Run npm test and focused Python/ARM suites; compare unrelated failures with base, recording names. Final clean-runtime comparison completed: candidate400/359pass/32fail/9skip; base381/340pass/32fail/9skip; same32 failure names.
- [x] Build both native candidates and combined HDF/halation/ten-slot variants; verify final BIN section bytes and real ISP admission on each output.
- [x] Package separately with matching FILMS.M10, receipts, provenance, SHA256 and device checklist; report WAITING_FOR_USER_VALIDATION.

## Execution ledger

- Existing isolated worktree retained; branch daily/gr3-gr3x-parity-20261027 created at aa9207f.
- Exact official inputs restored locally from the primary checkout; ignored binary files stay outside Git.
- Ruling: execute inline without another planning approval — user explicitly instructed synchronization after reviewing the design.
- Production SHA has not been queried; no production mutation is part of candidate delivery.

- Review: independent agent found and closed draft-state overwrite and nominal71 stock-encoding issues; no remaining P1/P2.
- Ruling: preserve stock enum6 ratio0x3fe49249 for IIIx nominal71, proven by original writer/reader literals and final ARM roundtrip.
- Final combined candidates: GR3 build7875062f, GR3x buildd3a06c1b; camera validation pending.

- Final verification: Node64/64, HTTP1/1, III finalBIN22/22, IIIx finalBIN19/19; focal37pass/1skip. ZIP inventory and every SHA256 verified.
- Delivery state: WAITING_FOR_USER_VALIDATION; no merge/push/deployment.
