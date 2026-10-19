# GR III: recovered black screen, actual device bottleneck, V6 changes

The supplied fwdc239b.bin exactly matches V5 delivery (build2a3fa20c, SHA256 b26e045f3807f92ad3a2e76aea9e9ba99124eba9c05e83a330f2a35fcccb7f85). Four CP/IO pages merge to148 records; CRC pages valid, no rejected/unmerged pages. Read-only originals retained in builds/gr3-v5-device-2026-10-19. User confirms recovery and complete DNG/JPG pairs; this run proves long processing, not lost files or permanent deadlock.

## Device time, not emulation time

| Capture | Custom adapter | Before color | Color/texture | After color |
|---|---:|---:|---:|---:|
| First800T, prefix overwritten | owner render13271ms |9766ms|3472ms|0ms|
|5207|30335ms|0ms|30333ms|0ms|
|Blue Phoenix|32805ms|1710ms|28767ms|2325ms|
|Tone20, unknown selected film|rejected RAW0|not executed|not executed|not executed|
|Tone21, unknown selected film|rejected RAW0|not executed|not executed|not executed|
|Final800T|10719ms|7643ms|3075ms|0ms|

All six original encoder waits return1 in158–194ms. This does not prove disk durability or the complete encoder duration. Old file/BE probes have no events. StoreImageProcess opcode01000001 tail-calls5350bfb0; old probe5350b380 belongs to opcode01000002. Therefore no saved-file timing is inferred from absent events.

The two RAW0 cases show exact known planner release caller5351fd54 -> pool id1/backing return1 -> original setter clears R2f4 andR60 -> original release return -> JPEG capture. They are not OOM evidence and their skipped effects must not count as speed gains.

## Implemented V6

1. Correct the cache-selected route which previously bypassed block8. Cached and uncached execution now both retain original full RGB cache semantics, effects, dimensions and output bytes. New event134 proves batch pixel coverage, cache hits and fallback flags.
2. Add a recipe-owned48-byte RAW lifecycle token at50c0; total allocation50f0. Only the exact successful original release/pool/setter sequence allows processing current YUV after RAW has legally retired. Wrong SI, failed pool, fresh setter or missing proof reject. This token is independent of debug records and never dereferences old RAW addresses. Released path does not read R230 or sticky44d0. Existing JPEG/preview/request/SI/plane/scratch overlap checks remain.
3. Add actual generic module call/return and Store opcode observation. Store-only drain is after handler return and local refcount mutex release, before owner notification may retire recipe. It preserves original call SP, all GPR, D0–D31/FPSCR and flags. It does not change actual file writes, waits, pool release decisions or timeouts. Transitive global filesystem lock absence and durable file completion remain unproved.

## Evidence and remaining limits

The V5 original binary and V6 actual linked cached entry have identical whole Y/C and padding output on6000x2 representative cache-selected images. Texture instruction count decreases30.92–32.12% with grain768+leak8,16.82–21.31% with color alone. These are ARM instruction counts, not camera latency predictions. Cases execute12000 batch pixels, flags7, no fallback.

Original native pool dispatch/setter retirement followed by complete capture is regression-tested for films35/66/67/68 on128x96, with inaccessible R230, trapped sticky44d0 and mapped old RAW reads. Full Y/C including padding/canaries equals the live-RAW result. Negative proof cases reject without modifying pixels.

V6 remains a CPU full-effects renderer with native ISP observation. Complete arbitrary LUT plus spatial/grain/leak effects have NOT been activated in a proven original hardware graph. Original graph release may return after busy-state assertion; DMA quiescence/late completion and exact color/spatial equivalence remain blockers. This release must not be described as full ISP migration, seconds-to-instant playback, solved black screen, or proven no-loss capture. New hardware logs are required to measure actual improvement and actual Store completion/order.

The RAW token attests completed retirement only and relies on the unchanged native serialization of operations on one recipe. It does not lock a concurrently freeing live RAW. Cache-hit stats count successful lookups; a partly hit four-lane half may still recompute the whole half.
