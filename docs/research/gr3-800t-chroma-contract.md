# GR III chroma contract — resolved by original CPU execution

**Final conclusion:** shared low descriptors format1/address mode2 use Cb then Cr, unsigned8-bit storage, neutral128. The proof links original software pixel conversion, format1 CPU fill, and the official low-descriptor adapter. No NV16 convention, external runtime label, or hardware enum guess is used.

Reproduce with `.venv/bin/python scripts/analyze_gr3_800t_chroma.py /path/to/decoded/rtos.bin --out builds/gr3-800t-reverse/chroma/chroma-proof.json`. Integration tests require `GR3_RTOS_PATH=/path/to/decoded/rtos.bin .venv/bin/python -m unittest tests.test_gr3_800t_chroma -v`. The input must match the locked hash.

Formal report `chroma-proof.json` contains exact anchor address/preimage/meaning plus9pixel cases,28original fill/adapter cases across422/420 and scalar/NEON widths with allocation padding, and one independent420consumer run. All5tests passed with the locked RTOS.

RTOS SHA-256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

## New exact observations

* Function entry `0x537672ac` is the function whose assertion/debug identity uses `ConvertYCbCrToRgb` at `0x54034970`. It obtains its source descriptor through `[r1]`, uses descriptor `+4`, `+8`, `+c` as input addresses, and source format byte at `+0`.
* `0x537676e4` bytes `043094e5` loads the Y address, `0x537676fc` bytes `081094e5` loads combined chroma address, and `0x5376770c` bytes `0c1094e5` loads third address. Their stores into IIP pixel format information are at `0x537676f4`, `0x53767704`, and `0x53767718`.
* `0x5376762c..0x53767654` copies exactly 64 bytes from `0x538f4450` as its color conversion matrix. Interpreted as signed 32-bit integers, this is:
  `[4096,-1410,-2925,4335], [4096,7258,0,-7258], [4096,0,5743,-5743], [0,0,0,0]`.
  The matrix rows numerically correspond to G, B, R respectively for Y, Cb, Cr inputs with Q12 coefficients: G=Y-.344Cb-.714Cr plus offset; B=Y+1.772Cb plus offset; R=Y+1.402Cr plus offset. The coefficient interpretation is inference from constants, not an executed pixel conversion.
* Reverse matrix at `0x538f4490` contains `[1223,2404,467,0], [-691,-1357,2048,4096], [2048,-1715,-333,4096], [0,0,0,0]`. It is copied by the RGB->YCbCr path. Again actual arithmetic/scaling happens in hardware.
* Exact IIP config path: `0x5377448c` calls `0x53773c58`, `0x53774394`, then tail calls `0x537740cc`. `0x53773c58` dereferences config+0x50 as pixel-format information. Addresses `+0x24/+0x28/+0x2c/+0x30` are passed respectively to setters `0x5377a1f0/0x5377a24c/0x5377a2a8/0x5377a304`. Their own assertion names are `SetAddressYG`, `SetAddressCbB`, `SetAddressCrR`, `SetAddressAlpha`.
* Those four setters mask low 3 address bits and store the addresses to virtual pixel table offsets `+0x24/+0x28/+0x2c/+0x30`. This proves that the converter's combined-chroma pointer occupies the IIP **CbB address field**, while the CrR address field receives zero for the known descriptor path. It does **not** establish the ordering within the combined buffer.
* `0x53779f7c` packs four chunk-order selectors into the top byte of virtual pixel table word0. Values each are two-bit fields; the first argument ends at bits24:25, second26:27, third28:29, fourth30:31. `0x53773d18..0x53773d5c` gets these from pixel info `+0x34..+0x37`.
* `0x53779fbc/0x53779fd8/0x53779ff4/0x5377a010` put pixel info `+a..+d` into virtual table word1 bits0..3. `0x5377a048/0x5377a064/0x5377a080/0x5377a09c` put two-bit values into word1 bits8:9,10:11,12:13,14:15. Caller `0x53773dcc..0x53773e08` supplies `pixelInfo[0xf] XOR 1` to all four latter setters. For format1 converter path this byte is 0, so values are 1. The physical significance of numeric enum1 has not been proved.

## CPU evidence and limits

`probe.py` executes actual instructions from `0x537672ac` through function return using Unicorn with a synthetic 16x8 low descriptor, format1, allocation16x8, address mode2, and function arg2=0. It intercepts every BL and records config buffers at calls `0x5376767c`, `0x53767740`, `0x53767848`. Result in `probe.json`. This establishes the construction of config bytes in this specific invocation; all called routines and hardware computation are outside that probe. It is not a pixel-accuracy test.

