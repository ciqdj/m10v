# m10v Official GR III SD Update Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not spawn subagents; the current task does not authorize delegation.

**Goal:** Let the local Web workbench place the exact verified official GR III 2.10 BIN on a selected removable SD volume and prove its on-card hash before showing the official camera update steps.

**Architecture:** A macOS volume adapter discovers external physical disks using `diskutil` and resolves a freshly queried device identifier to a mounted removable volume. A separate writer stages the already imported original, syncs, publishes it as `fwdc239b.bin`, and reads it back. The server accepts only device identifiers, never browser-supplied paths; the UI displays a result distinct from camera update status.

**Tech Stack:** Node.js 20 standard library, macOS `diskutil`/`plutil`, existing vanilla JS Web UI, `node:test`. No Python or npm dependency at runtime.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-gr3-build-sd-flash-design.md`

## Global Constraints

- Official input is exactly 30,391,780 bytes with SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`; destination file name is `fwdc239b.bin`.
- `Store.readOriginal(id)` is the only firmware source for SD writing. Modified candidates are never accepted by this flow.
- A successful SD readback proves only that the official file is on the card. The camera update remains a separate manual operation.
- Preserve existing projects and backup bytes. Do not commit or push during task steps; `AGENTS.md` requires a publish-mode choice and command review when the development task is complete.
- Work in the current checkout because its untracked m10v files and neighboring dirty repositories cannot be copied safely into a fresh default-branch worktree.

## Review Focus

1. A crafted device identifier containing path syntax is rejected before any command or write (Task 1 test).
2. An external USB disk without removable SD properties, the system volume, or an unmounted volume is never offered as a target (Task 1 test).
3. An existing `fwdc239b.bin` is not overwritten, including when its bytes differ (Task 2 test).
4. Failure during staging or a wrong readback hash leaves no successful status and does not touch the stored original (Task 2 test).
5. Missing token, foreign Origin, or a direct modified-candidate write route cannot write to a volume (Task 3 test).

---

## File Map

- `node/sd-volumes.mjs`: command wrapper and strict volume identity/capability checks; owns no firmware bytes.
- `node/sd-write.mjs`: single official BIN staging, sync, publish, and readback; owns no device discovery.
- `node/server.mjs`: token-guarded volume listing and official project write route.
- `web/index.html`, `web/app.js`, `web/styles.css`: selected-card, progress, hash and manual camera steps in the approved page style.
- Corresponding `*.test.mjs` files: real core behavior with injected volume provider / temporary volume, plus HTTP contract.
- `docs/testing/gr3-sd-update.md`: exact verification record and physical SD gate.

### Task 1: Removable-volume discovery and fresh identity verification

**Files:** Create `node/sd-volumes.mjs`, `node/sd-volumes.test.mjs`.

**Interfaces:** `listSdVolumes(runDiskutil = defaultRunner) -> Promise<Volume[]>`; `resolveSdVolume(deviceIdentifier, runDiskutil = defaultRunner) -> Promise<Volume>`. `Volume` contains `device_identifier`, `mount_point`, `total_bytes`, `file_system` and verified removable/external/writable properties; only `device_identifier` crosses HTTP.

- [ ] Write tests with captured plist fixtures for a removable mounted card, an internal/system disk, an unmounted disk, and malformed identifiers. Assert only the removable card is listed and resolve rejects all unsafe values.
- [ ] Run `node --test node/sd-volumes.test.mjs`; verify failure is due to missing implementation.
- [ ] Implement `diskutil list -plist external physical`, `diskutil info -plist <identifier>`, and `plutil -convert json -o - -` using argument arrays, bounded output and fresh re-query. Require a mount under `/Volumes/`, no symlink, external/removable/ejectable media and writable volume; reject unsupported platforms explicitly.
- [ ] Rerun the focused test and `npm test`; confirm all pass.

### Task 2: Verified official-file staging on one volume

**Files:** Create `node/sd-write.mjs`, `node/sd-write.test.mjs`.

**Interfaces:** `prepareOfficialSd(original: Buffer, volume: Volume) -> Promise<{device_identifier, filename, bytes, sha256, mount_point, status}>`, with `status: 'official_sd_ready'` only after target-file readback.

- [ ] Write tests using a temporary mounted-volume simulation: exact source writes `fwdc239b.bin` and reads back the same SHA; existing target refuses overwrite; insufficient space, staging failure and altered readback yield errors with no success report.
- [ ] Run `node --test node/sd-write.test.mjs`; verify the expected missing-function failure.
- [ ] Implement `inspectOfficial(original)` before write, regular directory/no-symlink checks, free-space check, exclusive stage creation on the selected volume, file sync, final-name absent check, rename, directory sync and fresh file readback. Clean temporary artifacts on failure; never return ready status before full SHA/length equality.
- [ ] Rerun the focused test and `npm test`; confirm all pass.

### Task 3: Server capability and HTTP security boundary

**Files:** Modify `node/server.mjs`, `node/server.test.mjs`.

**Interfaces:** `GET /api/sd/volumes` returns identifiers and display metadata; `POST /api/projects/{id}/sd/prepare` accepts JSON `{device_identifier}` and uses `Store.readOriginal(id)`. The same server-issued token and Origin rules as import/backup apply to the POST.

- [ ] Add HTTP tests proving imported official bytes can reach the injected SD writer, missing token and foreign Origin return 403, body/path tricks return 400/404, and every modified-candidate SD route remains 404.
- [ ] Run `node --test node/server.test.mjs`; verify the new tests fail for absent routes.
- [ ] Implement the two routes with a narrow JSON body cap, injected SD service for tests and fresh `resolveSdVolume` immediately before writing. `/api/status` distinguishes `official_sd_supported` from `candidate_sd_blocked`.
- [ ] Rerun the focused test and `npm test`; confirm all pass.

### Task 4: Existing-page SD workflow and physical-card check

**Files:** Modify `web/index.html`, `web/app.js`, `web/styles.css`, `node/server.test.mjs`; create `docs/testing/gr3-sd-update.md`.

**Interfaces:** After official import, show available card identifiers/mount names, exact output name and SHA, a deliberate “写入官方包到 SD 卡” action, readback result, and the separate official camera-update steps. No modified-candidate write action appears.

- [ ] Create a rendered preview of the added card in the current layout and get user confirmation before changing UI code.
- [ ] Add page-contract assertions for the card selector, official-only action, readback hash and camera-status separation; verify they fail with the old page.
- [ ] Implement the confirmed UI, preserving file-picker and backup flows. Handle no card, stale selection, write failure and a successful on-card hash without marking camera verified.
- [ ] Run `npm test`, `git diff --check -- m10v`, and a local browser check of the page. Record that `diskutil list -plist external physical` currently shows no removable card; mark real-card write/readback as pending until a card is present.

## Completion gate

The feature is locally complete when tests and the actual Web route can prepare and read back the exact official BIN on a real removable SD card. If no card is available, report software verification separately from the unperformed physical-card check; do not claim a camera update.
