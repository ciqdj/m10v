# Native spatial exactness: current evidence

Firmware: GR III 2.10 RTOS SHA256 `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

An exact hardware compiler for the current full spatial effects is **not yet supported by the available evidence**. This is a lack of established hardware semantics, not a proof that the hardware cannot implement the effects. No custom SPF graph is activated.

## Operations established

- Loader→Store original entry `0x53681260`: original graph construction, descriptor binding, submit, event wait and release control flow executes in ARM tests. Hardware pixels are not emulated, so even format6 identity pixel behavior still needs camera confirmation.
- Original spatial-stage dispatcher `0x53680dbc`, actual caller `0x53503ab4`: `r2=0` selects execution; nonzero `r2` selects sizing. The adapter executes stock substages without a second independent event. It does not replace the custom CPU effects.
- SPF lowpass setup `0x5367a7c0..0x5367a810`: original constructor flags contain `0x1fb00`, mode setter `0x5377ae04` receives zero, and `0x5368bd78` receives 17 halfwords. The setter copies low13 bits into register-image fields; it does not evaluate a convolution or reveal signedness, binary point, tap positions, intermediate clipping or border replication.
- GPC setters expose raw20 values and 2-bit rounding fields. Their serialization is tested against the original ARM code; their arithmetic meanings remain unproved.

## Exact software contract and rejected shortcuts

`halation_energy.h:energy_blur` performs horizontal `(left + 2*center + right)>>2` into uint16, then vertical `(top + 2*center + bottom)>>2`, repeating each pass with replicated boundaries and distance1 or2. Additions widen before shifting. The maximum energy is49928, or53048 with Phoenix peak supplementation, so a14-bit-only path loses information.

A single 3×3 outer-product convolution with weights `[1,2,1]×[1,2,1]/16` is not exact. At a center whose neighborhood rows are `[0,0,0]`, `[0,0,2]`, `[3,3,3]`, separate horizontal floors give `[0,0,3]` and final0; the fused sum gives floor(16/16)=1. An exact hardware implementation needs observable truncation at both axis boundaries. Repeating or fusing multiple blur passes introduces the same problem.

`energy_source` is integrated squared excess with zero contribution for missing cells, not maxpool. Phoenix adds a bounded peak term to the integrated source. A fixed linear convolution cannot itself implement maxpool: on two sample signals `(1,0)` and `(0,1)`, each maximum is1, while their sum also has maximum1 rather than2. This disproves substitution by a linear kernel, without claiming SPF has no undocumented nonlinear modes.

Source extraction depends on thresholds and, for800T, reconstructed red, followed by squaring. Compositing depends on both original-pixel brightness and spatial energy, bilinear reconstruction, protection factors, clipping and shared chroma. A fixed matrix or fixed linear SPF kernel alone cannot implement these conditional/product operations. Additional hardware LUT/multiply/max stages could potentially express them, but their required numerical and spatial behavior is not established.

## Ownership limitation

`0x53778490` returns `!(status&4)`; `0x53778474` returns `(status&3)==3`. The original release loops until both are false, with finite polls and assertions that log and return. These functions do not establish generic DMA-idle semantics. `AbortMultipleImageProcess` at `0x5377876c` clears control low2 bits and returns without status acknowledgment; ARM tests verify unchanged status for all low3 status combinations.

Consequently neither a completed event bit nor return from original release proves custom DMA buffers reusable after failure. Node insertion into an existing stage still requires compatible descriptor ports, exact numerical semantics, completion identity and proven failure cleanup. A private event queue alone would isolate event consumption, but would not stop DMA or protect subsequent captures.

## Minimum evidence for an exact compiler

1. Hardware/manual or measured impulse responses establish all17 tap coordinates, coefficient scaling/sign and applicable mode, at distances1 and2.
2. Ramps, negative-coefficient patterns and maximum-range inputs distinguish rounding, accumulator range and pre/postshift clipping; edge impulses establish replication.
3. Two explicit passes preserve the software axis-floor behavior; software differential tests cover randomized full uint16 energy inputs, skinny/partial cells and repeated passes.
4. Original owner abort/reset is observed to acknowledge quiescence before descriptors, scratch or context can be reused; delayed/duplicate events cannot complete a later transaction.

Until these are established, emitting guessed coefficients would be an approximate effect, incompatible with the requested no-quality-loss contract.