Input pixel information captured at `0x53767740` has YG address `0x10010000`, CbB address `0x10020000`, CrR address0, allocation stride16. The numeric flags and chunk selectors are zero at `+a..+f` and `+0x34..+0x37`. That is consistent with hardware's native YCbCr format, but native format semantic mapping is missing.

The first source pixel information record in probe.json was captured via r6 because that call uses another unit's config layout. The output record uses pointer at config+0x50 as required by its actual driver.

## Initial investigation status (superseded below)

No software byte unpacking consumer was found in the examined converter paths. They program IIP pixel-format and CSC hardware rather than perform byte-level RGB arithmetic on CPU. Neither NV16 convention nor matrix coefficient signs uniquely identifies UV/VU order. The driver has distinct pixel format enums, chunk order flags, sign enums and table setters, and those alone are insufficient without the hardware enum semantics or a software consumer matched to the capture format. Therefore capture chroma byte order, center encoding and clipping range remain unproved. Do not use the matrix offsets as proof that buffer neutral=128.

`refs.py` is an exploratory reference scanner: its MOVW/MOVT heuristic does not model register clobbers and must not be treated as a reference proof. In particular its apparent matches to signed-data dump strings were disproved by inspecting instructions (assertion source line values reused r3 before MOVT).

## Breakthrough: actual software pixel converter

`0x536c9450` executes a CPU conversion with no hardware or intercepted calls. `pixel-probe.py` runs the actual ARM/VFP instructions and records nine asymmetric/neutral/boundary cases in `pixel-probe.json`.

Input u32 byte0 is Y; byte1 increases the blue output and decreases green (Cb); byte2 increases red and decreases green (Cr). Both chroma bytes are loaded unsigned and converted to f32 before subtracting exactly128.0. The exact firmware float literals at `0x536c9550..0x536c9564` are128.0,1.4019999504,.3440000117,.7139999866,1.7719999552,255.0. Actual emulation confirms neutral Y0/128/255 produces RGB0/128/255. (128,160,128)->RGBA(128,116,184,255); (128,128,160)->(172,105,128,255). It clips each output RGB channel to0..255 and truncates the positive f32 intermediate to u32. This is genuine byte encoding proof **for this converter input**, not the capture buffer.

`0x536c9568` is a wrapper mapping source word's byte0 Y, byte2 first chroma, byte3 second chroma to the CPU converter's Y,Cb,Cr word. Therefore its input first chroma byte is Cb and second Cr.

`0x536d858c` is a semiplanar consumer: `0x536d8624 b270d8e0` reads two successive Y bytes via ldrh; `0x536d862c b240d9e0` reads combined chroma pair via ldrh. `0x536d8634/8638` puts low Y and the chroma halfword into stack bytes0,2,3 and calls the above wrapper. `0x536d8648` selects high Y; the next output pixel uses the same pair. The next row similarly shares the pair by rewinding chroma. Dispatcher at `0x536d88e0..8950` calls this path only for **UI bitmap type2**, apparently semiplanar420 as evidenced by two-row sharing. This is UV unsigned128-centered proof for UI bitmap type2. Do not conflate its enum2 with JPEG low descriptor enum1.

`0x536d8788` separately consumes packed422 with bytes Cb,Y0,Cr,Y1 (instructions `0x536d8800..885c`) and calls the same software conversion. Its dispatcher selector is UI bitmap type5. This confirms software conversion support of another 422 format but does not prove capture semiplanar422 ordering.

Source accessors: `0x536c7528` returns bitmap+8 firstbuffer; `0x536c7530` returns bitmap+0x10 if bitmap+c split flag!=0, else computes bitmap+8+width*height. The latter default combined-buffer calculation is performed by `0x536c74b0` only for bitmap enum1..4; its source is an independent UI bitmap object.

## Additional search notes

Opcode search for unsigned-byte subtract128 found AE class `18AeCheckComposition`, RTTI `0x53c576f8`, routines `0x5348b6dc..b710` and `0x5348b880..b8ac`. They compute average |byte-128| from independent planar obj+a8 and obj+ac buffers; their provenance into capture descriptors is unproved. Thus they cannot bridge the above UI representation to capture.

Read local gr3-film-mods `FINDINGS.md` section22l and `film_cave.py`; they contain CSP RGB->YCbCr coefficients and film matrix tuning, but no byte-level capture chroma order proof. Local darkslide-gr and gr-custom-tool search also did not reveal a matched byte-layout proof.

