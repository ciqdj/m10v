# m10v GR III Version And Recovery Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not spawn subagents; the current task does not authorize delegation.

**Goal:** Complete the safe GR III workbench by turning the verified `2.10.21.27` to `2.10.21.28` research probe into an independently checked report-only capability, hardening official SD publication, and keeping every modified BIN egress path closed until hardware recovery is proven.

**Architecture:** A dedicated version module edits only the four evidenced version fields and the evidenced CPU/decoded/container additive checksums in memory. A separate verifier freshly decodes the result, proves the exact diff whitelist, and returns metadata without returning bytes. The HTTP/UI layer exposes same-version-first strategy and the micro-version probe as evidence only; the official SD writer publishes the original BIN using a same-volume atomic no-overwrite operation.

**Tech Stack:** Node.js 20 standard library, `node:test`, vanilla HTML/CSS/JavaScript; Python 3.12 research probe only as an independent cross-check.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-gr3-build-sd-flash-design.md`

## Global Constraints

- Accept only the exact 30,391,780-byte source with SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4` and project 588.
- Source version is exactly `2.10.21.27`; the only research successor is `2.10.21.28`.
- Default strategy remains same-version first. The incremented candidate is a probe, not an enabled flashing path.
- Candidate bytes never enter HTTP, backup ZIP, persistent storage, logs, static files, downloads, or SD writing.
- Computer backup contains the official package and project identity, not camera Flash/NAND; UI and docs must not promise brick recovery.
- Preserve all unrelated parent-repository changes. Do not commit or push until the user selects an `AGENTS.md` publish mode.

## Review Focus

1. A target below, equal to, or outside the `(2,10,21,x)` successor range must not create a version-bump report.
2. All four version sites must agree after a bump; changing any fifth logical byte must fail independent verification.
3. CPU big-endian sum, decoded little-endian sum, and outer little-endian sum must each fail when independently corrupted.
4. Direct build/download/backup/SD requests must never expose or persist the incremented candidate.
5. An existing SD target or publication race must not overwrite the existing `fwdc239b.bin` or report `official_sd_ready`.

---

### Task 1: Version successor policy and exact four-site edit

**Files:**
- Create: `node/version-candidate.mjs`
- Create: `node/version-candidate.test.mjs`

**Interfaces:**
- Produces: `analyzeVersionProbe(official: Buffer, target = '2.10.21.28') -> VersionProbeReport`
- Internal: `buildVersionProbe(official: Buffer, targetWord: number) -> {candidate: Buffer, targetDecoded: Buffer, replay: object}`; this function is not exported.

- [ ] Write failing tests for exact successor acceptance and rejection of same, lower, skipped-family, overflow, and malformed versions.
- [ ] Run `node --test node/version-candidate.test.mjs`; expect missing-module failure.
- [ ] Implement the exact four version writes, repair CPU word `+0x7C`, decoded trailer sum, and outer container sum through the existing frame replay.
- [ ] Return a JSON-safe report only: hashes, sizes, four readback versions, changed logical ranges, frame counts, sums, blockers, and `candidate_export_allowed: false` / `candidate_sd_allowed: false`.
- [ ] Run the focused test and `npm test`; expect all tests passing.

### Task 2: Independent version-candidate verification

**Files:**
- Create: `node/version-verify.mjs`
- Create: `node/version-verify.test.mjs`
- Modify: `node/version-candidate.mjs`

**Interfaces:**
- Produces: `verifyVersionProbe(official: Buffer, candidate: Buffer, targetWord: number) -> VersionProbeReport`
- Consumes: `decodeFrameMap`, exact firmware section boundaries, and the four evidenced version offsets.

- [ ] Write failing tamper tests for a fifth logical byte, each version copy, CPU checksum, decoded checksum, container checksum, malformed frame, and target/source mismatch.
- [ ] Run the focused test; expect missing verifier failure.
- [ ] Implement a fresh decode that permits differences only at the four version bytes and the two evidenced checksum words; require all non-target partitions and bytes unchanged.
- [ ] Verify CPU BE32 sum zero, decoded LE32 sum zero, outer LE32 sum zero, project/markers, section boundaries, and exact successor readback.
- [ ] Run focused tests, `npm test`, and `/opt/homebrew/bin/python3.12 scripts/probe_gr3_version_repack.py fwdc239b.bin`; compare Node and Python report fields.

### Task 3: Report-only HTTP and Web strategy display

**Files:**
- Modify: `node/server.mjs`
- Modify: `node/server.test.mjs`
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`

**Interfaces:**
- `POST /api/projects/{id}/versions/probe` accepts an empty body, requires session token and same Origin, and returns only `VersionProbeReport`.
- `/api/status` exposes `version_strategy: 'same_version_first'`, `version_probe_available: true`, and keeps all candidate export/write capabilities false.

- [ ] Add failing HTTP/page-contract tests for authorization, exact report fields, empty-body limit, and absence of candidate bytes or modified-BIN routes.
- [ ] Run the focused server tests; expect 404/status-contract failures.
- [ ] Implement the report-only route and immutable capability flags without storing candidate bytes.
- [ ] Add a compact version strategy block to the existing candidate area: current four-site version, recommended same-version route, optional `2.10.21.28` offline probe, and explicit recovery/export blockers.
- [ ] Run focused tests and `npm test`; inspect desktop and narrow layouts without claiming camera acceptance.

### Task 4: Atomic no-overwrite official SD publication

**Files:**
- Modify: `node/sd-write.mjs`
- Modify: `node/sd-write.test.mjs`
- Modify: `docs/testing/gr3-sd-update.md`

**Interfaces:**
- `prepareOfficialSd()` keeps its public return shape but publishes the staged file with same-volume atomic no-overwrite semantics.

- [ ] Add failing tests for a publication race that creates the destination after staging, forced publish failure, and preservation of a pre-existing target.
- [ ] Run the focused test and confirm the current copy-based implementation fails the race contract.
- [ ] Replace final copying with same-volume atomic no-overwrite publication, sync the file and directory, and remove only the owned staging file on failure.
- [ ] Run focused tests and `npm test`; update the SD test record with the exact local evidence and keep real-card status pending.

### Task 5: Backup/recovery boundary and complete verification

**Files:**
- Modify: `node/backup.test.mjs`
- Modify: `node/server.test.mjs`
- Modify: `README.md`
- Modify: `docs/testing/gr3-local-workbench.md`

**Interfaces:**
- Existing backup format remains four-member and official-only; no version probe or candidate is added.

- [ ] Add failing regression assertions that backup ZIP restores only the official hash and cannot contain candidate/version-probe bytes or metadata claiming camera recovery.
- [ ] Run focused tests and confirm any missing contract fails before documentation changes.
- [ ] Make only the minimal implementation or copy changes needed to satisfy the recovery boundary.
- [ ] Run `npm test`, `PYTHONPATH=. /opt/homebrew/bin/python3.12 -m unittest -v`, both analysis scripts, the Python version probe, and `git diff --check -- m10v` from the parent repository.
- [ ] Perform a final review against all five Review Focus items and record any ruling; do not create a commit or push before the publish-mode prompt.

## Completion Gate

The workbench is complete for offline use when the exact version successor can be built and independently verified only in memory, its report is visible without any candidate byte egress, official backup remains exact and honest about recovery limits, and official SD publication is atomic/no-overwrite. Modified-firmware flashing, downgrade recovery, and camera acceptance remain blocked until separate hardware evidence exists.
