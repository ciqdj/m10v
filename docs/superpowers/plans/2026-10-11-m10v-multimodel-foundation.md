# Multi-Model Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the GR III-only server/storage assumptions with a versioned adapter registry, isolated model projects and atomic build transactions without changing existing GR III read-only behavior.

**Architecture:** Small Node modules own adapter contracts, registry selection, immutable objects, editable projects and build publication. The existing GR III parser is wrapped, not rewritten. HTTP routes switch from SHA-as-project-ID to opaque project IDs while retaining a compatibility lookup during migration.

**Tech Stack:** Node.js 20 ESM and `node:test` with no new npm dependencies.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-multi-camera-firmware-platform-design.md`

## Global Constraints

- Adapter schema is exactly version 1 and responses are JSON-safe.
- Input objects are addressed by SHA-256; editable projects use opaque IDs.
- Existing GR III official import, analysis, backup and official SD tests stay green.
- GR II is registered as unsupported metadata only and has no detector.
- Do not perform Git writes; record the proposed commit only.

## Review Focus

- Two adapters claim the same input: reject as ambiguous; Task 1 test.
- A detector throws on arbitrary bytes: continue only for explicit non-match, reject corruption; Task 1 test.
- Project adapter differs from object adapter: reject before reading draft assets; Task 3 test.
- Build verifier fails after a candidate was staged: remove only owned staging and publish nothing; Task 4 test.
- Legacy SHA project route points to two drafts: require explicit project ID; Task 5 test.

---

### Task 1: Versioned adapter contract and unique registry

**Files:**
- Create: `node/platform/adapter-contract.mjs`
- Create: `node/platform/adapter-registry.mjs`
- Create: `node/platform/adapter-registry.test.mjs`
- Create: `node/adapters/gr2/index.mjs`
- Create: `node/adapters/gr3/index.mjs`
- Modify: `package.json`

**Interfaces:**
- Produces: `validateAdapter(adapter) -> adapter`, `createRegistry(adapters) -> {detect(bytes), get(id), list()}`.
- `detect(bytes)` returns `{adapter, inspection}` only for one exact match and throws for zero, ambiguous or corrupt matches.

- [ ] **Step 1: Write failing registry tests** for exact GR III selection, arbitrary-byte rejection, ambiguous matches, detector corruption, duplicate adapter IDs and the non-building GR II descriptor.
- [ ] **Step 2: Run `node --test node/platform/adapter-registry.test.mjs`** and confirm failure because the modules do not exist.
- [ ] **Step 3: Implement the contract and registry** with schema `1`, required method validation and explicit `NO_MATCH` signaling; wrap `inspectOfficial` in `node/adapters/gr3/index.mjs` without moving parser logic. Change the package test script to `node --test` so nested platform/adapter tests are discovered on every full run.
- [ ] **Step 4: Run the focused test and `npm test`**; expect zero failures and the existing optional legacy-backup skip only when its external fixture is absent.
- [ ] **Step 5: Record deferred commit** `feat: add multi-model adapter registry` with only the files in this task, including `package.json`.

### Task 2: Immutable object store and opaque project schema

**Files:**
- Create: `node/platform/ids.mjs`
- Create: `node/platform/project-schema.mjs`
- Create: `node/platform/store.mjs`
- Create: `node/platform/store.test.mjs`
- Modify: `node/storage.mjs`

**Interfaces:**
- Consumes: `registry.detect(bytes)` from Task 1.
- Produces: `PlatformStore.importObject(bytes)`, `createProject(objectSha, title)`, `readProject(projectId)`, `readObject(sha)`, `saveDraft(projectId, expectedRevision, draft)`.
- Project IDs match `prj_[0-9a-f]{24}` and revisions are non-negative integers.

- [ ] **Step 1: Write failing storage tests** for one object with two projects, revision conflicts, adapter/object mismatch, symlinked directories, malformed IDs, interrupted publication and legacy GR III import migration.
- [ ] **Step 2: Run `node --test node/platform/store.test.mjs`** and verify the expected missing implementation failure.
- [ ] **Step 3: Implement IDs, schemas and atomic storage** under `objects/`, `projects/`, `builds/` and `ledger.jsonl`; keep the old `Store` as a compatibility façade until Task 5.
- [ ] **Step 4: Run focused tests and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add isolated firmware projects and objects` with explicit Task 2 paths.

