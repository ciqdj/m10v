# GR III Editable Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the exact GR III baseline adapter into a same-version editor for shutdown images and custom crop ratios with independent finished-file verification.

**Architecture:** Extend the existing strict parser and frame replayer behind the shared adapter interface. Resource editing lands first, followed by evidence-producing RTOS analysis and model-specific ARM patches for menu/crop registries. Every build is recreated from the immutable input and verified by a separate decoder.

**Tech Stack:** Node.js 20 ESM, CPython 3.12/Pillow for image normalization, ARM LLVM/LLD for evidenced native patches.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-multi-camera-firmware-platform-design.md`

## Global Constraints

- Only source SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4` is initially editable.
- All four internal/outer version copies remain `2.10.21.27`.
- No GR IV offset, instruction, registry or selector ID is accepted as GR III evidence.
- Unknown call chains block only the affected feature and are surfaced as exact capability blockers.
- Output is offline experimental firmware; no SD/camera action is added.
- Do not perform Git writes; record proposed commits only.

## Review Focus

- Image normalization changes dimensions/profile after preview: build must re-derive and compare asset hash; Task 1 test.
- Resource growth shifts a non-target record: reject unless the GR III resource-table verifier proves the new layout; Task 2 test.
- ARM patch lands on a half instruction or unexpected source word: reject before compilation output is used; Task 4 test.
- Crop patch affects JPEG but not DNG/RAW geometry: capability remains blocked until all required consumers are evidenced; Task 3 test.
- Candidate is valid but any version byte changed: independent verifier rejects; Task 5 test.

---

### Task 1: Shared image normalization for GR III assets

**Files:**
- Create: `python/m10v_images/__init__.py`
- Create: `python/m10v_images/worker.py`
- Create: `python/tests/test_images.py`
- Create: `node/platform/image-worker.mjs`
- Create: `node/platform/image-worker.test.mjs`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `normalizeShutdownImage({sourcePath, fit, width:720, height:480, outputPath}) -> {sha256, width, height, coding, previewPath}`.

- [ ] **Step 1: Write failing image tests** for PNG/JPEG/WebP/BMP/TIFF, EXIF orientation, alpha-to-black, contain/cover, decompression bounds, invalid/truncated images, deterministic output and preview/output hash agreement.
- [ ] **Step 2: Run Python and Node focused tests** and confirm missing worker failures.
- [ ] **Step 3: Implement a confined Pillow worker and Node client** with exact dependency pin `Pillow==12.3.0`, size/pixel limits and no metadata preservation.
- [ ] **Step 4: Run focused suites and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add deterministic GR III image normalization`.

### Task 2: Five-slot GR III shutdown resource builder

**Files:**
- Create: `node/adapters/gr3/shutdown.mjs`
- Create: `node/adapters/gr3/shutdown.test.mjs`
- Create: `node/adapters/gr3/resource-verify.mjs`
- Create: `node/adapters/gr3/resource-verify.test.mjs`
- Modify: `node/gr3-jpeg.mjs`
- Modify: `node/adapters/gr3/index.mjs`

**Interfaces:**
- Consumes: normalized 720×480 assets and existing `decodeFrameMap`/`repackWithTarget`.
- Produces: `readShutdownDraft(decoded)`, `applyShutdownDraft(decoded, draft)`, `verifyShutdownCandidate(source, candidate, draft)` for the five evidenced resources.

- [ ] **Step 1: Write failing tests** for all five official slots, replacement, rename/order draft rules, JPEG profile mismatch, record growth/shift, non-target resource changes and fresh candidate readback.
- [ ] **Step 2: Run focused tests** and confirm missing-module failures.
- [ ] **Step 3: Implement exact resource-record parsing and replacement**; preserve names/count/order and permit only layouts proved by the verifier.
- [ ] **Step 4: Run focused tests, `npm test` and the GR III resource probe** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: build verified GR III shutdown resources`.

### Task 3: Close GR III native crop and custom-menu evidence

**Files:**
- Create: `scripts/analyze_gr3_native_features.mjs`
- Create: `node/adapters/gr3/native-evidence.mjs`
- Create: `node/adapters/gr3/native-evidence.test.mjs`
- Create: `docs/research/gr3-native-feature-map.md`
- Modify: `scripts/analyze_gr3_rtos.mjs`

