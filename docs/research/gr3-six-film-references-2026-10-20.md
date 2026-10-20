# Six additional film interpretations (IDs 73–78)

These are display sRGB approximations for rendered camera pixels. No scene exposure,
sensor spectrum, actual development/scan calibration or manufacturer LUT is
available. A small implementation error against our target is **not** a measured
error against real film. Actual film accuracy remains unknown. All source tables
and generator dependencies are pinned in `native/gr3/newstocks-reference.json`.

| ID | Stock | Numerical source and interpretation |
|---|---|---|
|73|Fujifilm C200|Its own visible sensitivity and characteristic curves in Jan Lohse's MIT `fuji_c200.py`, checked against Fujifilm's C200 bulletin. Not Lucky C200, Superia or another film.|
|74|Kodak ProImage 100|Kodak E-4L July 1997 p3 characteristic and spectral-sensitivity curves, manually digitized in `newstocks-sources/proimage-100-digitized.json`. No substitute stock or guessed Portra LUT.|
|75|Kodak T-Max 100|Named G'MIC community `kodak_t-max_100.cube` from MIT YahiaAngelo/Film-Luts; not T-Max 400/3200. Input encoding is undocumented upstream, so display sRGB is an assumption. Output explicitly neutral monochrome.|
|76|Aerochrome III 1443|Its own experimental MIT spectral-film-lut data; visible-only false-colour mapping. **Approximation: RGB has no NIR reflectance.** Equal RGB values from different materials cannot predict differing infrared response.|
|77|Aerocolor IV 2460|Its own MIT `kodak_aerocolor.py` visible sensitivity and density curves. Manufacturer URL's filename says III; vendor model explicitly identifies IV 2460.|
|78|VISION3 50D 5203|Its own MIT `kodak_5203.py` curves; Kodak H-1-5203t July 2015 confirms 5203/7203, daylight 5500K, EI50, ECN-2 and remjet. Not 250D/5207.|

The shared adaptation uses each film's recorded log-exposure range normalized
into display code values, and a declared 22% characteristic-curve blend. Its 10%
visible cross-channel term integrates that film's own sensitivity under assumed
RGB Gaussian primaries (610/545/460nm, sigma35nm). These are design assumptions,
not inverse ISP, spectrum reconstruction, absolute exposure, negative scanning,
measured film colour accuracy or scanner calibration. Aerochrome's separate
false-colour topology is explicitly assumed. Parameters are public in the generator.
C200's upstream RMS grain data is marked copied from 5207, so it is **not used**.
Shared procedural grain remains a user control, never a claim of measured granularity.

## Official document checks

- [C200 technical bulletin](https://asset.fujifilm.com/www/my/files/2020-09/cdc2d78497ca4ff6084f02188d175f10/films_c200_datasheet_01.pdf): downloaded successfully; the manufacturer's specific C200 curves are represented by the pinned MIT transcription.
- [ProImage E-4L historical manufacturer PDF mirror](https://vklaboratori.com/wp-content/uploads/2018/07/kodak-pro-image-100.pdf): SHA256 `f2d1a1faa32bbbc96ab4f69ffa5ee7d99f8bc554392dcec42f715fb934d92700`. p3 specifies daylight, C-41, Status M; sensitivity at 1/50s and 0.2 above D-min. Includes dye density, but the current display adaptation does not model optical negative scanning. Estimated manual reading uncertainties: density ±0.04, logH ±0.06, logSensitivity ±0.10, wavelength ±5nm; these are visual estimates, not statistical confidence intervals.
- [T-Max F-4016 June 2018](https://www.kodakprofessional.com/sites/default/files/wysiwyg/pro/resources/f4016_TMax_100.pdf): p1 identifies ISO100/21°, p8 specifies diffuse rms granularity8, resolving power63lp/mm at1.6:1 and200lp/mm at1000:1, D-76 at20°C. It also publishes multiple development-time characteristic curves and p9 contrast indices; no single development time can be claimed to match the community LUT. Fine grain is a qualitative default only.
- [5203 official H-1-5203t](https://www.kodak.com/content/products-brochures/Film/VISION3-50D-Color-Negative-Film-7203-TECHNICAL-DATA.pdf): verified 5 pages; extended highlight latitude cannot be recovered from clipped rendered pixels.
- [Aerochrome official AS-57 April2006](https://www.kodak.com/content/pdfs/amc/Specifications-and-Characteristics-of-KODAK-Aerial-Films-datasheet-EN.pdf): identifies1443 false-colour reversal/negative, AR-5/C-41, aerial speed40 with Wratten12 and rms23. Aerial speed is explicitly not conventional pictorial ISO; the catalogue iso40 field follows the upstream aerial model, not a physical exposure recommendation.
- [2460 official AS-2652, October 2009](https://www.kodak.com/content/products-brochures/Advanced-Materials/KODAK-AEROCOLOR-III-Negative-Film-2460-datasheet.pdf): the initial `/content/pdfs/` URL failed, but this official six-page alternate was read successfully. Despite III in its URL, the document identifies IV 2460. It specifies daylight balance, no integral colour masking, AN-6 / C-41 compatibility and EAFS / ISO A 125 at maximum contrast; this aerial speed is not ordinary pictorial ISO. Page 6 publishes separate low / medium / maximum contrast characteristic curves (C-41 development 3:15 / 4:15 / 5:15), and page 5 spectral sensitivity. The current display model does not promise to match every development condition.

## Quantitative checks

8192 uniform display-RGB holdout samples. ΔE00 compares implementation to the
declared display target, not a film photograph. Full results, maxima and RGB code
errors are recorded alongside source hashes.

| Stock | Native surrogate ΔE00 p95 |
|---|---:|
|C200|0.506|
|ProImage100|0.595|
|T-Max100|0.912|
|Aerochrome1443|1.284|
|Aerocolor2460|0.325|
|5203|0.655|

T-Max's maximum native-surrogate error is7.33 on this holdout (p95 .912); extreme
colours are less accurately approximated. This must not be hidden by the p95.
Browser/CPU LUT interpolation errors and native surrogate fitting errors are
separate. Native C tetrahedra match an independent integer reference at all 256
greys plus1024 random triples per film; browser endpoint/alpha/monochrome and SD
export/audit are covered by tests. Actual camera rendering is still unverified.

## Compatibility and storage

Existing film IDs1..72 stay fixed. New IDs73..78 use an independent60750-byte
immutable LUT bank so each ARM linked object remains under64KiB. Icon IDs671..748
include all78 artworks; five dynamic film cards move to749..753.

SD built-in catalogue has46 choices (33..78), with the original hidden catalogue
1..32 retained. Custom LUT IDs now begin79. Old SD packs and cached custom records
have a different renderer contract and require regeneration/reinstallation. An old
custom73..78 carrying its bank marker is rejected by the new state validator;
it cannot silently render as a new built-in. No guessed migration is performed.

The largest measured offline configuration (base `0x540ba000`, debug, live
colour, HDF, SD, native colour/grain, all NEON/capture/lifecycle extensions)
produces 856312 runtime bytes, RTOS growth875320 bytes and end address
`0x5418b0f8`. The bounded896KiB budget leaves42184 bytes. Fresh candidate decode
and readback audit verifies100 hooks, only RTOS changed,78 icons and46 SD recipes.
This establishes offline packaging bounds; it is not a real camera stability test.
