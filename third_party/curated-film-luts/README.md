# Community film colour references

Retrieved 2026-10-19 from [YahiaAngelo/Film-Luts](https://github.com/YahiaAngelo/Film-Luts), which identifies these assets as G'MIC film LUTs. The upstream MIT notice is retained in `LICENSE`; the original cube headers are unchanged. The exact downloaded contents are pinned by SHA-256 in `native/gr3/curated-reference.json`.

- `kodak_portra_160.cube`: `luts/negative_new/kodak_portra_160.cube`, modern Portra 160, not the older NC/VC stocks.
- `fuji_superia_100.cube`: `luts/negative_old/fuji_superia_100.cube`. Used as an explicitly approximate colour reference for business-use 100. It is **not** an Industrial 100 measurement or official transform.

These display LUTs are community interpretations, not manufacturer-supplied film data. Their input encoding is not documented upstream; M10V explicitly assumes display sRGB. Interpreting them on already-rendered camera RGB cannot recover the exposure or spectrum of the photographed scene.

No Lucky Super 200 LUT is included. New Lucky C200 has a separately authored, community-inspired display interpretation; Ross McConaghy's Firebird/Daisy LUT files were not downloaded or redistributed.
