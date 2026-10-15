# SD library v2 integration candidate

Status: offline verified; physical-camera acceptance and realtime film preview remain outstanding.

## Reported regressions and changes

- The first SD branch used an older base and omitted `daily/800t-rebuild` (480a15e). Merge that branch, preserving its energy renderer, native FN detail controls, capture adapter and shared M10V3 settings journal. These native files match that branch exactly. Existing M10V3 settings take precedence; M10V2 migration runs only when no valid M10V3 journal exists.
- ImageControl now has a separate Chinese `胶卷库` entry. Choose one of five slots, then a film, then OK. Browsing does not activate the target slot. Successful snapshot persistence and journal commit precede activation. MENU returns one level. Existing settings are under `胶卷设置`; 800T FN detail retains 光晕强度、扩散范围、高光阈值、颗粒、柔光.
- The user clarified that unchanged effects refer to realtime live view. This is unresolved: current rendering hooks process saved still JPEGs. Changing the label or installing a film does not implement live-view processing. Research points to separate ImageTuningLiveView::Make (0x536DDECC) and still Make (0x536DD8F0); their shared ISP subtunings do not establish a safe equivalent of the post-RGB JPEG renderer. No speculative preview hook is shipped.
- SD records now contain the renderer source digest at offset 8448. Full-record authentication rejects stale packs. Export a fresh matching pack after this upgrade.

## Verification

- Full Node suite: 190 tests, 184 passed, 6 optional-fixture skips, zero failures.
- Python suite: 112 tests, 104 passed, 8 initially skipped. The skips were inherited historical-fixture markers in the fresh-build menu subclass. Corrected that marker; reran the complete ADJ/menu module: 11 passed, zero skips. Thus all 112 suite cases have passed across these runs.
- Added ARM integration coverage installs two distinct films into the same slot, removes SD, executes the real capture renderer, and verifies different output pixels. This proves the emulated saved-image path, not physical live view.
- Added Chinese root/slot flow, browsing cancellation and native detail resource coverage. Existing corruption, short read, AppData failure and journal tests remain passing.
- Generated contract check and independent review passed. Candidate was decoded and independently reread from disk; integrated component audit verified.

## Candidate

Ignored output: `builds/sd-library-v2/delivery/`. Firmware `fwdc239b.bin` is 31,275,544 bytes, SHA-256 `73cb9f3a67ae2e4f8b66bb0c326a506a125917ce54e5968fdfd45dfc7a56348c`. RTOS growth 511,568 bytes. It preserves the previous 800T delivery configuration: film IDs 33/64/54/56/37, timestamp, aspect, level and negative grain extensions. Saved camera settings may override initial defaults.

Fresh `M10V-SD-films-33.zip` contains all 33 supported films. Extracted FILMS.M10 is 409,600 bytes, SHA-256 `77d1a7502c34eab7db79250b6f9375aac0886b766fab3f23f53d8b2081a2da80`. Copy only FILMS.M10 into SD-root M10V when updating; preserve camera-created files.

No flashing or deployment was performed. Physical menu/font behavior, FN controls, saved JPEG output, SD removal, reboot persistence, write durability and existing camera functions still require device regression. This candidate does not close the user's realtime-preview requirement.
