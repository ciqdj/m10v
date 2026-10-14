# m10v Final Multi-Model Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a polished local GR III/GR IV product in which every advertised latest-reference feature has a complete browser-to-domain workflow.

**Architecture:** Node owns the loopback origin, session authorization, model routing and immutable inputs. The pinned GR IV Python core remains authoritative for filter, crop, shutdown, calibration, toolchain, build and history behavior through a strict one-request worker; model-specific web modules sit inside a shared product shell. GR III keeps its independent exact-sample and fail-closed rules.

**Tech Stack:** Node.js 20, browser-native HTML/CSS/ES modules, CPython 3.12, Pillow 12.3.0, NumPy 2.5.3, rawpy 0.27.1, OpenCV headless 5.0.0.93, Capstone 5.0.9, Unicorn 2.1.4, LLVM/LLD.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-final-product-design.md`

## Global Constraints

- Pin GR IV behavior and assets to `gr-custom-tool` commit `549591db6ee7809fa7617c3637296ddc79b34f59`.
- Include the three bundled DNG samples and Lightroom bridge; record hashes for every vendored file.
- GR III candidate versions remain identical to the imported internal version.
- GR IV `1.11.10.7` first generates `1.11.10.10`; later builds use the matching local maximum plus one.
- Node is the only HTTP listener; bind only to `127.0.0.1` and require the session token for mutations.
- Never claim GR IV sample or hardware verification without a compatible user BIN and recorded result.
- Never expose automatic camera flashing or camera Flash/NAND recovery claims.
- Git commits and pushes are deferred until the repository-required publication choice after completion.

## Review Focus

- A visible button without a namespaced server route must fail the UI/API parity test in Task 4.
- A stale or modified vendored DNG/UI/native file must fail provenance in Task 1.
- A worker response that embeds a path outside the GR IV data root must fail before download in Task 3.
- Switching models with unsaved edits must warn and must not leak one model's state into the other in Task 5.
- Narrow viewports and long Chinese filenames/hashes must not create horizontal page overflow in Task 6.

---

### Task 1: Complete the pinned GR IV distribution snapshot

**Files:**
- Modify: `scripts/sync_gr4_reference.mjs`
- Modify: `vendor/gr4/PROVENANCE.json`
- Create: `vendor/gr4/web/**`
- Create: `vendor/gr4/gr4_editor/assets/calibration/samples/*.DNG`
- Modify: `node/adapters/gr4/provenance.test.mjs`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Produces: `verifyGr4Provenance(root) -> manifest` covering Python, native, web, Lightroom and calibration assets.
- Consumed by: Tasks 2, 4 and 7.

- [ ] **Step 1: Extend the failing provenance test** to require upstream web files, Lightroom scripts, three exact DNG filenames and hashes, while continuing to reject `gr4_editor/server.py` and runtime `data/`.
- [ ] **Step 2: Run** `node --test node/adapters/gr4/provenance.test.mjs`; expect failure for missing web/DNG entries.
- [ ] **Step 3: Extend** `scripts/sync_gr4_reference.mjs` to copy all distributable reference files deterministically, preserve the m10v worker, and emit file sizes plus hashes.
- [ ] **Step 4: Run the sync and focused provenance test**; expect one pass and a manifest pinned to `549591d`.
- [ ] **Step 5: Run** `(cd vendor/gr4 && ../../.venv/bin/python -m unittest discover -s tests -p 'test_*.py')`; record named fixture skips separately.

### Task 2: Expose the complete GR IV worker service

**Files:**
- Modify: `vendor/gr4/adapter_worker.py`
- Create: `node/adapters/gr4/operation-schema.mjs`
- Modify: `node/adapters/gr4/client.mjs`
- Modify: `node/adapters/gr4/client.test.mjs`
- Create: `node/adapters/gr4/operation-schema.test.mjs`

**Interfaces:**
- Produces: `client.request(operation, payload, workspace)` for status, settings, project, filters, XMP, icons, calibration, toolchain, crop, shutdown, build and history.
- Produces: `validateGr4Operation(operation, payload)` before spawning Python.
- Consumed by: Task 3.

- [ ] **Step 1: Write failing operation-schema tests** for every required operation, unknown fields, identifier traversal, oversized embedded data and model-crossed payloads.
- [ ] **Step 2: Run focused Node tests**; expect missing operation definitions.
- [ ] **Step 3: Write failing worker integration tests** using temporary workspaces for status/settings and malformed paths; assert exactly one JSON response.
- [ ] **Step 4: Implement the operation schema and worker dispatch** by calling reference `Editor` methods; binary bodies remain confined paths, never base64 in protocol JSON.
- [ ] **Step 5: Run focused tests and the applicable upstream service tests**; expect zero failures.

### Task 3: Build the namespaced GR IV HTTP facade and recovery flow

**Files:**
- Refactor: `node/gr4-runtime.mjs`
- Create: `node/gr4-routes.mjs`
- Create: `node/gr4-routes.test.mjs`
- Modify: `node/server.mjs`
- Modify: `node/server.test.mjs`

**Interfaces:**
- Consumes: Task 2 client operations.
- Produces: `handleGr4Request(context) -> boolean` below `/api/gr4/`.
- Produces: typed downloads resolved only from opaque project/build/hash identifiers.
- Consumed by: Task 4 UI transport.

- [ ] **Step 1: Write a failing route inventory test** covering status/settings, import, project get/save/import/export, filter add/remove/icon/XMP, crop preview, shutdown item/image/export, calibration state/register/run/output, toolchain, build, history/open/rollback, original and typed downloads.
- [ ] **Step 2: Run focused routes test**; expect missing routes.
- [ ] **Step 3: Write failing security tests** for missing token, wrong origin, excessive body, escaped ID, symlink artifact, mismatched original hash and worker-returned external path.
- [ ] **Step 4: Implement `gr4-routes.mjs` and reduce `server.mjs` to routing composition**; map reference results without weakening their validation.
- [ ] **Step 5: Add original-package backup metadata and project JSON import/export**; require the exact original SHA before restore/resume.
- [ ] **Step 6: Run route, server and full Node suites**; expect zero failures and only named optional fixture skips.

### Task 4: Port the complete GR IV editor UI into a product module

**Files:**
- Create: `web/gr4/index.html`
- Create: `web/gr4/app.js`
- Create: `web/gr4/calibration-ui.js`
- Create: `web/gr4/styles.css`
- Create: `web/shared/api.js`
- Create: `web/shared/dialogs.js`
- Create: `web/shared/evidence.js`
- Create: `node/ui-contract.test.mjs`

**Interfaces:**
- Consumes: Task 3 `/api/gr4/` facade.
- Produces: full GR IV browser workflow at `/gr4/` and exported `GR4_ACTIONS` route inventory.
- Consumed by: Tasks 5 and 6.

- [ ] **Step 1: Write a failing UI/API parity test** that extracts every actionable `data-operation` and proves it exists in the route inventory.
- [ ] **Step 2: Run** `node --test node/ui-contract.test.mjs`; expect missing GR IV product module.
- [ ] **Step 3: Port the pinned reference editor behavior** for filter, crop, shutdown, calibration, toolchain, project, build and history flows; change transport paths to `/api/gr4/` and remove standalone-server assumptions.
- [ ] **Step 4: Add original BIN backup/recovery actions and evidence labels** without changing GR IV domain behavior.
- [ ] **Step 5: Run the UI contract and full Node suites**; expect zero missing actions or routes.

### Task 5: Replace the test dashboard with a coherent multi-model shell and GR III workspace

**Files:**
- Replace: `web/index.html`
- Replace: `web/app.js`
- Replace: `web/styles.css`
- Create: `web/gr3/index.html`
- Create: `web/gr3/app.js`
- Create: `web/gr3/styles.css`
- Modify: `node/server.mjs`
- Modify: `node/ui-contract.test.mjs`

**Interfaces:**
- Consumes: Task 4 GR IV workspace and existing GR III APIs.
- Produces: `/` home, `/gr3/` workspace and navigation to `/gr4/`.

- [ ] **Step 1: Write failing shell tests** for product-home structure, model routing, exact GR III/GR IV version copy, evidence labels and absence of placeholder/test-platform language.
- [ ] **Step 2: Run the UI contract**; expect the old dashboard to fail.
- [ ] **Step 3: Implement the shared photographic-tool shell** with warm neutral tokens, black model rail, recent-project entry, compact evidence surface and responsive model tabs.
- [ ] **Step 4: Move the existing GR III workflow into `/gr3/`** while preserving all element contracts and fail-closed controls.
- [ ] **Step 5: Add unsaved-edit navigation guards** and model-isolated browser state; test that state does not cross workspaces.
- [ ] **Step 6: Run UI, server and full Node tests**; expect zero failures.

### Task 6: Rendered-product and interaction verification

**Files:**
- Create: `docs/testing/final-product-ui.md`
- Modify: UI files from Tasks 4 and 5 only when a rendered defect is reproduced.
- Add: focused regression tests for every repaired defect.

**Interfaces:**
- Consumes: running product from Tasks 1–5.
- Produces: screenshot and interaction evidence for desktop and narrow layouts.

- [ ] **Step 1: Start the final server** and inspect `/`, `/gr3/` and `/gr4/` in the in-app browser at desktop width.
- [ ] **Step 2: Exercise empty-state navigation, settings dialogs, import pickers, risk confirmation and history dialogs** without a firmware file; assert no console-visible or UI error.
- [ ] **Step 3: Import the supplied exact GR III file** and verify identity, report, backup, shutdown resources and locked candidate export.
- [ ] **Step 4: Inspect home and both workspaces at narrow width**; assert no horizontal overflow with long filenames and SHA-256 values.
- [ ] **Step 5: For each defect, add a failing contract test before fixing it**, rerun focused tests, then repeat the rendered check.
- [ ] **Step 6: Record screenshots, viewport sizes and untestable GR IV sample-only states** in `docs/testing/final-product-ui.md`.

### Task 7: Final integrity, documentation and handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/testing/gr4-reference-adapter.md`
- Modify: `.superpowers/sdd/2026-10-11-m10v-multimodel-foundation/progress.md`
- Review: all files changed by Tasks 1–6

**Interfaces:**
- Produces: a reproducible final release candidate and evidence-separated handoff.

- [ ] **Step 1: Run provenance sync/check** and confirm no unexpected sibling dependency or diff.
- [ ] **Step 2: Run `npm test` and the full applicable vendored Python suite**; capture exact pass/skip/fail counts.
- [ ] **Step 3: Verify Python 3.12 dependencies, LLVM detection behavior and startup from a clean process**; a missing LLVM may block build but must not block browsing/editing.
- [ ] **Step 4: Self-review every Review Focus item and the spec section-by-section**; repair findings through RED/GREEN cycles.
- [ ] **Step 5: Update documentation** with setup, model-specific version policies, backup scope, evidence labels and known absence of GR IV sample/hardware validation.
- [ ] **Step 6: Start the final service, open the final URL and leave it running for user review.**
- [ ] **Step 7: Present the repository publication menu required by `AGENTS.md`; do not create a commit or push until the user selects and confirms exact commands.**
