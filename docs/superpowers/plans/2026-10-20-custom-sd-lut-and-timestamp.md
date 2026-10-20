# Custom SD LUT and Timestamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import named 3D `.cube` LUTs into the SD film library, install them into camera slots, render saved JPEGs with them, and keep one web timestamp control in Imaging.

**Architecture:** A versioned 12288-byte record carries a 13³ RGB8 table and bounded name. The camera validates and saves the record before switching a slot; capture reads the saved record, never the SD card. Existing built-in records and state remain compatible.

**Tech Stack:** Node.js ESM, browser JavaScript, C/ARM firmware modules, Node test runner, Python unittest/ctypes host tests.

**Spec:** `docs/superpowers/specs/2026-10-20-custom-sd-lut-and-timestamp-design.md`

## Global Constraints

- GR III and GR IIIx must each pass their own ABI, budget, build and artifact checks.
- Only saved JPEG color changes; live view, RAW pixels and in-camera RAW development are outside scope.
- Up to 256 pack records; five active slots; each custom LUT is a 13³ RGB8 table (6591 bytes).
- Capture performs no SD access or `.cube` parsing. Existing time stamp, grain and leak effects remain composable.
- Old v1 built-in packs remain accepted; old firmware rejects the new custom record format.
- No camera success claim without actual device validation.

## Review Focus

- A 33³ or 65³ LUT must show the 13³ downsampling notice and export a deterministic table: Task 1 test.
- A malformed numeric token, 1D LUT or duplicate name must be rejected before export: Tasks 1 and 2 tests.
- A custom snapshot write that succeeds but fails readback must leave all five slots unchanged: Task 4 test.
- A missing or corrupt custom snapshot after restart must not feed arbitrary data into JPEG rendering: Tasks 4 and 5 tests.
- Enabling or disabling timestamp in Imaging after editing film slots must preserve all slot values: Task 6 test.

---

### Task 1: Portable LUT parser and record encoder

**Files:** Create `node/gr3-custom-lut.mjs`; modify `node/gr3-sd-film-pack.mjs`; test `node/gr3-custom-lut.test.mjs` and `node/gr3-sd-film-pack.test.mjs`.

**Interfaces:** `parseCustomCube(bytes: Buffer, filename: string, name: string): {id: number, name: string, rgb: Buffer, sha256: string}`; `customFilmRecord(film): Buffer`; `buildSdFilmPack(ids: number[], customFilms?: CustomFilm[]): Buffer`. Custom IDs start at 73 and are assigned deterministically from sorted content hashes within one export; duplicate hashes/names fail.

- [ ] Write tests: identity 2³ samples into 13³ RGB8; 33³ input produces deterministic 6591 bytes; empty/8 MiB+/1D/NaN/missing rows/duplicate names reject; original 40 records remain byte-identical.
- [ ] Run `node --test node/gr3-custom-lut.test.mjs node/gr3-sd-film-pack.test.mjs`; confirm new tests fail.
- [ ] Implement strict `.cube` parser, bounded ASCII camera name, trilinear resampling and custom record encoding. Choose and document exact byte offsets next to the encoder and C decoder; keep CRC and renderer version binding.
- [ ] Run the two test files and commit the portable format.

### Task 2: Export API and library page

**Files:** Modify `node/gr3-sd-film-export.mjs`, `node/server.mjs`, `web/gr3/sd-library.html`, `web/gr3/sd-library.js`, `web/gr3/sd-library.css`, `node/server.test.mjs`; create `node/gr3-sd-film-export.test.mjs`.

**Interfaces:** `exportSdFilms({model, ids, customFilms})` consumes bounded base64 `.cube` payloads and returns `{receipt, zip}`; `/api/gr3/sd-library/export` remains token protected. GR IV keeps its current route until separately validated.

- [ ] Write tests for mixed built-in/custom ZIP, invalid LUT and duplicate name HTTP errors, request-size cap, and unchanged built-in-only export.
- [ ] Run the named tests; confirm new tests fail.
- [ ] Add name/file import controls, selected custom cards, removal, busy/error state, downsampling notice and preview; send only selected entries on export. Increase only this endpoint's body limit to the bounded number of accepted LUT files, with a hard total cap.
- [ ] Run tests and a browser inspection of the page; commit.

### Task 3: C pack validator and menu identity

**Files:** Modify `native/gr3/m10v_sd_library.h`, `native/gr3/m10v_sd_library.c`, `native/gr3/m10v_sd_camera.c`, `native/gr3/m10v_settings_view.c`; test `tests/test_gr3_sd_library.py`, `tests/test_gr3_sd_camera.py`, `tests/test_gr3_sd_menu.py`.

