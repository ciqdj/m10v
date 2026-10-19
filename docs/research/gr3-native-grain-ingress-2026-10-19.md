# Original GR III grain sizing and execution ingress

Basis: original RTOS SHA256 `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`, VA `0x53000000`.

This identifies a concrete native grain integration using the original spatial
stage, allocator, work buffer, graph, completion event, and release. It does not
move colored grain, leak tint, or red halation into that graph.

## Three coordinated hooks

| BL site | Original word | Target | Purpose |
| --- | --- | --- | --- |
| `5351361c` | `ebfffee7` | `535131c0` | Request effect-stage gate |
| `535033d8` | `ebffff1b` | `5350304c` | Spatial settings for workspace sizing |
| `53503aa0` | `ebfffd69` | `5350304c` | Spatial settings for actual execution |

Each wrapper must run the displaced original function at the original SP and
preserve its original outputs, flags, VFP state, and callee-saved registers.
Native grain override is a post-original settings edit; changing SI is unnecessary.
Both settings sites must use the same immutable per-recipe snapshot. A default
request with grain enabled needs a 24,000,000-byte plane at6000x4000. Patching only
execution is incorrect even if it happens to work with an existing large buffer.

### Gate

`5351361c` has `r0=request`, `r1=ShootingInfo`; its original target is
`535131c0`. The latter writes `request+24` (one byte) and returns void. After
calling it, set this byte to1 only for an admitted frame snapshot with nonzero
native grain. Preserve original behavior for all other frames. Existing patches
at this callsite must be composed; a second independent BL replacement would
remove the first patch.

`53513218` handles tones11/12/17/18/19/21 using shading and clarity only, so even
SI+795 nonzero does not enable stock grain for those tones. `53513240` handles
13/15/16/22 and also checks grain. Thus settings-only overrides cannot guarantee
the graph runs for all film carrier tones.

### Sizing

At `535033d8`, original inputs are:

- `r0=params=fp-4c`, native parameter object0x34bytes;
- `r1=*(C+34)`, ShootingInfo;
- `r2` is the original stage scale/crop flag; keep it unchanged;
- `ip=C` at wrapper entry, from `535032c4: ldr ip,[message+8]`.

Save C before calling the original function: ip is caller-saved. The original
settings pointer is `params+10=fp-58`, initialized by535033d0..d4. After settings,
`535033e8` calls original `53680dbc(context,params,&required_bytes)` with
context=`*(module+8a0c)`. The original stage queries substages and reports their
maximum workspace; no graph is submitted in this branch. Module sizes and
allocates through the original planner, including its original alignment slack.

### Execution

At `53503aa0`, original inputs are:

- `r0=params=fp-7c`;
- `r1=*(C+34)`, ShootingInfo;
- `r2=r7`, original scale/crop flag;
- `r4=C`, loaded from message+8 at535036e4;
- `params+10=fp-88`, set at53503a90..94.

After settings, original `53503ab4` invokes53680dbc with r2=0. Params+2c/+30
are the original workspace and capacity. Keep them unchanged. Original
53680f44..58 checks queried requirements before actual processing.

## Ownership correlation

DigitalFilterProcessConfig vptr is `53d0fc60`, typeinfo `53d0fb0c`, name pointer
`53d0fb18` (`26DigitalFilterProcessConfig`). Constructor5350f940 loads literal
5350fe00, and5350f9c4 writes this vptr at destination recipe+4320.

Original setup5350ed8c..edcc populates C fields:

| Field | Value | Writer |
| --- | --- | --- |
| C+30 | sourceRecipe+1a8 |5350edb8|
| C+34 | `*(sourceRecipe+44c8)` ShootingInfo |5350eda8|
| C+38 | `*(sourceRecipe+5c)` request |5350edb0|
| C+3c | `*(sourceRecipe+435c)` digital filter descriptors |existing retained field|

Source/destination recipes can differ. Derive sourceRecipe from C+30, then
validate recipe vptr, private state ownership/CRC, SI identity, and original
request pointer. Do not derive the source recipe by subtracting4320 from C.
At the gate there is no C input; correlate `r0=request` and `r1=SI` with the
already-owned frame snapshot through its original creator or a checked lookup.
Do not invent a recipe pointer from SI or request pointer arithmetic.

## Values and actual native behavior

