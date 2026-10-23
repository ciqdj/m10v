# GR III crop/playback repair plan

Goal: stabilize XPan/6x7 with native focal crops, keep each shot's selected film, make additional spatial effects opt-in.

Scope: GR III 2.10. Preserve dirty workspace, film IDs/LUTs, five slots, RAW ownership, persisted user settings, HDF feature, original controls and non-crop output geometry. No camera attached; offline evidence is not device acceptance.

| Area | Before | Required | Evidence |
|---|---|---|---|
| Live crop | XPan mask only at 1x; 6x7 writer uses fixed sensor rectangles across AF paths | Masked view uses original full-height focal-crop rectangle consistently; output JPEG/DNG unchanged | ARM actual native rectangle setter + dimension functions, all Q13 crop magnifications |
| Film capture | Encoder rejects a stock SI tone before reading frozen selected-tone snapshot | Valid owned snapshot decides slot; foreign/stock-only frames remain untouched | ARM queued first-shot carrier-lag reproduction, invalid ownership and RAW gates |
| Extra effects | Grain/halo automatically enabled on selecting/resetting some films | Fresh selections/defaults/reset off; manual values and existing journal survive | Host + JS state/selection/reset/storage regression |

- [x] Add reproductions and verify failure on current source.
- [x] Fix geometry with original native setters and preserve nonmasked/capture routes.
- [x] Fix snapshot ordering and per-frame carrier handling; investigate embedded preview source.
- [x] Align opt-in defaults across C, JS and reset; retain explicit stored settings.
- [x] Run relevant host/ARM and complete Node suite, inspect final BIN, package unique candidate with hashes/provenance/recovery steps.
- [x] Explicit device acceptance received for r3: user “发布github和宝塔，测试OK” (2026-10-22).
- [ ] Publish GitHub and Baota under release workflow after integration verification.
