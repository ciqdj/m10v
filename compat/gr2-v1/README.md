# GR II v1 compatibility source

GR II uses a five-slot, 104-byte v4 state and a bounded BE32 renderer. The latest
GR III uses a ten-slot, 184-byte v5 state, different native grain handling and a
new SD renderer contract. Reusing those headers or the new web normalizer would
silently alter GR II persistence and native memory ownership.

This directory pins the required original source/data dependency closure from
PROVENANCE.json's revision. It contains no official or third-party firmware.
The extracted catalogue/state module and SD encoder serve GR II only. Source
notices and reference model inputs are retained; original project-wide notices
remain applicable. GR II C sources explicitly include these headers; its Python
builder validates reference tables here before compilation.

Shared visual CSS, brand navigation and picker still follow the current site.
The GR II control markup and normalizer under web/gr2 preserve its model ABI.
Do not upgrade this snapshot implicitly when changing GR III. A deliberate GR II
upgrade requires its configuration, SD contract, BE32 ABI and memory regressions.