**Interfaces:**
- Produces: a machine-readable evidence map containing executable ranges, instruction mode, exact source words, callers, consumers, relocation/code regions, persistence fields and readback rules for crop and shutdown menu.

- [ ] **Step 1: Write failing evidence tests** requiring menu, persistence, JPEG, DNG/RAW, replay and shutdown-selection consumers plus full instruction boundaries and source hashes.
- [ ] **Step 2: Run the focused test** and confirm the current partial evidence is rejected with named missing consumers.
- [ ] **Step 3: Extend static analysis** using deterministic instruction/data cross-reference checks against the exact RTOS; emit no patch bytes and fail if any anchor differs.
- [ ] **Step 4: Run analysis twice and compare byte-identical JSON reports**; all mandatory evidence fields must be present before Task 4.
- [ ] **Step 5: Record deferred commit** `research: map GR III native feature paths`.

### Task 4: GR III native compiler and reversible patch registry

**Files:**
- Create: `python/m10v_gr3_native/__init__.py`
- Create: `python/m10v_gr3_native/toolchain.py`
- Create: `python/m10v_gr3_native/compiler.py`
- Create: `python/tests/test_gr3_native.py`
- Create: `node/adapters/gr3/native-client.mjs`
- Create: `node/adapters/gr3/native-client.test.mjs`

**Interfaces:**
- Consumes: Task 3 evidence map and normalized crop/shutdown drafts.
- Produces: `compileNativePatch({rtosPath, evidencePath, draftPath, outputPath}) -> PatchReport` with expected-before ranges and canonical restoration proof.

- [ ] **Step 1: Write failing compiler tests** for toolchain preflight, half-instruction rejection, unexpected source words, branch range, unresolved relocation, registry overflow, deterministic output and canonical restoration.
- [ ] **Step 2: Run focused Python/Node tests** and confirm missing compiler/client failures.
- [ ] **Step 3: Implement the minimal ARM compiler** by adapting only generic GPL toolchain mechanics; all addresses and expected words come from the GR III evidence map.
- [ ] **Step 4: Run focused suites and LLVM preflight** with zero failures; prove unapplying the report restores exact RTOS SHA.
- [ ] **Step 5: Record deferred commit** `feat: compile reversible GR III native feature patches`.

### Task 5: Same-version GR III build and independent verification

**Files:**
- Create: `node/adapters/gr3/build.mjs`
- Create: `node/adapters/gr3/build.test.mjs`
- Create: `node/adapters/gr3/verify.mjs`
- Create: `node/adapters/gr3/verify.test.mjs`
- Modify: `node/adapters/gr3/index.mjs`
- Modify: `node/candidate-verify.mjs`

**Interfaces:**
- Consumes: immutable official input, validated project draft, Task 2 resource output and Task 4 native patch output.
- Produces: adapter `build`/`verify` methods, candidate filename `fwdc239b.bin` and same-version report.

- [ ] **Step 1: Write failing build/verifier tests** for no-op exactness, shutdown-only, crop-only, combined features, all checksum layers, fresh decode, version invariance, fifth-byte tampering and malformed frames.
- [ ] **Step 2: Run focused tests** and verify missing operations fail.
- [ ] **Step 3: Implement ordered composition** from the immutable decoded baseline, repair only evidenced checksums, frame-repack once and keep all four version words unchanged.
- [ ] **Step 4: Run focused tests, `npm test`, Python suites and all GR III analysis scripts** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: generate same-version GR III firmware candidates`.

### Task 6: GR III adapter review gate

**Files:**
- Create: `docs/testing/gr3-editable-adapter.md`
- Modify: `docs/testing/gr3-local-workbench.md`

**Interfaces:**
- Produces: exact offline evidence for the shipped GR III adapter, separated from hardware acceptance.

- [ ] **Step 1: Generate no-op and each feature combination in temporary directories**; record hashes, sizes and manifests without writing an SD card.
- [ ] **Step 2: Independently decode each candidate** and compare every non-target byte/range and all four version words.
- [ ] **Step 3: Run fault injection** for build, verify and publication stages and prove no partial downloadable build.
- [ ] **Step 4: Review every hardware-facing statement** and keep `hardware: not_tested`/no recovery guarantee.
- [ ] **Step 5: Self-review all Review Focus entries** and repair findings before product integration.

