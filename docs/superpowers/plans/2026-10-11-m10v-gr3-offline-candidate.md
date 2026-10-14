# m10v GR III Offline Candidate Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not spawn subagents; the current task does not authorize delegation.

**Goal:** Rebuild and independently inspect a minimal Street Edition `Collabo.jpg` candidate in memory while keeping all modified BIN download, backup and SD-write paths closed.

**Architecture:** A Node frame codec starts from the immutable exact official BIN, reuses unchanged encoded frames and emits bounded literal frames for changed decoded ranges. A dedicated resource module permits one exact-size JPEG record replacement; a separate verifier decodes the resulting container anew and checks the requested diff, versions and known sums. The local API returns a report and drops candidate bytes.

**Tech Stack:** Node.js 20 standard library and `node:test` at runtime; existing Python 3.12 research decoder used only as a development cross-check.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-gr3-build-sd-flash-design.md`

## Global Constraints

- Only source SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4` and project 588 are accepted.
- First target is the 111,155-byte, 720×480 `B:\\Resource\\Jpeg\\Collabo.jpg` payload in `RES`; the four baseline version sites remain `02 0a 15 1b`.
- Candidate bytes never enter an HTTP response, static directory, backup ZIP or SD writer. Neither a UI switch nor caller-supplied evidence can change this.
- `candidate_offline_verified` means only that all implemented static checks passed. Camera acceptance, internal installed version, recovery and custom crop remain unverified.
- Preserve existing files in the dirty parent checkout. No Git commit or push during tasks; use the `AGENTS.md` publish-mode flow after completion.

## Review Focus

1. No-op repack must be byte-for-byte the exact official BIN, not merely decodable (Task 2 test).
2. A JPEG with wrong dimensions, extra data after EOI, unsupported SOF, or wrong exact length must be rejected before candidate build (Task 3 test).
3. A changed RTOS/CPU/version byte or a second RES record must fail the independent diff whitelist (Task 4 test).
4. A malformed encoded frame or a stale checksum must fail fresh candidate decoding (Task 4 test).
5. Crafted `/api/build`, candidate-download and candidate-SD requests must not return modified bytes (Task 5 test).

---

## File Map

- `node/gr3-frames.mjs`: frame boundaries, deterministic replay, literal replacement and outer/decoded additive sum repair.
- `node/gr3-jpeg.mjs`: strict JPEG profile and resource-record lookup for the one Street target.
- `node/candidate-verify.mjs`: independent fresh decode, section/version/diff and checksum checks.
- `node/candidate.mjs`: combines exact baseline, resource replacement, repack and verification; returns report only.
- `node/server.mjs`: report-only candidate analysis endpoint and server-owned capability state.
- `web/`: approved page addition for image upload and offline report, with no firmware export button.
- `scripts/analyze_gr3_rtos.mjs` and research docs: reproducible update/consumer evidence matrix with explicit unknowns.

### Task 1: Update-path evidence matrix

**Files:** Create `scripts/analyze_gr3_update.mjs`, `node/gr3-update-evidence.test.mjs`; modify `docs/research/gr3-crop-shutdown-evidence.md`.

**Interfaces:** `analyzeUpdatePath(official: Buffer) -> {source_sha256, gates: Gate[], unresolved: string[]}`; each `Gate` records exact ROM address, expected instruction bytes, observed behavior and the caller that makes it relevant.

- [ ] Write tests asserting the exact official sample reports the known version-branch caller `0x53838CD0`, project/marker wrapper `0x536290C8`, CPU verifier `0x53629044`, and unresolved flash-write/acceptance links; a one-byte altered official input must be rejected.
- [ ] Run `node --test node/gr3-update-evidence.test.mjs`; confirm the missing-module failure.
- [ ] Trace the candidate path from update-state dispatch through project, version, integrity and write callbacks using only this RTOS/section data. Implement exact instruction/table assertions for supported claims and record every unresolved edge; do not infer an untraced write or recovery path.
- [ ] Rerun focused test and `node scripts/analyze_gr3_update.mjs fwdc239b.bin`; update the research document from its generated evidence.

### Task 2: Deterministic Node frame replay

**Files:** Create `node/gr3-frames.mjs`, `node/gr3-frames.test.mjs`.

**Interfaces:** `decodeFrameMap(official: Buffer) -> {decoded: Buffer, frames: Frame[]}` and `repackWithTarget(official: Buffer, targetDecoded: Buffer) -> {candidate: Buffer, reused_frames, replaced_frames}`. Each `Frame` records encoded/decoded half-open offsets.

