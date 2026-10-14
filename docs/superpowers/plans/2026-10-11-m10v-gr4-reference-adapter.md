# GR IV Reference Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the public `gr-custom-tool` crop/shutdown editor as a model-isolated GR IV adapter while preserving its reference tests and version policy.

**Architecture:** Vendor a provenance-recorded snapshot of the GPL Python core and native sources, excluding its standalone server/UI/data. A Python 3.12 JSON-lines worker exposes the shared adapter protocol; a Node client enforces timeouts, message bounds and path confinement. Without a GR IV BIN, sample-level tests remain named skips.

**Tech Stack:** Node.js 20, CPython 3.12, Pillow 12.3.0, Unicorn 2.1.4, ARM LLVM/LLD.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-multi-camera-firmware-platform-design.md`

## Global Constraints

- Reference source is `/Users/zhaoo/Desktop/code/zhaoo/gr-custom-tool` at the captured Git commit; do not depend on that sibling path at runtime.
- Preserve GPL headers and record source SHA-256 values.
- Exclude the reference HTTP server, web UI, donation assets and local data.
- GR IV versions follow `.7` to `.10+`; GR III version policy is untouched.
- No real GR IV sample means `reference_verified`, not `offline_verified`.
- Do not perform Git writes; record proposed commits only.

## Review Focus

- Worker prints a warning before JSON: treat protocol as corrupt, never parse the last line; Task 2 test.
- Worker hangs after writing output: terminate the process group and reject the build; Task 2 test.
- Sibling reference repo changes after vendoring: provenance check detects drift without changing runtime; Task 1 test.
- GR IV build claims sample verification without an imported exact file: reject manifest normalization; Task 4 test.
- GR IV history requests a used or overflowed version: preserve reference rejection; Task 3 test.

---

### Task 1: Vendor the reference core with provenance

**Files:**
- Create: `vendor/gr4/PROVENANCE.json`
- Create: `vendor/gr4/requirements.txt`
- Create: `vendor/gr4/gr4_editor/**`
- Create: `vendor/gr4/tests/**`
- Create: `scripts/sync_gr4_reference.mjs`
- Create: `node/adapters/gr4/provenance.test.mjs`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Produces: a self-contained Python package and `verifyGr4Provenance(root, manifest)` helper used only by development checks.

- [ ] **Step 1: Write a failing provenance test** asserting source repository commit, explicit included-file hashes, excluded UI/server/data paths and GPL headers.
- [ ] **Step 2: Run the focused test** and confirm missing snapshot failure.
- [ ] **Step 3: Implement the deterministic sync script and vendor snapshot** using file copies through the script, not shell redirection; normalize only paths/import bootstrap required by the adapter package.
- [ ] **Step 4: Run provenance tests and the vendored Python reference suite**; expected zero failures and only existing fixture-dependent skips.
- [ ] **Step 5: Record deferred commit** `chore: vendor GR IV reference adapter core` with explicit `vendor/gr4`, script and notice paths.

### Task 2: Python JSON worker and hardened Node client

**Files:**
- Create: `vendor/gr4/adapter_worker.py`
- Create: `vendor/gr4/tests/test_adapter_worker.py`
- Create: `node/adapters/gr4/client.mjs`
- Create: `node/adapters/gr4/client.test.mjs`
- Create: `node/adapters/gr4/index.mjs`

**Interfaces:**
- Worker consumes one JSON request from stdin with schema `1`, operation and confined paths; emits exactly one JSON response and no other stdout.
- Node produces adapter methods `detect`, `inspect`, `capabilities`, `createDraft`, `validateDraft`, `previewCrop`, `prepareShutdownAsset`, `build`, `verify`, `rollback`, `outputFilename`.

- [ ] **Step 1: Write failing Python and Node protocol tests** for handshake, malformed JSON, extra stdout, stderr diagnostics, message over 1 MiB, timeout, nonzero exit, absolute-path escape and symlink input/output.
- [ ] **Step 2: Run focused suites** and confirm missing worker/client failures.
- [ ] **Step 3: Implement a one-request worker and spawn client** with a 60-second default operation timeout, bounded buffers, environment allowlist and process-group termination.
- [ ] **Step 4: Run both focused suites and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add hardened GR IV adapter bridge`.

### Task 3: GR IV drafts, features and version policy

**Files:**
- Create: `vendor/gr4/adapter_service.py`
- Create: `vendor/gr4/tests/test_adapter_service.py`
- Modify: `node/adapters/gr4/index.mjs`
- Modify: `node/platform/adapter-registry.test.mjs`

**Interfaces:**
- Consumes: reference `Editor` domain functions without starting its server.
- Produces: normalized crop/shutdown drafts, capability responses and `allocateVersion(source, ledger, requested)` behavior matching the reference.

- [ ] **Step 1: Write failing contract tests** for factory/custom crops, shutdown assets/items, 16-item limit, contain/cover, unknown fields, `.7` to `.10`, occupied versions, family mismatch and overflow.
- [ ] **Step 2: Run focused Python/Node tests** and verify normalized-contract failures.
- [ ] **Step 3: Implement the adapter service** by calling reference modules; do not duplicate firmware constants in Node.
- [ ] **Step 4: Run focused suites, the full reference suite and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: expose GR IV editor through adapter protocol`.

### Task 4: GR IV build, verify, history and rollback

**Files:**
- Modify: `vendor/gr4/adapter_service.py`
- Modify: `vendor/gr4/tests/test_adapter_service.py`
- Create: `node/adapters/gr4/build-contract.test.mjs`
- Modify: `node/platform/manifest.mjs`

**Interfaces:**
- Consumes: platform staging directory and GR IV draft/options.
- Produces: candidate `fwdc248b.bin`, adapter report, normalized manifest and rollback candidates with reference version allocation.

- [ ] **Step 1: Write failing tests** for mock exact-layout fixtures covering build/readback, canonical-base proof, version allocation, candidate tampering, history load, rollback and missing-real-sample evidence labels.
- [ ] **Step 2: Run focused tests** and verify build operations are absent.
- [ ] **Step 3: Wire reference build/history functions** into the worker; require `reference_verified` without a recognized user sample and reject any report claiming hardware verification.
- [ ] **Step 4: Run all Node, m10v Python and vendored GR IV suites** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add GR IV build and rollback adapter`.

### Task 5: GR IV adapter review gate

**Files:**
- Create: `docs/testing/gr4-reference-adapter.md`

**Interfaces:**
- Produces: an auditable statement of reference parity and the absence of sample/hardware evidence.

- [ ] **Step 1: Run the reference-vs-vendored provenance comparison** and record the source commit and intentional bridge-only additions.
- [ ] **Step 2: Run dependency and LLVM preflight checks** without persisting configuration on failure.
- [ ] **Step 3: Run all suites and list every skip by name**; do not count missing GR IV firmware tests as passes.
- [ ] **Step 4: Review normalized manifests and UI-facing capability JSON** for false sample/hardware claims.
- [ ] **Step 5: Self-review all Review Focus entries** and repair findings before starting the GR III editable plan.

