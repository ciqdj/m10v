# GR III Universal Halation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver one identifiable GR III test package with optional universal halation and per-film camera controls.
**Architecture:** Compile-time capability selects mode-aware dispatch. Existing 800T/Phoenix kernels remain unchanged; a bounded generic kernel handles bloom and horizontal streaks. Reuse the current per-film journal and frozen capture state.
**Tech Stack:** Freestanding ARM C, Python build/audits, Node HTTP and browser JS.
**Spec:** docs/superpowers/specs/2026-10-26-gr3-universal-halation-design.md

## Global Constraints
- Backend write option defaults false, GR III only, requires film library.
- Enabled firmware defaults to off, including old nonzero halo settings.
- Camera modes: off / highlight spill / horizontal streak; mutually exclusive.
- Preserve special kernels and calling order; RAW ownership and existing features stay intact.
- Deliver test package only; camera acceptance is pending; no push or deployment.

## Review Focus
- Old journal values cannot silently enable new effects.
- Custom LUT workspace cannot alias spatial scratch.
- Shader-free disabled path must avoid spatial allocation.
- Existing per-capture snapshot and completion masks must apply to all modes.
- Turning off the build capability must ignore new saved modes safely.

### Task 1: Mode contract and rendering
**Files:** native/gr3/m10v_library.h, m10v_library.c, m10v_universal_halation.h (new), m10v_library_capture.c; tests/test_gr3_universal_halation.py (new).
**Interfaces:** M10V_UNIVERSAL_HALATION compile flag; profile 4=spill, 5=streak, 6=explicit off (also inactive without capability), old profiles 0..3=off in new capability; legacy builds retain old behavior and ignore profiles 4..5. No state size change. m10v_library_halation remains transactional setter.
- [x] Capture baseline outputs from both existing kernels and renderer.
- [x] Add tests for explicit modes, inactive legacy records, special output equivalence, generic bloom/streak, custom LUT, padding, preflight, completion masks and setter failures; run and observe failure.
- [x] Implement mode dispatch, bounded kernel and capture scratch contract; run host tests and ARM build.

### Task 2: Camera detail controls
**Files:** native/gr3/m10v_detail.c, scripts/build_gr3_native_detail.py, menu caption generator/resources; new mode menu tests.
**Interfaces:** Reuse retired detail field 4 / id22 for mode 0..2, provide Chinese captions and stock slider values; all film variants receive mode/gain/spread/threshold when capability enabled. Existing entrypoints unchanged.
- [x] Add failing menu dispatch/table/range tests.
- [x] Implement mode-aware callbacks, preserve profile during special gain edits, reset off, failure rollback; verify ARM/menu tests.

### Task 3: Backend and webpage capability
**Files:** scripts/build_gr3_m10v_library.py, node/gr3-native-library.mjs, node/gr3-m10v-native-build.mjs, node/server.mjs, web/gr3/studio.js, scripts/export_gr3_m10v_native.mjs; node/gr3-universal-halation.test.mjs (new).
**Interfaces:** halation_enabled boolean option; --universal-halation CLI; manifest and receipt universal_halation capability; fingerprint binding and independent readback.
- [x] Add failing plan/default/model/configuration-hash tests.
- [x] Thread capability through UI/HTTP/plan/build; initialize all halo gains to zero, bind source fingerprints and audit.
- [x] Verify relevant Node/UI and builder checks.

### Task 4: Candidate delivery
**Files:** docs/testing/2026-10-26-gr3-universal-halation.md; builds/gr3-universal-halation-20261026/ (ignored artifacts).
- [x] Run npm test and relevant Python/ARM regression; report pre-existing failures separately.
- [x] Fresh reviewer checks cumulative diff and special-mode equivalence; fix blocking findings.
- [x] Export using existing webpage build pipeline with capability enabled, package matching SD film pack, receipt, source/config fingerprints, SHA256 and recovery/test instructions.
- [x] Verify package contents and hashes; deliver WAITING_FOR_USER_VALIDATION.
