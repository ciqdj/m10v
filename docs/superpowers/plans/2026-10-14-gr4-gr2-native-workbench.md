# GR IV / GR II Native Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Reverse-engineer the supplied official images and port the GR3 workbench through independently verified model interfaces.
**Architecture:** Keep the existing GR3 build intact. Reuse the GR4 reference decoder and shared film algorithms; implement a separate GR2 UNITY reader. Enable each writer only after its checksum and ABI contracts are proved.
**Tech Stack:** Node built-ins, Python, Capstone/Unicorn and LLVM already used by this repository.
**Spec:** docs/superpowers/specs/2026-10-14-gr4-gr2-native-workbench-design.md

## Global Constraints

- Execute GR IV → GR II; official inputs remain read-only and are never committed.
- Share semantic configuration, not fixed GR3 addresses or assumed image-buffer formats.
- Static JPEG processing; protect RAW CFA intervals. Hardware acceptance remains separately unverified.
- Preserve license/source provenance; public research without a reuse license supplies facts only.
- User explicitly authorized direct execution on 2026-10-14; no additional design or plan approval gates.

## Review Focus

- Corrupt or truncated containers must fail before exposing a writer.
- Inputs named as another model must be recognized from bytes, not filenames.
- Unknown versions must not receive known-address patches.
- Unsupported functions must never generate apparently successful firmware.
- Mixed model drafts must not apply one model's ABI or resources to another.

### Task 1: Reproducible GR IV inventory

**Files:** scripts/analyze_model_firmware.py, tests/test_model_firmware.py, docs/research/gr4-gr2-port-evidence.md.
**Interfaces:** `inspect_gr4(data: bytes) -> dict` emits hashes, versions, section rows, startup mapping and capabilities; CLI writes research JSON to a selected output directory.
- [ ] Write and run tests for exact GR4 identity, section sizes and malformed input; expected initial result: missing inspection function.
- [ ] Implement read-only inventory using the existing strict decoder and independent source identity checks.
- [ ] Run tests, analyze the supplied image and document verified interfaces versus research gaps; commit.

### Task 2: GR II UNITY decoder and updater analysis

**Files:** node/gr2-firmware.mjs, node/gr2-firmware.test.mjs, scripts/analyze_model_firmware.py, docs/research/gr4-gr2-port-evidence.md.
**Interfaces:** `inspectGr2(bytes)` gives exact identity, component inventory and resource rows; `readGr2Component(bytes,name)` yields decoded bytes. No unverified checksum writer is exported.
- [ ] Independently probe the official container, decode components, identify updater and checksum references.
- [ ] Write and run tests for record bounds, XOR involution, exact component hashes, corruption, identity and resource bounds; expected initial result: missing module.
- [ ] Implement strict parsing and model recognition; establish byte-exact unmodified decode/re-encode proof.
- [ ] Run tests and document executable architecture, resources and checksum evidence; commit.

### Task 3: Verified capabilities and model entry points

**Files:** node/adapters/gr2/index.mjs, node/adapters/gr4/index.mjs, node/server.mjs, model route tests and web model entry files.
**Interfaces:** model inspection/capability responses describe `can_build` per feature; GR4 uses its existing reference API, GR2 gets only proved operations.
- [ ] Write and run import/route tests for GR4, GR2 and unsupported identities; expected initial result: model capability unavailable.
- [ ] Implement model entry points and input handling without disturbing GR3 configuration or build routes.
- [ ] Run route and UI checks; commit.

### Task 4: GR IV native film/menu/image bridge

**Files:** native/gr4 model ABI/profile, scripts GR4 analysis/build files, model native-build tests, research evidence.
**Interfaces:** a model profile records original bytes and proved function contracts; a builder may consume it only when menu, storage, clock and capture contracts are established.
- [ ] Trace official menu/resource and static JPEG call chains, prove each candidate with disassembly and targeted execution.
- [ ] Write failing tests for the established contracts before implementing the model-specific native runtime.
- [ ] Integrate five slots, catalog/icons, persistence, grain/soft/halation/stamp through verified APIs; independently audit candidates and protected RAW ranges.
- [ ] Run focused native/API checks and update capability states only for proved functionality; commit.

### Task 5: GR II native film/menu/image bridge

**Files:** native/gr2 profile/runtime, GR2 build/audit modules, tests and research evidence.
**Interfaces:** follows Task 4's semantic contract with independently proved GR2 ABI, encoding, checksum and output filename.
- [ ] Trace GR2 program/resources and updater; establish checksum recomputation and image-buffer ownership.
- [ ] Write and run tests for verified contracts, then implement model-specific menu, state, image and clock integration.
- [ ] Decode and audit generated candidates, test all corrupt/unknown identity cases, update capabilities; commit.

### Task 6: End-to-end validation and documentation

**Files:** README.md, docs/testing model acceptance records, plan ledger.
- [ ] Run npm test and focused Python suites; record baseline/environment failures individually.
- [ ] Exercise model imports/builds and independent candidate readback; list feature parity and unresolved contracts explicitly.
- [ ] Review the whole change, fix material findings with failing regression tests, commit only task files. Do not merge, push, publish or operate a camera.