Settings are12bytes: s16 shading+0, clarity+2, grain+4, HdrTone+6, f32 scale+8.
Original5350304c maps SI grain1/2/3 to processing3/2/1, respectively.
Granulation5367ad3c uses processing1→amplitude256,2→128,3→64. For a UI strength
that increases1..3, use processing=`4-strength`. Native strength values are not
pixel size; this does not establish equivalence to the current multiscale or
colored grain renderer.

The original graph reads the Y plane and writes Y. No color/chroma grain route
was identified in this function. Its original graph execution path remains
5367b404 submit→5367b410 wait→5367b418..4ec release/cache/destruction. Reusing
these paths adds no independent graph/event or unowned DMA lifetime. Retain
original failure behavior; never mark native grain as applied merely because
settings were written or workspace was queried.

## Grain size remains a real executed parameter

`m10v_isp_native_effects_noise_shape(noise,bytes,width,height,stride,size)`
correlates the ORIGINAL RNG workspace before the original cache clean. Size0
preserves every byte; sizes1/2 apply causal separable2/3-tap box filters. Exact
integer mid-CDF curves restore the uniform8 marginal after the lowpass. This
preserves all original photo dimensions; it never filters/downsamples photos.

The scalar reference uses128B of tile history. The optional `M10V_NOISE_NEON`
implementation traverses horizontal samples and vertical rows in reverse, so
causal neighbors remain unchanged until read; no history row is needed. VHADD
computes the two-tap floor average. For sum<=765, SQDMULH with10923 computes
`floor(sum*21846/65536)==floor(sum/3)` exactly. CDF gathers remain scalar.
Compile this object separately with `-O2 -mfpu=neon -mfloat-abi=softfp` and
`-DM10V_NATIVE_NOISE_ONLY -DM10V_NOISE_NEON`, retaining integer AAPCS at its
boundary. Do not enable softfp for the entire recipe translation unit.

Locked Cortex-A9 compilation emits1056bytes text+512bytes read-only CDF data;
stack usage76bytes. Compared with the scalar implementation's1036bytes total,
the NEON implementation adds532bytes and reduces fixed stack from184 to76bytes.

24MP host statistics below use independent uniform8 noise, seeded7351, not a
camera-exported noise plane. They test the creative noise model, not physical
IIP grain appearance or camera timing. Interior autocorrelation samples use
1,2,3-pixel offsets, with every fourth row/column sampled after an8-pixel margin.

|size|mean|variance|variance / ideal uniform8|horizontal lag1|horizontal lag2|
|---|---|---|---|---|---|
|0|127.4983|5463.1695|1.00035|-0.00102|0.00118|
|1|127.5014|5421.7940|0.99278|0.48420|0.00004|
|2|127.4594|5422.2093|0.99285|0.64990|0.32135|

Vertical lag1 is0.48494 and0.64965 for sizes1/2; size2 vertical lag2 is0.32137.
Thus the larger size has a wider correlation radius while retaining essentially
the same mean and variance. Real-camera calibration must assess grain through
the original LUT/Blend and original amplitude/ISO/exposure conditions.

Unicorn executes the actual Cortex-A9 implementation on6000-wide frames with
heights4/8/12. All measured counts follow a checked affine per-row relation:

|size|scalar extrapolated24MP instructions|NEON extrapolated24MP instructions|
|---|---|---|
|0|33|35|
|1|627081931|121164059|
|2|723081931|152944059|

These are instruction workcounts, not camera latency measurements. The reduction
is80.68%/78.85% for sizes1/2. Generated local measurements live in ignored
`builds/gr3-isp-research/native-grain-noise[-neon]-statistics.json`.

`tests/test_gr3_native_grain_noise_neon.py` compares actual ARM NEON output with
the scalar reference for all three sizes on a full6000x4000 plane, vector tails,
padding, singleton dimensions and widths through6000. It guards r4-r11, SP and
d8-d15. `tests/test_gr3_native_grain_noise_hook.py` additionally executes the
original dispatcher and original Granulation through the installed RNG wrapper,
verifying the real saved-frame delta0x60 and original caller r4=C. The wrapper
requires its configured original dispatcher return PC (coordinated stage wrapper
entry+16), and Granulation's saved return PC53681050. It calls the original RNG
first and preserves its complete post-call GPR/flags/FPSCR/d0-d31 state. Invalid
or foreign frame chains leave the original RNG path intact.
