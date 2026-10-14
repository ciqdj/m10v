# m10v GR III Local Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not create a subagent unless the user explicitly requests one.

**Goal:** Deliver a usable local Web workbench for exact GR III firmware inspection, verified computer-side backup and restore rehearsal, with all modified-firmware exports locked.

**Architecture:** A Python 3.12 stdlib HTTP server binds to loopback and exposes a narrow inspection/backup API. The isolated core reuses only audited GR III read-only codec/profile functions from `gr-custom-tool`; local storage and backup are implemented with exact identity and atomic writes. A small browser UI consumes server-issued capability states. No candidate builder or camera interface is included in this milestone.

**Tech Stack:** Python 3.12, `http.server`, `unittest`, HTML/CSS/vanilla JavaScript. No runtime third-party packages for the first milestone.

**2026-10-10 user change:** The first implementation used this Python plan. The user then requested a Web-only Node runtime. The active server is now `node/server.mjs`, started with `npm start` or `start.command`; it ports the strict read-only parser and backup path, with no npm dependencies. Python files remain offline reference code, not a runtime requirement. See `docs/testing/gr3-local-workbench.md` for Node verification.

**Spec:** `docs/superpowers/specs/2026-10-10-m10v-gr3-web-design.md`

## Global Constraints

- Only the exact GR III baseline is accepted: 30,391,780 bytes; SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`; project 588; internal version `2.10.21.27`.
- The supplied `fwdc239b.bin` must be ignored by Git and absent from source distributions.
- Backend capability state always reports `can_generate: false`, with the GR III CPU checksum and hardware recovery blockers. No route may serve a modified BIN.
- Backup means computer-side files only. It cannot promise camera Flash/NAND recovery or firmware downgrade.
- Any copied GPL-2.0-only source retains copyright/SPDX headers; add compatible license and attribution to m10v.
- No automatic Git commit or push in task steps. At development completion follow the user-provided release-mode choice, show exact commands, and wait for confirmation.

## Review Focus

- A same-name or same-version modified BIN must fail identity validation; Task 1 fixture test changes one byte.
- A backup ZIP with duplicate or traversal members must be rejected without changing stored data; Task 2 adversarial tests.
- A partial disk write must leave the old project and original intact; Task 2 failure-injection test.
- A non-loopback or cross-origin request must not import files; Task 3 server tests.
- A crafted browser request for `/api/build` or guessed candidate path must not return a BIN; Task 3 and Task 5 tests.

---

## File Map

- `.gitignore`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `README.md`: repository hygiene, copied-source terms, launch and recovery scope.
- `m10v_core/profile.py`, `m10v_core/codec/{container,frames}.py`, `m10v_core/firmware.py`: audited GR III identity, strict decoding and report; inspect source provenance before copying and expose no mutation API. A byte-identical no-op repack is exercised by an internal test only.
- `m10v_core/storage.py`: immutable content-addressed baseline and project records.
- `m10v_core/backup.py`: bounded ZIP export, inspection and restore rehearsal.
- `m10v_core/api.py`, `run.py`: loopback HTTP API, session token, static file serving and startup.
- `web/index.html`, `web/app.js`, `web/styles.css`: local browser workflow and capability display.
- `tests/test_firmware.py`, `tests/test_backup.py`, `tests/test_api.py`, `tests/test_workflow.py`: distinct core, storage, server and browser-contract checks.

### Task 1: Repository hygiene and strict read-only GR III core

**Files:** Create `.gitignore`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `m10v_core/{__init__,profile,firmware}.py`, `m10v_core/codec/{__init__,container,frames}.py`, `tests/test_firmware.py`; update `README.md`.

**Interfaces:** `inspect_official(data: bytes) -> FirmwareReport` returns model, full SHA, byte length, versions, section summaries and proof flags; `FirmwareIdentityError` carries a safe stage-specific message. Importing the public module exposes no mutation or repack API.

- [ ] Record the exact source commit and license for each selectively reused file; add the BIN ignore rule and attribution.
- [ ] Write `test_exact_official_report`, `test_changed_byte_rejected`, `test_wrong_project_rejected`, `test_truncated_frame_rejected` and `test_internal_noop_repack_matches_exact_official_bytes`; sample-dependent tests skip explicitly if the local BIN is absent.
- [ ] Run `python3.12 -m unittest tests.test_firmware -v`; confirm new tests fail for missing implementation.
- [ ] Implement the narrow read-only wrapper using audited GR III container/profile/decoder facts; avoid GR4 constants and remove candidate code from the exported package. Keep the no-op repack callable only inside the test module.
- [ ] Rerun the same tests and confirm exact sample report and all rejection cases pass.

### Task 2: Immutable storage and portable backup

**Files:** Create `m10v_core/storage.py`, `m10v_core/backup.py`, `tests/test_backup.py`.

**Interfaces:** `Store(root: Path).import_official(data: bytes) -> ProjectRecord`; `export_backup(store: Store, project_id: str, destination: Path) -> BackupReport`; `inspect_backup(path: Path) -> BackupReport`; `restore_backup(store: Store, path: Path) -> ProjectRecord`. The first milestone archive contains original BIN, project JSON, manifest and recovery instructions; `assets/` and `builds/` are absent while no such records exist.

- [ ] Write round-trip test that exports the sample, restores to a fresh root, and compares original and project hashes.
- [ ] Write rejection tests for missing/extra/duplicate/traversal/symlink members, changed hash, oversized entry and invalid JSON; assert the old store remains unchanged.
- [ ] Write failure-injection test for a failed temporary write or rename; assert no published partial project or overwritten original.
- [ ] Run `python3.12 -m unittest tests.test_backup -v`; confirm failures reflect missing implementation.
- [ ] Implement bounded ZIP validation, immutable hash-addressed original storage, temp-directory validation, fsync and atomic rename; reject references outside the store.
- [ ] Rerun backup tests and verify a fresh-root restore report is saved.

### Task 3: Loopback-only server and hard capability lock

**Files:** Create `m10v_core/api.py`, `run.py`, `tests/test_api.py`.

**Interfaces:** `create_server(store: Store, host: str = '127.0.0.1', port: int = 0) -> ThreadingHTTPServer`; JSON routes `GET /api/status`, `POST /api/import`, `GET /api/projects/{id}`, `POST /api/projects/{id}/backup`, `POST /api/backup/inspect`, `POST /api/backup/restore`. State-changing routes require the session token and allowed Origin. No route accepts a remote bind address.

- [ ] Write server tests for loopback bind, fresh session token, missing/wrong token, foreign Origin, upload limits and exact report JSON.
- [ ] Write tests for `/api/build`, traversal, guessed build downloads and unsupported methods; expect 404 or 403 with no BIN bytes.
- [ ] Run `python3.12 -m unittest tests.test_api -v`; confirm failures reflect missing implementation.
- [ ] Implement server, bounded request reading and static path allowlist; keep all capability values server-owned and `can_generate: false`.
- [ ] Rerun server tests; manually inspect generated status JSON for explicit CPU checksum and hardware recovery blockers.

### Task 4: Render-first browser UI

**Files:** Create a reviewable rendered mockup under `docs/design/`, then `web/index.html`, `web/app.js`, `web/styles.css` and `tests/test_workflow.py`.

**Interfaces:** UI reads `/api/status` and project reports, and offers import, partition report, backup export/inspect/restore rehearsal. Crop and shutdown cards read independent backend statuses; neither creates a firmware candidate.

- [ ] Produce a rendered view of home, report, backup and feature workbench; obtain user confirmation before writing UI code.
- [ ] Write browser-contract tests for exact hash display, unknown-input error, restore rehearsal result, two independent blocked feature cards and no enabled firmware export.
- [ ] Run `python3.12 -m unittest tests.test_workflow -v`; confirm missing UI contract failures.
- [ ] Implement HTML/CSS/JS from the approved render; escape all firmware-derived text and keep risk text beside the relevant actions.
- [ ] Run workflow tests and inspect the running page at desktop and narrow viewport sizes.

### Task 5: End-to-end verification and user handoff

**Files:** Update `README.md` and `docs/testing/gr3-local-workbench.md`; make only targeted fixes in earlier task files.

**Interfaces:** A reproducible local command launches m10v; the test record names the exact sample SHA, Python version, unit-test result, import/backup/restore hashes, server bind address and confirmed locked build behavior.

- [ ] Run all tests with Python 3.12 and verify an exact official import, ZIP export, fresh-root restore and equal SHA.
- [ ] Re-run adversarial import and backup cases through HTTP; verify rejected requests leave the original usable.
- [ ] Verify source tree and distributable omit `fwdc239b.bin`, and all modified-firmware routes remain unavailable.
- [ ] Record offline results separately from hardware status (`not_tested`) and document the computer-side recovery limit.
- [ ] Report source, tests and risks; ask the user for the repository's required release mode before any commit or push.

## Deferred, separately planned milestones

1. Candidate validation infrastructure building on the first milestone's internal exact no-op repack test.
2. Independently proven version/checksum repair and controlled minimal-version candidate; no output until all hard checks pass.
3. Separate crop and shutdown reverse-engineering plans, each with static, byte, readback and hardware gates.
4. Camera recovery procedure research and hardware test records; never infer success from the backup ZIP.
