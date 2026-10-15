# GR III RAW NR and native library integration

Verified source: `bin/fwdc239b-gr3-official.bin`, GR III 2.10.21.27,
SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`.
Reference: local `gr3-film-mods/raw_nr.py` and `FINDINGS.md` section 21.
Those sources describe PPU Bayer filtering before RAW storage. Their camera observations concern their own builds; this native-library combination has not been camera-tested.

## Independent local evidence

Decoded the official RTOS with the existing strict full-file identity/container reader.
Capstone 5.0.7 confirms these actual ARM instructions:

| Address | Official | Replacement for off |
| --- | --- | --- |
| 0x5343326c | 0x02266001 `eoreq r6,r6,#1` | 0xe3a06000 `mov r6,#0` |
| 0x53433284 | 0x02277001 `eoreq r7,r7,#1` | 0xe3a07000 `mov r7,#0` |
| 0x53642ac4 | 0x13834018 `orrne r4,r3,#0x18` | 0x13834010 `orrne r4,r3,#0x10` |

The surrounding first path reads debug flags 0x77 and 0x7c through 0x53654220;
0x53642b4c loads cfg+0x19 before NRUnit parameter setup, and the still PPU caller at
0x53642f44 calls 0x53642b24. The off patch forces both still enable decisions to zero
and removes the alternate path's NR bit 3. The condition on the alternate OR is retained.
Unicorn 2.1.4 executes the actual planned replacement words for both Z states and all
boolean initial values, including preservation of the alternate conditional behavior.

Mode-0 B pointers at initialized-data ROM offset `0x107b540+0x375ec` are:

| Variant | Table | SHA-256, all 144 x 20 bytes |
| --- | --- | --- |
| 0 | 0x53ef9720 | d0f6f8ad9e5781c46eece7ea11bd22c5d28abaf60487dff37e4c353879eed2d6 |
| 1 | 0x53ef6868 | 4c8250c16bb2efd882be719a508917f5fb7c84afd8edb69689cc29f0eb1c41a7 |

Both stock enable bytes are zero at indices 0..35, one at 36..143. The threshold
mode clears only byte 0 below `round(8*(log2(iso/3.125)-1))`; all 19 other bytes per entry
and entries at/above the threshold retain their original values. ISO 6400 maps to 80,
so indices 36..79 change in both variants, exactly 88 bytes. Accepted ISO thresholds:
400, 800, 1600, 3200, 5000, 6400, 8000, 10000, 12800. Nominal ISO labels map to quantized
firmware table indices. This is an export-time threshold, independent of the existing
High-ISO NR menu, which retains its JPEG behavior. Live-view NR modes are unchanged.

## Shared state and API

Both native `prepare` and `build` endpoints accept:

```json
{
  "extensions": {
    "aspect": true,
    "level": true,
    "negativeGrain": true,
    "rawNr": {"mode":"threshold","iso":6400}
  }
}
```

Other RAW values: `{"mode":"stock"}` and `{"mode":"off"}`. The old complete three-boolean
extensions object remains valid and normalizes to RAW stock. Unknown fields, invalid ISO,
and ISO supplied to off/stock are rejected. `withNativeLibrary` accepts feature `rawNr`.
The frontend must send the same extensions to prepare and build, plus the returned
`configuration_sha256` as `accepted_configuration_sha256`. Changing RAW mode or ISO
invalidates the accepted plan. GR IIIx accepts stock only; nonstock never uses GR III
addresses on GR IIIx. No camera menu, catalog ID or native persisted setting is added.

The source fingerprint now includes the RAW planner and its resource reader. Composition
applies RAW edits after camera/native/negative-grain edits with exact preimage overlap
checks. A second audit decompresses the final firmware and compares every decoded byte
against a newly constructed expected image, including unrelated code and tables. Its
compact receipt `composition.raw_nr` records config, source identity, mechanism, table
pins, patch count/digest, instruction sites or cleared index range (upper end exclusive),
and JPEG/live-view stock scope. Compact ranges avoid oversized HTTP receipt headers.
A valid-checksum image composed for one RAW mode is rejected when audited as another.

## Verification

- `node --test node/gr3-integrated-export.test.mjs node/gr3-raw-nr.test.mjs node/gr3-customization.test.mjs`
- `node --test node/gr3-native-routes.test.mjs node/gr3-raw-nr.test.mjs`
- `.venv/bin/python -m unittest discover -s tests -p test_gr3_raw_nr_arm.py -v`

Tests cover strict normalization, all supported threshold entries and retained parameter
bytes, mode-specific plan hashes, stale acceptance rejection, GR IIIx gating, actual
combined aspect/level/negative-grain/native export for stock/off/threshold, RAW-only HTTP
export, receipt hash checks, and independent full-image readback/tamper rejection.
