# Flat Film Grid Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task.

**Goal:** Open all 30 films directly in their exact requested order, using legible portrait artwork and reliable exit buttons.

**Architecture:** Preserve the five backend metadata groups and stable IDs; flatten only the camera selector. Reuse its ten owned bitmap buffers, eliminate the broken external caption stream, and scope physical button handling to the owned film controller.

**Tech Stack:** C/ARM, Python asset generation and Unicorn, Node firmware export.

**Spec:** Latest user instructions in this conversation: no directory page; all films displayed directly; pictures identify the exact film; MENU exits and DISP returns to shooting.

## Global Constraints

- Exact 30-film order from web/gr3/film-directory.json; no renaming, ID reuse or LUT change.
- Two rows of five, three continuous pages; no card-external names.
- Preserve 184-byte journal, ten-slot cap, read-only browsing, other native pages and A/B behavior.
- Preserve allocation ownership and ROM checks; do not increase the firmware growth budget.
- Build a new identifiable GR III 2.10 candidate; device validation precedes publication.

## Review Focus

- Sparse or stale SD records must not install another ID.
- Full/retired slots require explicit cleanup; browsing never writes.
- Physical release/hold/repeat events must not retrigger exits.
- Foreign controllers and native A/B DISP retain their behavior.
- OOM fallback and repeated paging must not leak or retain freed bitmap pointers.

### Task 1: Flat selector and artwork

**Files:** native/gr3/m10v_settings.c/.h, m10v_settings_view.c/.h, m10v_film_card.c/.h, scripts/generate_m10v_film_cards.py, scripts/build_gr3_m10v_library.py, node/gr3-m10v-native-build.mjs; tests/test_gr3_directory_menu.py, tests/test_gr3_directory_view.py.

**Interfaces:** Existing settings open/key and film-card render signatures unchanged. Add M10V_KEY_CLEAN for explicit retired-slot maintenance inside the film page.

- [x] Replace group assertions with flat navigation over all 30 IDs, three pages, stale/sparse records, zero-write cancel and explicit cleanup tests; run to establish failure.
- [x] Open catalog directly, remove group view and external labels, draw page x/3. Keep explicit cleanup behind private-page Fn when retired slots exist.
- [x] Render brand/model inside 120x148 portrait boxes with bounded glyph scaling; remove caption stream from runtime and update manifest assertions.
- [x] Verify real original ARM widgets, heap failure, paging and teardown; render all 30 actual C cards into preview images.

### Task 2: Physical exits and delivery

**Files:** native/gr3/m10v_settings_controller.c, native/gr3/m10v_ab_camera.inc, tests/test_gr3_flat_controller.py, docs/testing/gr3-flat-film-grid-r2-20261023.md.

**Interfaces:** Existing BaseController dispatch wrapper; MENU key5 closes private film page; DISP key4 calls native route08000000, parent10000000 once per physical press.

- [x] Add tests executing original BaseController filtering with real physical packet shape; cover phase/repeat and foreign-owner pass-through.
- [x] Implement owned-page scoped exits with lifecycle recheck and no duplicate virtual dispatch.
- [x] Run scoped C/ARM/Node regressions and complete npm suite against known baseline (final log recorded in delivery report); verify integrated RAW NR budget and final export.
- [x] Commit scoped changes and build a unique test package with source/config fingerprints, hashes and device checklist. Publication stays pending this candidate's device validation.
