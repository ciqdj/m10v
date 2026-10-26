# GR III 2.10: measured CPU fallback and processing-ingress repair

Base: GitHub main `2d5fc71870cccb65d4a81adfec6114256e2ec448` (fetched again
for this iteration). Prior ISP-fit candidate d124947 was replayed as a8826a8.
This branch remains a test candidate; no firmware merge into main.

## Device measurements

Three supplied debug pages are CRC-valid and agree on build `879dccce`, the
identified diagnostic BIN. They contain one 5219 capture (film62, tone25).
The capture profile is complete; two IO pages merge without conflict.

| Measured phase | Milliseconds |
| --- | ---: |
| Capture adapter entry to exit | 19094 |
| CPU color stage | 18823 |
| Cache writeback stage | 267 |
| Settings-read stage | 2 |
| JPEG submission | 20 |
| JPEG event wait | 83 |

Native-completion mask is **0**, CPU residual stages **1** (color), settings
source **0** (durable load, not recipe snapshot source4). Thus the expensive
whole-image CPU color branch ran on the device. This is not a conjecture
about SD speed or JPEG encoding. The JPEG wait returned successfully; these
pages do not prove file durability or measure all later filesystem work.

The preceding frozen-UI/stock-SI hypothesis is not this capture: SI tone is25,
a valid M10V carrier. IO trace overflow dropped7 observations; absence of an
ISP observation event alone would not prove nonexecution. The independent
capture source/completion/residual events establish the failed handoff.

## Root and repair

The former snapshot site5351ae44 belongs to5351ae2c, which disposes current
buffer references through5352197c and reserves the next raw recipe. It is not
the processing-task producer. Original5352197c enumerates buffer IDs, invokes
release helpers and clears their references. Calling it submission in earlier
notes/tests was incorrect. Commit a895cda0e347a33c0a2db04a8cfa615dcd939161 moved
snapshotting to this wrong site (Oct21); this dates the source regression,
not an identification of the user's remembered early binary.

Original5351ea9c(owner,recipe) builds processing packets at
recipe+3b0+24*kind and metadata at recipe+5f0+32*kind, then sends them via
536abd28. The repaired hook freezes the recipe at this producer's entry,
before any of those packets can execute. It reads the exposed frame's own SI
tone, not a newer UI choice. Subsequent tasks retain the same snapshot.

The scheduler may hold backend locks. The helper now reads only the validated
UI-owned cache and checks its publication/mutation state, without filesystem,
allocation or lock acquisition. UI journal loading still publishes that cache.
An unavailable cache does not fabricate successful ISP completion. Native
frame/owner/SI/CRC completion guards remain active. The old5351ae44 instruction
is restored to stock; independent HDF reservation timing is unchanged.

This fixes the demonstrated missing-ingress path. ISP completion is established
before the stock image resizing/encoding paths, so immediate review can inherit
the processed image rather than depending on late CPU recoloring. Device
latency, review appearance and blackout recovery still require the RC2 run.

## Verification and limitations

Before repair, the new original-task-producer regression failed all four
5219/D76 stage0/stage1 cases: no recipe snapshot existed before Develop.
After repair it passes. It executes the original packet/metadata producer;
OS mode/setup and transport are explicit service boundaries. This covers the
actual device command order19/0/16/1/8/9/2/4 rather than manually supplying a
snapshot or invoking a buffer-retirement hook first.

41 targeted ARM/final-BIN checks passed: all24 task kinds, stage0/1,
post-submission UI/state changes, real journal-load/cache publication, cold/busy
cache zero-I/O, GPR/SP/LR/NZCV/D0-D31/FPSCR preservation, ordinary built-in fits,
Charmera/Pixel exclusions, SD compatibility, view recovery and debug-page
integrity. Authenticated ordinary captures have unmapped24MP planes and fail
on pixel/cache/allocation/storage access; the repaired path returns without
those accesses. Independent Node auditing accepts the final BIN and rejects
an owner+f0/wrong-recipe wrapper even with its runtime hash repaired.

Full Node run:364 tests,310 passed,44 failed,10 skipped. It is not a green
repository suite. Failures include stale version4/five-slot/catalog expectations
and missing .runtime compatibility assets. On untouched main, selected
catalog/slot/Charmera/SD tests reproduce7 failures out of20; native-build,
Node-path and route tests reproduce the same3 failures as this branch (e.g.
95 vs88 films and37 vs30 visible entries). Not every failure was separately
classified, and no unrelated expectations were rewritten for a green result.

Independent review caught the supported non-live-preview debug v7 path: its
cache had previously been compiled out with Live Make. Cache ownership, UI
publication, controller allocation and HDF offsets now follow snapshot ingress
independently of the actual live-preview hook. A full v7 export regression
failed before the follow-up fix and passes afterward, including durable cache
publication and zero-pixel encode. Headless direct Python research builds
without the SD settings owner must supply snapshots through the explicit API;
automatic cache-based ingress is not available in that research configuration.

User's MENU hang has no supplied menu-channel evidence and remains unlocalized.
Do not claim it fixed because the capture bottleneck is repaired. No ISP
hardware, DMA, physical scheduling or camera performance is emulated.

## RC2

GR III2.10 only; debug enabled for confirmation. Existing camera journals have
priority; no reset or ABI migration is introduced. Charmera/Pixel retain their
special CPU renderers. Halo and custom-LUT exceptions remain explicit.

BIN SHA256: `5d329f546bcd7df52962a4fd99da0e590da3e805aa4f8205db8b53a4f31c083f`.
151 checked hooks,32,111,448 bytes. Receipt/manifest record the complete source
and configuration fingerprints; camera_tested remains false.
