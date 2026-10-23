# Film Catalogue Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exactly match the user's five groups and 30 names in the backend and camera, rebuilding 2460 from its own spectral model.

**Architecture:** One JSON catalogue owns names, stable identities, grouping and order. Generate the camera table and use it for SD ordering and group-bounded camera navigation; retain decoder identities for existing journals.

**Tech Stack:** Node.js, Python/NumPy/Spectral Film LUT, freestanding C/ARM.

**Spec:** `docs/superpowers/specs/2026-10-23-film-catalog-order-design.md`

## Global Constraints

- Exact spellings and order are the spec's 30-item list; only one Cyanotype.
- Existing Pixel World is ID 290; style IDs 291..297 remain stable; 5213 uses 298.
- Keep ten slots, model gates, RAW ownership, atomic storage and existing capture behavior.
- No claims of physical film calibration or camera acceptance; no push/deploy before device acceptance.

## Review Focus

- A stale SD card must not bypass the requested ordering or identify the wrong film.
- Groups with one, six or fourteen films must navigate without empty selections or accidental writes.
- Long English names must remain complete in caption and stamp paths.
- Old hidden IDs and 79..288 custom identities must not be rebound.
- 2460 and 5213 native, CPU and web rendering must consume the matching new targets.

### Task 1: Shared directory and exact backend/SD output

**Files:** `web/gr3/film-directory.json`, `node/gr3-film-directory.mjs`, `scripts/generate_m10v_directory.py`, `native/gr3/m10v_film_directory.h`, catalogue/SD/icon/caption consumers.

**Interfaces:** `FILM_DIRECTORY`, `directoryFilm(id)`, `orderedFilmIds(ids)`; C `m10v_directory_*` inline accessors.

- [ ] Write/run failing API and SD round-trip tests against the literal user list.
- [ ] Add the shared directory and update consumers without changing stable IDs.
- [ ] Generate labels/artwork metadata and compare Node/SD/C identities.
- [ ] Run Node catalogue, picker, SD and native-name checks.

### Task 2: Spectral 2460 and independent 5213

**Files:** spectral generator/manifest/LUT assets, C rendering and native ISP target dispatch, browser preview and build source contracts.

**Interfaces:** explicit mappings 77 -> KODAK_AEROCOLOR; 298 -> KODAK_5213; immutable LUTs and matching native profiles.

- [ ] Write/run failing tests that reject the old 2460 approximation and wrong-stock substitutions.
- [ ] Bake full spectral pipelines with pinned parameters, then fit native targets and report holdout errors.
- [ ] Wire CPU, ISP, preview, SD and build validation to matching tables.
- [ ] Verify deterministic provenance, LUT sampling and native/C endpoints.

### Task 3: Grouped camera menu and final candidate

**Files:** settings state/view/controller, menu resource generator, build fingerprints and tests/testing receipt.

**Interfaces:** ordered directory groups, group-bounded card pages; existing install/remove transaction retained.

- [ ] Write/run failing navigation tests for all groups, page boundaries, cancel and full ten-slot state.
- [ ] Implement grouped navigation and exact group/name captions.
- [ ] Run affected Python/ARM tests, npm test, build and read back a GR III candidate.
- [ ] Obtain a fresh whole-branch review, address important findings, and deliver an identifiable test package with limits.

Baseline: origin/main `41f6f77`. Initial targeted 18 tests: 15 pass, 3 pre-existing failures (two old SD compatibility fixtures and one v4-offset style-filter journal test). Preserve this evidence separately from new failures.
