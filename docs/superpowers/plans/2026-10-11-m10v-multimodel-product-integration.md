# Multi-Model Product Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete shared editing, backups, history, rollback, downloads, toolchain settings and responsive UI for the finished GR III and GR IV adapters.

**Architecture:** Thin HTTP controllers expose shared domain services; adapter capability data controls model-specific fields. Official-package backup, edit backup and candidate downloads use separate schemas/routes. The UI presents one workflow with accurate evidence labels rather than duplicating pages per model.

**Tech Stack:** Node.js 20 ESM, browser HTML/CSS/JavaScript, CPython 3.12 adapter workers.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-multi-camera-firmware-platform-design.md`

## Global Constraints

- GR III has no editable version field; GR IV exposes suggested/legal reference versions.
- Official backup, edit backup and candidate firmware never share routes or archive kinds.
- Downloads resolve only ledger-backed completed builds.
- No automatic SD or camera write for candidates.
- Evidence labels come from backend manifests, not UI inference.
- Do not perform Git writes; record proposed commits only.

## Review Focus

- A GR IV draft is imported into a GR III project with the same title: reject by adapter/input identity; Task 1 test.
- A completed build file is replaced after ledger registration: download rehashes and rejects; Task 3 test.
- History contains a missing parent or cycle: show a corrupt-history error and disable rollback; Task 2 test.
- Backup includes a candidate path or absolute path: reject before extraction; Task 1 test.
- Browser refresh during build retries POST: idempotency returns the original build or a conflict, never a second build; Task 3 test.

---

### Task 1: Distinct official and edit backup workflows

**Files:**
- Create: `node/platform/edit-backup.mjs`
- Create: `node/platform/edit-backup.test.mjs`
- Modify: `node/backup.mjs`
- Modify: `node/backup.test.mjs`
- Modify: `node/platform/project-service.mjs`

**Interfaces:**
- Produces: `exportOfficialBackup(objectSha)`, `restoreOfficialBackup(zip)`, `exportEditBackup(projectId)`, `restoreEditBackup(zip, objectSha)` with distinct `kind`/schema.

- [ ] **Step 1: Write failing tests** for both round trips, cross-kind rejection, wrong input SHA, asset hashes, duplicates, traversal, symlinks, excessive sizes, absolute paths and candidate/build references.
- [ ] **Step 2: Run focused tests** and confirm edit-backup functions are missing.
- [ ] **Step 3: Implement strict archive schemas and atomic restore**; preserve the official computer-only recovery statement.
- [ ] **Step 4: Run focused tests, `npm test` and Python backup tests** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: separate official and edit backups`.

### Task 2: Cross-model build history and rollback service

**Files:**
- Create: `node/platform/history.mjs`
- Create: `node/platform/history.test.mjs`
- Modify: `node/platform/store.mjs`
- Modify: `node/platform/project-service.mjs`

**Interfaces:**
- Produces: `historyForProject(id)`, `openBuild(buildId)`, `loadBuildAsProject(buildId)`, `rollback(projectId, targetBuildId, options)`.

- [ ] **Step 1: Write failing tests** for linear ancestry, missing/cyclic parents, adapter mismatch, deleted files, GR III same-version rollback and GR IV higher-version rollback.
- [ ] **Step 2: Run focused tests** and confirm missing history service failure.
- [ ] **Step 3: Implement ledger graph validation and adapter-delegated rollback**; never infer ancestry from equal version labels.
- [ ] **Step 4: Run focused tests and all suites** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add adapter-safe firmware history and rollback`.

### Task 3: Build, manifest and download HTTP APIs

**Files:**
- Modify: `node/platform/routes.mjs`
- Modify: `node/platform/routes.test.mjs`
- Modify: `node/server.mjs`
- Modify: `node/server.test.mjs`

**Interfaces:**
- Produces: POST project save/build/rollback/backup routes and GET ledger-backed firmware/manifest/history routes with bounded opaque IDs.

- [ ] **Step 1: Write failing HTTP tests** for idempotent build keys, stale project revisions, authorization, model/version options, rehash-on-download, missing files, incomplete builds and route-kind separation.
- [ ] **Step 2: Run HTTP tests** and verify expected missing routes.
- [ ] **Step 3: Implement controllers** using services only; stream completed files with fixed names `fwdc239b.bin` or `fwdc248b.bin` and `nosniff`/`no-store` headers.
- [ ] **Step 4: Run syntax checks and all suites** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: expose verified multi-model build APIs`.

