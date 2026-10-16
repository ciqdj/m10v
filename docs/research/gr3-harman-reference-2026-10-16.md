# HARMAN reference models, 2026-10-16

These are independent, assumed interpretations, not official LUTs, measured film
models, or calibrated GR3 reproductions. No third-party preset was copied.
Numeric coefficients are all `assumed`, including every cross-channel weight,
curve knee, curve power, scan balance and relative grain multiplier.

## Evidence

- [Phoenix II technical information, July 2025, five pages](https://www.harmanphoto.co.uk/amfile/file/download/file/1968/product/2208/): the revised emulsion has finer grain, improved latitude and possible halation in high-contrast scenes. The D55 wedge is not a complete RGB sensitometry or calibrated LUT.

- [RED technical information, June 2025, five pages](https://www.harmanphoto.co.uk/amfile/file/download/file/1965/product/2170/): page 3 states that the red record receives red and blue, green receives green and blue, and the blue record receives little information. It includes a characteristic curve and 2856 K wedge spectrogram. Neither plot supplies the full numerical sensitometry needed for a spectral model; neither was digitized in this implementation.
- [Official RED launch, 14 February 2025](https://www.harmantechnology.com/harman-red-125-a-brand-new-professionally-finished-redscale-film/): RED is the original Phoenix emulsion exposed through the base, ISO125, 135/36, standard C41. The clear base has no anti-halation layer.
- [Official Phoenix II product](https://www.harmanphoto.co.uk/harman-phoenix-ii-35mm) and [FAQ](https://www.harmanphoto.co.uk/faq/): Phoenix II is a different revised emulsion. The model only uses qualitative direction (restrained color, contrast, grain); it does not derive Phoenix II from a measured RED model or invert the original Phoenix.

The RED PDF illustrates EI250/125/64 bracketed exposures, with coarser grain,
stronger shadows and deeper reds underexposed; normal exposure gives orange
and softer shadows. Higher exposure gives finer grain and brighter tones. Its
standard C41 process is unchanged across these brackets; push processing is not
recommended. Scanner density and color correction affect the result.

## Model

Input is assumed display-encoded sRGB, D65. The camera JPEG's ISP and original
scene spectrum are not recovered. Decode to linear light before exposure and
channel mixing. The model is explicitly RGB, not a full spectral simulation.

Phoenix II: a restrained chromatic matrix with every row summing to one,
followed by an identical saturating tone response in all channels. This preserves
a neutral gray axis and does not introduce a fixed global blue cast. Colorful
inputs remain chromatic; it is not a sepia or grayscale transform.

RED: `record = linearRGB @ record_matrix.T * (125/EI)`. The red record uses R+B,
green uses G+B, and blue uses a weak B response. A channel-specific `log1p`
density response and fixed scan powers/gains produce a positive image. The scan
inversion is a simplified monotone density-to-positive relation, not measured dye
transmission/scanner optics. Different powers make exposure change color ratios;
EI is not implemented as final-output brightness. Red shadows become relatively
deeper; increasing exposure raises the relative green contribution.

All coefficients are in `PARAMETERS` in the generator and copied into the
manifest. They are auditable assumptions constrained by official descriptions,
not values read from official curves. All calibration flags are false. The default
RED table is EI125; EI64 and EI250 match the official bracket examples. This
supports internal selection without prescribing a new UI. Shared grain controls
may multiply their existing strength by `grain_relative[ei]`; this is only an
assumed relative direction. Spatial grain, diffusion and leaks are not baked into
these color LUTs. No specific halation color/radius/strength is claimed: reversed
exposure changes the optical path, so absence of anti-halation does not justify
copying an 800T red halo or declaring a blue halo.

## Asset contract and verification

Four 15 cubed uint8 RGB tables, blue axis fastest:

| index | stock id | model | exposure |
| --- | --- | --- | --- |
| 0 | 67 | Phoenix II 200 | EI200 |
| 1 | 68 | RED125 default | EI125 |
| 2 | 68 | RED125 | EI64 |
| 3 | 68 | RED125 | EI250 |

The C symbol is `m10v_harman_luts[4][3375][3]`. Web stock `values` is a flattened
10125-element uint8 list. The manifest hashes each table's raw bytes, generator
source, parameter JSON and source-reference JSON. The independent standard-library
verifier parses nested C dimensions and checks C/Web equality, range, identity,
hashes, calibration flags, and literal source parameter definitions using AST
without executing the generator. These hashes detect inconsistency; they are
not signatures or guarantees against coordinated malicious replacement.

Held-out validation: tetrahedral interpolation at 8192 deterministic random
encoded-RGB points in [0,1], seed68125, against the continuous assumed model.
This measures quantization/interpolation only, not film fidelity.

| table | RGB abs p95 | RGB abs max | delta E00 median | delta E00 p95 | delta E00 max |
| --- | --- | --- | --- | --- | --- |
| Phoenix II | .00750 | .08685 | .1114 | .3614 | 1.6214 |
| RED EI125 | .00160 | .03321 | .0800 | .1824 | 5.0585 |
| RED EI64 | .00179 | .05477 | .0786 | .2057 | 8.5991 |
| RED EI250 | .00152 | .01639 | .0823 | .1925 | 2.5239 |

The larger maxima occur near dark/color-boundary regions; averages do not imply
uniform error bounds. A denser LUT or domain shaper could reduce them but is not
part of this firmware table-size contract. Validation tests also exercise neutral
monotonicity, colored inputs, B-to-R/G contributions, exposure before density,
color-ratio changes with exposure, and rejection of corrupt/malformed payloads.

To regenerate: `.venv/bin/python scripts/build_gr3_harman_reference.py`.
To verify without numpy/colour: `python3 scripts/verify_gr3_harman_reference.py`.
To run scoped tests: `.venv/bin/python -m unittest tests.test_gr3_harman_reference`.

## Missing measurements

A calibrated model needs paired digital RAW/film color-chart and grayscale
captures across EI64/125/250, fixed C41 and fixed scanner correction, and point-light
captures for halation. Unknowns include full spectral sensitivities, dye spectra,
exposure-dependent grain statistics, scanner inversion and GR3 ISP response. Public
scans alone conflate scanner choices with film response. Do not market these assets
as measured or claim 100 percent film reproduction.