- [ ] Add sample-dependent tests: no-op replay equals original bytes and SHA; a one-byte decoded mutation with repaired trailer re-decodes exactly, with nonzero replaced frames. Test a truncated encoded frame and an invalid target length.
- [ ] Run `node --test node/gr3-frames.test.mjs`; confirm missing implementation failure.
- [ ] Implement strict frame-map decode and original-frame reuse. For changed frames emit literal chunks no longer than 0x7fff bytes, recalculate encoded size/footer/container sum, and verify generated output re-decodes to target; avoid Python runtime calls.
- [ ] Rerun focused test and `npm test`; cross-check probe output with `PYTHONPATH=. python3.12 scripts/probe_gr3_res_repack.py fwdc239b.bin`.

### Task 3: Street JPEG profile and one-record logical edit

**Files:** Create `node/gr3-jpeg.mjs`, `node/gr3-jpeg.test.mjs`.

**Interfaces:** `inspectStreetJpeg(jpeg: Buffer) -> {width: 720, height: 480, bytes: 111155, profile: object}`; `replaceCollabo(decoded: Buffer, jpeg: Buffer) -> {targetDecoded: Buffer, changed_offset: number, changed_length: number}`.

- [ ] Add tests for exact official resource roundtrip, wrong dimensions/length, truncated JPEG, trailing data, unsupported coding markers and a second-record modification attempt.
- [ ] Run `node --test node/gr3-jpeg.test.mjs`; confirm missing implementation failure.
- [ ] Implement marker parsing and compare the required profile against the exact official JPEG. Locate the `RES` record by full path, enforce its unchanged length and resource table count, write only its payload, then repair the decoded trailer sum.
- [ ] Rerun focused test and `npm test`; record which JPEG encoding characteristics remain unproven on hardware.

### Task 4: Independent candidate readback and diff audit

**Files:** Create `node/candidate-verify.mjs`, `node/candidate-verify.test.mjs`, `node/candidate.mjs`, `node/candidate.test.mjs`.

**Interfaces:** `verifyCandidate(official: Buffer, candidate: Buffer, requestedJpeg: Buffer) -> CandidateReport`; `analyzeStreetCandidate(official: Buffer, jpeg: Buffer) -> CandidateReport`. The report includes source/candidate hashes, version readback, changed logical offsets, frame counts, all known sums, `status: 'candidate_offline_verified'` and blockers. No exported function returns candidate bytes to the server.

- [ ] Write tests that tamper with a second RES record, CPU/version sites, footer sum and one encoded frame; each must fail. Test an exact input JPEG yields a report but no candidate byte property.
- [ ] Run `node --test node/candidate-verify.test.mjs node/candidate.test.mjs`; confirm missing implementation failure.
- [ ] Implement a fresh candidate parse independent of the writer's replay state, validate all 14 section boundaries, four unchanged version sites, unchanged non-target records and sections, JPEG readback, CPU/decoded/container sums, and target-specific logical diff.
- [ ] Rerun focused tests, `npm test` and the Python probe as a separate decoder cross-check.

### Task 5: Report-only HTTP capability

**Files:** Modify `node/server.mjs`, `node/server.test.mjs`, `node/backup.test.mjs` if necessary.

**Interfaces:** `POST /api/projects/{id}/candidates/shutdown/analyze` accepts at most 2 MiB JPEG bytes, requires token and same Origin, and returns only `CandidateReport`. `/api/status` advertises offline analysis separately from candidate export and SD writing.

- [ ] Add HTTP tests for exact official project, missing token, wrong Origin, oversized upload, and crafted build/download/SD routes; assert response bytes never contain a candidate BIN and backup ZIP remains original-only.
- [ ] Run `node --test node/server.test.mjs`; confirm new route expectations fail with 404.
- [ ] Implement the report-only route and immutable capability state. Avoid saving candidate bytes to `Store`, temp directories or logs.
- [ ] Rerun focused tests and `npm test`.

### Task 6: Visual integration and traceable research record

**Files:** Modify `web/index.html`, `web/app.js`, `web/styles.css`, `docs/testing/gr3-local-workbench.md`.

**Interfaces:** The existing shutdown card submits the selected JPEG to the report-only API and displays candidate hash, diff scope, known checks and blockers. It never offers modified BIN download or write-card control.

- [ ] Render the proposed card state and obtain user confirmation before UI code, following the earlier visual preference.
- [ ] Add page-contract tests for the selected-image report, explicit `offline_verified` label and blocked export; verify the old page fails them.
- [ ] Implement the confirmed UI and display the update-path evidence matrix's unresolved checks alongside the offline report, keeping unknown camera acceptance explicit.
- [ ] Run `npm test`, `node scripts/analyze_gr3_rtos.mjs fwdc239b.bin`, `git diff --check -- m10v`, and inspect the running page at desktop and narrow widths. Record local results separately from hardware status.

## Completion gate

The local builder is complete when exact no-op reconstruction and modified-input tests pass through an independent fresh decoder, the Web shows a report, and all modified BIN egress paths remain closed. Real JPEG compatibility and camera flashing remain hardware-gated, especially with the user's only Street Edition.
