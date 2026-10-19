# GR III implementation and candidate 2a3fa20c

The full original ISP objective remains incomplete. This change implements an exact
CPU throughput improvement and actual BE file diagnostics, plus a separately tested
native multi-axis writer/target fitter. It does not activate an unproved hardware graph.

## Implemented photograph path

`M10V_TEXTURE_NEON` links `m10v_texture_block8` into the actual firmware runtime and
dispatches complete eight-pixel blocks from the existing full-color texture path.
The block includes YUV/RGB conversion, warm leak exposure, all3375 RGB LUT entries
with the same tetrahedral interpolation, luminance-dependent grain, channel noise,
and the original YUV422 pair averaging. Every original round, clamp and tail is retained.
The existing exact color-cache path remains available for repetitive scenes; invalid
batch preflight or unbatchable tails continue through scalar processing.

There is no new image-sized allocation, persistent pixel pointer, worker queue, DMA,
RAW access or changed encoder/save call. The additional batch parameters occupy76
stack bytes; the isolated ARM block module is2736 bytes. The final runtime is638760
bytes.

Actual linked ARM full-width comparison uses6000x2 visible pixels, stride6008,
seedffffffff, real candidate LUTs and complete random Y/C input. All visible pixels,
padding and output bytes match the previous full implementation.

| Target path | Grain Q8 | Leak | New/previous ARM instruction work |
|---|---:|---:|---:|
|5207|0|0|0.5851|
|5207|768|8|0.5733|
|Phoenix / each RED variant|0|0|0.5441|
|Phoenix / each RED variant|768|8|0.5485|

These are instruction counts, not physical milliseconds or a promise of stock-speed
playback. The benchmark measures the fused texture path without its optional color
cache and does not accelerate the800T source/composite phases or legacy matrix loop.

## Actual file service and buffer evidence

The new checked hooks at5350b380/5350b384 enclose original53697658, preserving its
original SP and three argument registers. Optional656-byte call-owned diagnostics
record200/201 clocks,202 descriptor stage/status and203 bounded opaque context fields.
They do not run filesystem calls inside the original callback. Descriptor results
distinguish open, metadata and close errors. The context remains explicitly unassociated
with a recipe until its topology is demonstrated; native service success is not card
durability.

The checked53521e18 hook observes the unchanged original pool dispatch return.
Event184 never forces a free. It can still be lost if no safe drain follows the last
JPEG192 before recipe destruction. Thus the buffer-release verification objective
is not complete; absent184 is not evidence of a leak. No guessed RAW pointer,
destructor filesystem call or new RTOS message protocol was introduced.

## What native ISP can currently establish

The new frame-owned native multi-axis writer covers both complete matrix banks,
selectors, boundaries, controls and final matrix through original536df55c. Existing
local GR III camera experiments establish active12-sector behavior, beyond merely
showing that a register writer ran. The current target fitter jointly optimizes a
relative matrix, continuous sectors, curves and post matrix, then includes actual
CCA/CSP field quantization and the existing curve-helper rounding.

Independent65536-color scores: Phoenix medianDE00=.2803/P95=.6045/max1.5823;
5207 median1.8404/P95=4.5529/max15.8826. Phoenix passes the stated numerical gate;
5207 fails. Neither generated target is enabled in this candidate. The new complete
camera chain is not yet validated, and moving color before CPU leak/halation changes
their operation order/source. Successful fitting alone does not solve that integration.

Current spatial filters truncate after each separate axis and preserve full unsigned16
energy. A single fused convolution changes pixels. Existing native setters do not prove
tap scaling/edge rules; existing abort/release predicates do not prove drained DMA.
Consequently the present evidence supports native color processing, but not a claim
that all complete spatial effects can already execute safely in the new graph.

## Candidate evidence

Firmware SHA256 `b26e045f3807f92ad3a2e76aea9e9ba99124eba9c05e83a330f2a35fcccb7f85`.
Build ID2a3fa20c. Original settings and extension configuration retained; lifecycle
patch inventory25, total runtime638760. Manifest explicitly records
`full_isp_effects=false`, `save_chain_fixed=false`, `camera_tested=false`.

Verification uses a fixed source snapshot under `/private/tmp/m10v-gr3-v5-validation`
after source fingerprints changed during an earlier shared-checkout test run. All
manifest source files were compared against the working checkout before packaging.
74 targeted ARM/integration/decoder tests pass;3 checks re-extract the actual final
firmware and compare its full capture pixels against scalar processing. Full Node
suite results and camera test instructions are included in the package verification.
