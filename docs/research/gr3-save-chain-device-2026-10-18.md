# GR III f5ea39a0 device results

Firmware SHA-256: `757304099199d505906fda2d1bc39bcf8828b5163442392bb701bc7fc0feddb0`.
The six Desktop pages were copied unchanged into ignored `builds/gr3-save-chain-device`.
All pages pass CRC; merged history contains 147 records, no rejected or unmerged pages.
Capture history begins at sequence18, so the first frame's internal profile is incomplete.

## Measured critical path

All durations below are milliseconds. Owner render includes instrumentation around the
CPU adapter; inner profile measures the adapter itself. These are nested intervals and
must not be added together.

| Film | Owner render | Inner adapter | Pre-spatial | Color/fused texture | Post-spatial | JPEG submit | JPEG wait |
|---|---:|---:|---:|---:|---:|---:|---:|
|800T|12978|not retained|not retained|not retained|not retained|28|164|
|5207|27219|26884|0|26882|0|144|161|
|Phoenix II|30154|29970|1832|25872|2265|11|158|
|HARMAN RED|14024|14004|0|14002|0|8|157|
|Gold 200|16348|16327|0|16325|0|11|158|

Zero-duration spatial phases mean no separately timed work in that stage; they do not
establish that an effect was disabled. Some texture work is fused into the color loop.
The combined color/fused phase does not yet distinguish LUT cost from texture cost.

Five allocation-return events report success; five renders return0; all five original
JPEG wait calls return1. This narrows the dominant observed delay to CPU effects, rather
than the measured JPEG wait. It does not establish card durability or rule out other
black-screen causes.

The last three owner intervals run as follows (same device monotonic clock):

| Film | Owner enter | JPEG wait return |
|---|---:|---:|
|Phoenix II|93244|123567|
|HARMAN RED|123576|137765|
|Gold 200|137773|154290|

Only9ms and8ms separate those wait returns from the next owner entry. The sequence
occupies61.046 seconds from Phoenix entry to Gold wait return. This supports sustained
serial processing pressure; without shutter-accept timestamps it does not prove queue
depth, actual time spent black, or when each exposure was accepted.

## ISP and frame ownership

All five event198 records have tag0x49535001 and status7 (observer), sequence380,
tones12/18/19/20/21. Thus the real ISP hook executes, but it does not apply the custom
effects. All four complete inner profiles use the per-frame settings snapshot. Snapshot
ownership is working in this run; it has not removed the CPU bottleneck.

The decoder now labels observer mode explicitly, with `effects_offloaded=false`, and
retains owner-entry and JPEG-wait-return clock values. Unknown statuses remain unknown.

## Save evidence remains incomplete

No events180/181/182/195/196/197 occur. The installed synchronous file-worker trace
therefore has not demonstrated coverage of this capture path. Logger contention can
also skip a batch, so absent events alone cannot prove that worker never executed.
No event currently proves durable DNG/JPEG completion, and no allocation-return event
proves an actual backing-store release. Do not remove RAW guards or force-free buffers.

Further static investigation finds the BE still FileProcessError consumer at
0x5352420c, with a call
to0x5369be28 at0x53524244. This is a lead for tracing the actual file-status path,
not yet a validated hook or a save-completion timestamp.

## Remaining implementation gate

This run does not meet near-stock playback and does not validate a full ISP migration.
Native graph activation still needs proven pixel-equivalent color/spatial operations
and an abort/idle protocol that prevents stale DMA and completion events from reaching
later frames. The existing stock release path can return after busy-poll assertions;
its return value is insufficient as proof of idle. No new firmware is justified by
the decoder/report change alone.