### Task 4: Unified multi-model editor UI

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `node/server.test.mjs`

**Interfaces:**
- Consumes: adapter/project/capability/history/build APIs.
- Produces: one responsive UI for import, crop, shutdown, save, build, backups, history, rollback, downloads and evidence labels.

- [ ] **Step 1: Write failing page-contract tests** for adapter/model labels, GR III hidden version field, GR IV suggested version, unsupported GR II, separate backups, busy/error states and hardware-evidence copy.
- [ ] **Step 2: Run page tests** and confirm old GR III-only markup fails.
- [ ] **Step 3: Implement semantic HTML and state reducer**; split `web/app.js` into `web/api.js`, `web/state.js`, `web/editor.js` if it would otherwise exceed 500 lines.
- [ ] **Step 4: Run `node --check` and page tests** with zero failures.
- [ ] **Step 5: Start the local server and verify actual rendering/interactions** at approximately 390px, 768px and 1365px widths; capture screenshots and correct overflow/focus/errors.
- [ ] **Step 6: Record deferred commit** `feat: add unified GR III and GR IV editor UI`.

### Task 5: Launchers, dependencies and toolchain settings

**Files:**
- Create: `launcher.py`
- Create: `start.sh`
- Create: `start.cmd`
- Modify: `requirements.txt`
- Modify: `package.json`
- Modify: `.gitignore`
- Create: `python/tests/test_launcher.py`
- Create: `node/platform/toolchain-routes.test.mjs`

**Interfaces:**
- Produces: deterministic Python 3.12 environment preparation, Node server launch and adapter/toolchain status/save operations.

- [ ] **Step 1: Write failing launcher/toolchain tests** for exact dependencies, 64-bit Python 3.12, spaces in paths, occupied ports, failed install/preflight, separate LLD and no configuration write on failure.
- [ ] **Step 2: Run focused tests** and confirm missing launcher behavior.
- [ ] **Step 3: Implement launchers and toolchain routes** by adapting the reference bootstrap while making Node the only HTTP server; ignore `.venv`, local data, temporary adapter output and generated builds without ignoring source fixtures.
- [ ] **Step 4: Run launcher checks, LLVM preflight and all suites** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add multi-runtime launcher and toolchain setup`.

### Task 6: Documentation and final verification

**Files:**
- Modify: `README.md`
- Create: `docs/USAGE.md`
- Modify: `THIRD_PARTY_NOTICES.md`
- Verify unchanged: `LICENSE`
- Create: `docs/testing/multimodel-final.md`

**Interfaces:**
- Produces: user-facing installation, supported-input, editing, backup, build, history, risk and evidence documentation matching runtime behavior.

- [ ] **Step 1: Update docs** with exact GR III/GR IV differences, Python/LLVM requirements, output filenames, version policies, backup kinds and no-hardware-guarantee language.
- [ ] **Step 2: Run every command in the roadmap completion gate** and record exit status, pass/fail/skip counts and tool versions.
- [ ] **Step 3: Re-run full browser workflows** from clean temporary data for GR III and reference-only GR IV state; verify visible copy against backend reports.
- [ ] **Step 4: Run scoped whitespace, license/provenance and secret scans**; inspect repository status without staging.
- [ ] **Step 5: Perform whole-program self-review** against this plan, the other phase Review Focus lists and the design completion criteria; fix findings with RED/GREEN cycles.
- [ ] **Step 6: Record proposed final commit set** and present the repository-required publication menu; do not execute Git commands before confirmation.
