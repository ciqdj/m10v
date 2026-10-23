# Style filter reference assets

These assets are reference looks, not manufacturer LUTs or measured camera profiles.

- `fuji_velvia_50.cube`, `polaroid_px-680.cube`: YahiaAngelo/Film-Luts, commit `af957b631a304e6be94778b96cb3395de3438e9f`, MIT. Copyright (c) 2024 Yahia; full notice retained in `film-luts-license`. Paths: `luts/colorslide/fuji_velvia_50.cube`, `luts/instant_consumer/polaroid_px-680.cube`. Repository identifies its LUT collection as G'MIC-derived. PX-680 is an explicitly labelled historical instant-film proxy, not modern Polaroid 600/i-Type calibration.
- `Street Monochrome Eerie.cube`: sfi0zy / Street Monochrome, commit `3f915315da4f43dd86af304273615b3a54939a94`, CC BY 4.0. Author: Ivan Bogachev (sfi0zy), copyright 2026. Original project: https://github.com/sfi0zy/street-monochrome . License: https://creativecommons.org/licenses/by/4.0/ . Full license and original README retained in `street-license` and `street-readme.md`. M10V modifications: RGB neutralisation with Rec.709 luminance weights, resampling from the original lattice to 15 cubed, quantisation to 8 bit, and a separate approximate native ISP fit. No author endorsement implied.

The Lomography CN400 interpretation, Cyberpunk, Cyanotype and German Cool tables are independently authored by M10V. No game assets, commercial LUTs, Velvia 100, Polachrome, peel-apart Polaroid 669, Redscale, or Lomo X-Pro LUTs are substituted for the named references.

Reproduction parameters and SHA-256 hashes are recorded in `native/gr3/style-filters-reference.json`. Encoded display sRGB input is assumed; these transforms do not recover scene radiance or film exposure. Community look fidelity and physical camera/film matching are different properties.