## Resolved: CPU fill for 422 and official descriptor adapter

The earlier unresolved conclusion is superseded by these linked, executed functions:

1. **CPU semantic anchor** `0x536c9450`: byte1=Cb, byte2=Cr, unsigned loads, neutral128, asymmetric blue/red responses. `pixel-probe.py` confirms actual VFP execution.
2. **Common color-word repacker** `0x536c9428`: copies input Y byte0 to output byte0, Cb byte1 to output byte2, Cr byte2 to output byte3. Output byte1 is stack padding and is not consumed for Y; output halfword bits16..31 is Cb low / Cr high. Exact instructions `0x536c9430` (`0c00cde5`) writes Y byte; `0x536c9438` (`5004efe7`) extracts input bits8..23; `0x536c9440` (`1038dfe7`) inserts that into output bits16..31.
3. **CPU fill dispatcher** `0x536d6d94`: calls repacker and pixel converter with same input color at `0x536d6dc0` / `0x536d6dcc`, examines bitmap type at `0x536d6dd0`; bitmap type1 goes `0x536d6e20` -> `0x536d6be8`, type2 goes `0x536d6ea0` -> `0x536d6b60`.
4. **422 fill path** `0x536d6be8`: calls first-plane byte fill `0x536d6808`, then passes chroma halfword unchanged to `0x536d69f0`, adjusting x/stride/width by2 for one chroma pair per two horizontal pixels. `0x536d6c28` (`b6a1dbe1`) reads high halfword from repacked color; `0x536d6c38` (`0a20a0e1`) passes it as r2. `0x536d6b14` (`b220c3e0`) writes that halfword in the scalar remainder; wide blocks use the same value repeated through NEON stores. On little-endian ARM bytes are Cb thenCr. The routine fills every row for422; the420 variant halves the vertical coordinate/count as well.
5. **Official low-descriptor adapter** `0x536c761c`: bitmap type1 maps to low descriptor format1; type2 maps to low descriptor format2 using table at `0x53dbae40` bytes `01 02 01 02`. Address-mode table at `0x53dbae44` is `02 02 01 01`. Types1/2 are thus the combined-buffer representations; types3/4 are separate planar representations. Default non-split type1/2 uses bitmap+8 as descriptor+4, computes second pointer by allocation width*height and stores descriptor+8, computes third pointer0, stores mode2 at descriptor+0x1c. No chroma bytes are converted or exchanged by the adapter.
6. `0x536d70d4` and `0x536d70e0` actually invoke this adapter to prepare source/destination low descriptors for original macro-processing calls, including `0x536d7164` -> `0x536abd28`. Thus this is the same low image-processing descriptor contract, not an unrelated UI byte format with coincidentally similar dimensions.

`fill-bridge-probe.py` executes **all actual ARM/VFP/NEON instructions and called CPU functions** of the format-dispatched fill and low-descriptor adapter; no BL hooks or hardware stubs are used. It tests type1 andtype2 for five asymmetric, neutral, and extreme Cb/Cr pairs, total10cases. For4x2,type1, input(Y,Cb,Cr)=(128,160,128), resulting buffer is Y eight128bytes followed by `[160,128]` repeatedfour times. For(128,128,160), chroma is `[128,160]` repeatedfour times. (128,0,255) preserves `[0,255]`; (128,255,0) preserves `[255,0]`. Each generated type1 descriptor is:

`01000000 00200010 08200010 00000000 04000200 04000200 00000000 02000000`

That decodes format1; Y0x10002000; combined0x10002008; third0; visible4x2; allocation4x2; zero offsets; address mode2. This agrees with the capture constructor contract from `0x534a2cf0/0x534a2ac4` and the JPEG consumer descriptor-copy path `0x536a3d84`.

### Final proved contract and remaining scope limit

For the original low image descriptor **format1 and address mode2**, combined chroma bytes are `Cb0,Cr0,Cb1,Cr1,...`, with each pair corresponding to two horizontal Y samples on the same row. Components are stored as unsigned8-bit bytes; neutral is128. The firmware's software conversion interprets chroma as byte-128, with full-range Y arithmetic (Y0/255 map to neutral RGB0/255) and saturates resulting RGB to0..255. Allocation stride determines row starts. The CPU fill and official adapter establish this contract from firmware bytes, without assuming NV16 conventions.

This proves the in-memory representation expected by the shared original descriptor consumers. It does not measure actual camera ISP output distributions, prove that every JPEG-process invocation comes from shutter capture, or prove hardware/cache ownership timing. Those remain separate questions.
