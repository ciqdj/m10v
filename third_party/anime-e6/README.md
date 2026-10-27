# Anime / E6 provenance

`fuji_provia_100f.cube` is retained verbatim from YahiaAngelo/Film-Luts at af957b631a304e6be94778b96cb3395de3438e9f. Its repository declares MIT; included license preserves that notice. Its G’MIC header and normalized RGB domain do not establish camera or film calibration. See sources.json for exact URL and hashes.

The three anime looks, E100 and 5294 targets are independently authored numerical grading approximations. They contain no artwork or third-party transform coefficients. All numeric assumptions are in scripts/build_gr3_anime_e6_reference.py and the generated manifest. E100 and 5294 each have separate official context and separate assumed models; neither is E100G/GX/VS, 5285 or a motion-picture print LUT. Official PDFs were consulted and hashed, not redistributed; their curves were not digitized.

GRKit f62cd016 E100 JSON and its bake_spektrafilm.py were inspected only as research: the source input is Panasonic V-Log / V-Gamut, and its fitted parameters are not an sRGB LUT. No GRKit or spektrafilm code/data is incorporated.

These RGB targets exist for offline fitting and web reference. Camera defaults use generated quantized ISP parameters. There is no claimed physical-film, artistic, spectral or camera validation.
