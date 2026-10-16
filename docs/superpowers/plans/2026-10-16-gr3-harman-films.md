# HARMAN Phoenix II / RED 125 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add independent Blue Phoenix (Phoenix II 200) and HARMAN RED125 references to M10V精选, preserve common texture, implement justified special controls, then publish.

**Architecture:** Stable IDs67/68 after66. Own provenance-labelled analytic reference LUTs, not claimed measured film models. Existing native color/texture integration gains explicit stock dispatch and independent Phoenix II highlight scatter. RED has three pre-response simulated exposure choices, with own grain baseline. All camera and web settings share one versioned slot contract and validated journal migrations.

**Tech Stack:** Python/numpy/colour LUT generation, freestanding ARM C, Node independent audits, web controls.

## Research constraints

- Manufacturer Phoenix II July2025 datasheet: new emulsion versus original; finer grain/less radical contrast, no orange mask, possible halation; D55 wedge only, no full sensitometry/dye measurements. No fixed blue cast is justified.
- RED June2025 datasheet: reverse exposed original Phoenix; R responds to R+B, G to G+B, B weak. EI64/125/250 examples alter tones and grain. No measured RED PSF, do not add an unverified intrinsic halo.
- No redistributable measured LUT found. All numeric model parameters are explicit engineering assumptions. Input remains assumed display sRGB after GR3 ISP; `camera_calibrated=false`, `film_calibrated=false`. Interpolation errors describe approximation to our reference, not film similarity.
- Preserve existing films and normal functionality; no icon compression or unrelated optimization. Extend engineering allocation guards as needed while retaining mapping, ranges, readback and CRC verification.

## Tasks

- [x] Write provenance, independent analytic reference generator and semantic/interpolation/payload tests; inspect color charts and neutral/exposure sweeps.
- [x] Add native table sampler and stock dispatch; Phoenix II spatial effect; RED simulated EI; preserve 5207/800T paths. Test zero-effect, saturated colors, padding, all ID texture, stock-specific controls.
- [x] Add IDs67/68, icons, names and shared web/camera controls. Version4 schema104 / M10V5 journal; migrate published v3/M10V4 and earlier energy settings, preserve old files and special settings on common reset. Test ARM menus, migrations, capture, FN compatibility.
- [x] Run relevant Python/ARM and full Node suites, build/audit all extension combinations, verify actual browser desktop/narrow layouts and get independent review.
- [ ] Add changelog2026.10.16.4 archiving c002284 verified Actions38881736309, commit, push main/develop, wait for DEPLOY_OK and public checks.

User authorized implementation and publication, continuing the established library design without another approval round. Retain unrelated SD-library draft untracked.

UI follow-up: group appended films by category in the shared picker without modifying catalogue IDs or stored slots. Verified one M10V精选 heading followed by 800T, 5207, 蓝凤凰, 哈曼 RED in the actual browser.

Validation evidence:
- Host HARMAN/5207:55 passed; reference generator/verifier:4 passed; ARM library:30 passed; current menu/ADJ checks covered36 rows and67/68; new three-stock capture/pixel comparison passed.
- Full Node run:197 tests,192 passed,4 skipped,1 overlay range failure. Fixed its production guard and reran patch-plan suite:4 passed. Full matrix16 extension/debug combinations passed. Latest UI/group/state/guide/changelog subset:18 passed.
- Full Python discovery:317 tests; initial invocation lacked package top-level for API/backup, then16 actual tests passed in explicit package run. Three historical redraw assertion failures fixed and all17 historical tests passed (one expected historical failure). Two pre-existing workflow tests still expect obsolete homepage import forms/file-open layout; not counted as passed. Current Node homepage/guide routes verified separately.
- Actual browser verified67 halo/68 EI isolation, common reset preserving EI, refresh persistence,375px no horizontal overflow, and grouped picker order33/66/67/68 with a single curated heading. Independent native review resolved name/icon and migration defaults issues.
- Final all-extensions/debug firmware SHA256:857b3d3da2b649b810578955da76cdfaf135577911eb7510398afa5c8eb6e3d7. No camera or real-film calibration claimed.
