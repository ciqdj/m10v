# Monochrome community reference LUTs

Original files retrieved from YahiaAngelo/Film-Luts, revision
`af957b631a304e6be94778b96cb3395de3438e9f`, `luts/bw/`, on 2026-10-24:

- `kodak_tri-x_400.cube`
- `ilford_delta_100.cube`
- `rollei_ir_400.cube`

Upstream calls this the G'MIC Film LUTs Collection. Its MIT notice is retained
unchanged in LICENSE. Exact file SHA256 values are pinned in
`native/gr3/d76-reference.json`. No manufacturer-supplied LUT is claimed.

Encoding, emulsion generation, developer, scan and print chain are undocumented
upstream. M10V explicitly assumes display sRGB. These files are already neutral
monochrome; no different named stock is substituted. Rollei's LUT has bright
green and suppressed blue, used as the explicitly approved filtered-IR style.
Visible RGB cannot recover near-infrared scene reflectance.

No same-stock licensed LUT was found for PAN 400, SFX 200, Fomapan 400 or
CatLABS X Film 80 MKII. Their authored display approximations and official
identity/development references are recorded separately in the generator.
Manufacturer development times do not imply that the RGB curves were measured
in D-76. LUTs cannot reproduce spatial grain, acutance or film resolution.