**Interfaces:** Keep `m10v_sd_header`/`m10v_sd_record` and add `m10v_sd_custom_record(const uint8_t *record, uint32_t bytes, uint32_t expected_id)`; `m10v_sd_camera_item` returns a validated custom ID; menu name reads only validated bounded record text.

- [ ] Write shared Node/C vectors for valid custom record and corrupt CRC, digest, bounds, version, name, duplicate ID, short read and card removal.
- [ ] Run the three Python tests; confirm new vectors fail.
- [ ] Implement version dispatch and data-only validation, with v1 built-in path unchanged. Add menu label handling without leaking SD buffer lifetimes into capture.
- [ ] Run tests and commit.

### Task 4: Durable custom slots

**Files:** Modify `native/gr3/m10v_library.h`, `native/gr3/m10v_library.c`, `native/gr3/m10v_sd_camera.c`; test `tests/test_gr3_sd_camera.py`, `tests/test_gr3_m10v_library.py`.

**Interfaces:** Custom slot ID 73–288 maps to a slot-owned validated snapshot, not a global ID file. `m10v_camera_library_select_custom(state, slot, id, record)` persists and reads back the snapshot, then commits the slot journal. Built-in select signature stays unchanged.

- [ ] Write tests for five distinct custom slots, restart, swap card, replacement, failed/short snapshot write, failed readback, corrupted snapshot and v1 migration. Assert old slot and timestamp remain intact on every failure.
- [ ] Run named tests and confirm new tests fail.
- [ ] Implement slot-scoped storage, validate AppData size and transaction order, and load only complete validated snapshots. If storage or ARM budget cannot support five records, stop before creating a flashable candidate and report the measured limit.
- [ ] Run tests and commit.

### Task 5: JPEG LUT rendering and firmware integration

**Files:** Modify `native/gr3/m10v_library.c`, `native/gr3/m10v_library.h`, `node/gr3-m10v-native-build.mjs`; test `tests/test_gr3_m10v_library.py`, `tests/test_gr3_native_render_handoff.py`, `tests/test_gr3_film_lut_performance.py`, `node/gr3-m10v-native-build.test.mjs`.

**Interfaces:** Custom record lookup returns the validated 13³ table for `m10v_library_render_native`; interpolation uses existing YUV/JPEG color path and preserves spatial effects and timestamp order.

- [ ] Write pixel reference tests for identity and channel swap LUTs, boundary RGB values, malformed snapshot fallback, grain/leak/time stamp composition and no SD calls in capture.
- [ ] Run named tests; confirm new tests fail.
- [ ] Implement camera table lookup and trilinear sampling without capture allocations or new SD reads; update GR III and GR IIIx build manifests and verified resource budgets.
- [ ] Run host tests, firmware build/audit and performance gate for each supported model; commit only if all budgets pass.

### Task 6: One timestamp web entry

**Files:** Modify `web/gr3/native-library-controls.html`, `web/gr3/native-library.js`, `web/gr3/studio.js`, `web/gr3/sd-library.html`; test `node/ui-contract.test.mjs`, `node/gr3-unified-state.test.mjs`.

**Interfaces:** Imaging renders the existing global `stamp/format/corner/color` fields; native editor no longer renders duplicate time stamp controls. Camera time-stamp menu and stored fields stay unchanged.

- [ ] Write tests asserting one visible web time stamp editor, slot preservation across toggle/edit, legacy draft preservation and correct in-camera menu instructions.
- [ ] Run named tests; confirm new tests fail.
- [ ] Move controls and event binding to Imaging, remove duplicate editor controls, and update copy/instructions.
- [ ] Run tests and browser inspection; commit.

### Task 7: End-to-end audit and device handoff

**Files:** Modify `web/guide.html`, `docs/testing/gr3-sd-custom-lut-20261020.md`; test relevant Node and Python suites.

**Interfaces:** Document exact firmware/package version pairing, custom LUT limits, JPEG-only scope and camera test protocol.

- [ ] Test full ZIP → C validator → slot install → restart → JPEG reference path, including old v1 package and mixed built-in/custom package.
- [ ] Run `npm test` plus focused Python SD, menu, render and GR IIIx/GR IV regression suites; inspect independent final firmware diff and budget reports.
- [ ] Record exact offline results and a GR III / GR IIIx real-device checklist; mark untested behavior as pending.
- [ ] Commit docs and final fixes, then request whole-branch review.