### Task 3: Draft and capability service

**Files:**
- Create: `node/platform/project-service.mjs`
- Create: `node/platform/project-service.test.mjs`
- Modify: `node/adapters/gr3/index.mjs`

**Interfaces:**
- Consumes: `PlatformStore` and adapter `createDraft`, `validateDraft`, `capabilities` methods.
- Produces: `ProjectService.importFirmware(bytes, filename)`, `openProject(id)`, `saveProject(id, revision, draft)`, `listProjects()`.

- [ ] **Step 1: Write failing service tests** for normalized project responses, cross-model draft rejection, stale revisions, unknown draft fields and exact adapter capability propagation.
- [ ] **Step 2: Run the focused test** and confirm missing `ProjectService` is the failure.
- [ ] **Step 3: Implement the service** so browser-supplied objects cannot contain offsets, paths, checksums or adapter-private data; return capability blockers verbatim.
- [ ] **Step 4: Run focused tests and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add model-aware project service`.

### Task 4: Atomic adapter build transaction

**Files:**
- Create: `node/platform/build-transaction.mjs`
- Create: `node/platform/build-transaction.test.mjs`
- Create: `node/platform/manifest.mjs`

**Interfaces:**
- Consumes: adapter `build` and `verify`, immutable object path, project draft and options.
- Produces: `runBuild({store, registry, projectId, options}) -> BuildRecord` only after candidate and manifest are synced and atomically published.

- [ ] **Step 1: Write failing transaction tests** for success, build exception, verifier rejection, output escape, symlink output, duplicate build ID, manifest mismatch and failure after candidate rename.
- [ ] **Step 2: Run the focused test** and confirm the missing module failure.
- [ ] **Step 3: Implement same-volume staging and publication** with output allowlist `firmware.bin`/`adapter-report.json`, normalized manifest generation and owned-artifact cleanup.
- [ ] **Step 4: Run focused tests and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `feat: add atomic adapter build transactions`.

### Task 5: Multi-model HTTP foundation

**Files:**
- Create: `node/platform/routes.mjs`
- Create: `node/platform/routes.test.mjs`
- Modify: `node/server.mjs`
- Modify: `node/server.test.mjs`

**Interfaces:**
- Consumes: `ProjectService`, `runBuild`, registry descriptors.
- Produces: `/api/adapters`, `/api/projects`, `/api/projects/{id}`, `/api/projects/{id}/draft`; retains exact old GR III read-only routes until the product-integration plan removes them.

- [ ] **Step 1: Write failing HTTP tests** for model list, import, two drafts from one object, stale save, invalid host/token/origin, ambiguous legacy route and upload limits.
- [ ] **Step 2: Run `node --test node/platform/routes.test.mjs node/server.test.mjs`** and verify the new route assertions fail.
- [ ] **Step 3: Implement the route dispatcher** and keep `node/server.mjs` limited to transport/security/bootstrap responsibilities.
- [ ] **Step 4: Run `node --check` on all new modules and `npm test`** with zero failures.
- [ ] **Step 5: Record deferred commit** `refactor: introduce multi-model HTTP foundation`.

### Task 6: Foundation review gate

**Files:**
- Modify: `docs/testing/gr3-local-workbench.md`
- Create: `docs/testing/multimodel-foundation.md`

**Interfaces:**
- Produces: evidence that GR III behavior is preserved and later plans can rely on stable adapter/project/build interfaces.

- [ ] **Step 1: Run Node and Python full suites** and both existing GR III analysis scripts.
- [ ] **Step 2: Run a focused security scan** for direct adapter-private paths, broad static downloads, unguarded POST routes and firmware bytes in JSON.
- [ ] **Step 3: Exercise two projects sharing one GR III input** through HTTP and verify independent revisions.
- [ ] **Step 4: Document exact commands, results, skips and remaining blockers** without claiming candidate generation.
- [ ] **Step 5: Perform a self-review against all five Review Focus entries**; fix findings with their own RED/GREEN cycle before starting the GR IV plan.

