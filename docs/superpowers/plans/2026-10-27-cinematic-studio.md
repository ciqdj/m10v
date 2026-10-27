# M10V cinematic studio implementation plan

> Execute inline with superpowers:executing-plans. User approved direction C and full-library export guidance.

Goal: Replace the earlier dashboard presentation with the approved cinematic workspace while preserving target-specific configuration, import, export, persistence and recovery behavior.

Architecture: Reuse the existing native-library and studio state/controllers. A dedicated cinematic shell owns panel navigation, focus, scene and selected-film presentation. Export completion uses the existing authenticated SD export endpoints with the full catalog for the captured model; configuration and firmware receipts stay intact.

Constraints: Keep black/charcoal, warm gold and ivory; preserve GR III 10-slot and other target 5-slot restrictions; do not claim photographic background is a true firmware preview; no firmware/runtime changes or deployment. Working in existing isolated worktree, preserving prior dirty changes.

Review focus: preview must never add a film; new panel layouts must not detach controls from their controller roots; hidden panels must not trap keyboard focus; build completion must refer to the exported model and catalog; mobile dock must not cover the last control.

- [x] Cinematic shell and source/film/imaging/power/export layouts, keeping every existing control and event binding.
- [x] Catalog preview separate from selection, selected-film management and keyboard-safe panels, preserving undo and model limits.
- [x] Build completion with full compatible SD library download and explicit SD/M10V installation instructions; native-only functionality gating.
- [x] Desktop/mobile browser review, focused state/export tests, source/build identity checks and regression report.

Validation: existing navigation, model import, editor history, workbench state, zoom, power-images and version/bridge tests; new full-library payload and failure tests; browser checks at 390/768/1440 and actual source import, panel navigation, selection/history and download flow. No device acceptance claim.
