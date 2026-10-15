# GR III SD Film Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. User authorized continuous implementation without further stage approvals.

**Goal:** Export all or selected platform films to SD and load them into five camera slots without changing existing rendering.
**Architecture:** Versioned complete recipe records, bounded SD reader and controller-local paginated menu; persist validated records before existing atomic slot selection. Preserve existing ROM recipes as exact versioned rendering contracts, rejecting mismatched records instead of changing algorithms.
**Tech Stack:** Node.js, C/ARM, Python Capstone/Unicorn, existing native builder and HTTP server.
**Spec:** docs/superpowers/specs/2026-10-15-gr3-sd-film-library-design.md

## Global Constraints
- Original firmware only; no GRLife implementation or format dependency.
- Five active slots; export may contain all current platform films.
- Preserve old configuration, ADJ consumers, capture and feature composition.
- Firmware module remains within 512 KiB; no device flashing or deployment.

## Review Focus
- Short SD reads and card removal must never commit a slot.
- A valid CRC is not permission to execute unsupported recipes.
- Failed persistence leaves prior five-slot state intact.
- Changing pack order does not change saved film identity.
- Private menu IDs never reach stock tone setters.

### Task 1: Verify original IO ABI
- [x] Disassemble manager, concrete SD vtable and open/read/seek/close wrappers, record sizes and short-read behavior.
- [x] Execute real wrappers in Unicorn with filesystem leaf substitutes; test requested versus actual bytes and error propagation.
- [x] Record AppData variable-size ABI and bounded read requirements; physical quota remains a documented hardware acceptance item.
Files: scripts/analyze_gr3_sd_library.py; docs/research/gr3-sd-library-abi.md.

### Task 2: Independent pack codec
- [x] Write Node tests for all 33 films, arbitrary subsets, empty/duplicate/unknown IDs, corruption and recipe mismatch; observe missing implementation failure.
- [x] Implement node/gr3-sd-film-pack.mjs: buildSdFilmPack(ids), auditSdFilmPack(bytes), complete record data and fixed-size page directory.
- [x] Add C parser validating the same bytes, exact runtime recipe compatibility and failure atomicity. Test host and ARM with shared fixtures.
Files: native/gr3/m10v_sd_library.[ch], node/gr3-sd-film-pack.test.mjs, tests/test_gr3_sd_library.py.

### Task 3: Camera and menu integration
- [x] Add read-only SD paging, complete record persistence before slot commit; bound allocation/IO and release every handle.
- [x] Add controller-local SD menu with previous/next page; preserve existing built-in menu.
- [x] Extend builder source fingerprints/resources and candidate audit without broadening patch scope.
- [x] Exercise actual linked ARM menu, corrupted card, save failure, final page and existing slot behavior.
Files: native/gr3/m10v_sd_camera.c, native/gr3/m10v_library_menu.c, scripts/build_gr3_m10v_library.py, node/gr3-m10v-native-build.mjs.

### Task 4: Platform export
- [x] Test authenticated export route, all/subset, invalid requests and independent resulting audit.
- [x] Add selection page and entry in GR III workspace, download ZIP with SD/M10V/FILMS.M10 and instructions; clearly state matching firmware required.
Files: node/server.mjs, web/gr3/sd-library.*, node/gr3-sd-film-routes.test.mjs.

### Task 5: Verification and handoff
- [x] Run complete Node suite and relevant host/ARM suites, inspect any baseline failures separately.
- [x] Generate/redecode GR III candidate and package; verify source receipt, unchanged partitions, supported combined extensions and budget.
- [x] Fresh reviewer checks entire change; resolve important findings and rerun affected checks.
- [x] Document tested limits and hardware checklist; deliver source/candidate without claiming real camera acceptance.
