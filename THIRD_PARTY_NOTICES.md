# Third-party notices

The GR III profile and container codec in `m10v_core/profile.py` and
`m10v_core/codec/` are derived from `gr-custom-tool` (DoYitNow), licensed
under GPL-2.0-only. Source file SHA-256 values at import:

`node/firmware.mjs` ports the read-only GR III profile and decoding checks
from those files; it is also covered by this project's GPL-2.0-only license.

- `profiles/gr3.py`: `b5d90aaeaff45531d7f59904ab5eded33a2b5fc2259030c225faf6970c0a0ca7`
- `codec/container.py`: `7f6f83ac21387dd08002a5a0c20fccac6f212e398079c9694304463b6c163a45`
- `codec/frames.py`: `cd89e80080d7e8f1e940b7c737d9d3966ec75fb04a9961b9a1daeb5d19f9b078`

See `LICENSE`. The user's official firmware is not included in this source tree.

## GRLife compatibility data and local runtime

`web/gr3/film-catalog.json` contains 32 fitted film entries and camera icon pixels
derived from the [public GRLife film catalog](https://grlife.app/firmware-store/film-catalog.js).
Its film fitting data are attributed upstream to `film/NOTICE.md`, including
CC BY-SA 4.0 material; retain the upstream attribution and share-alike
requirements when redistributing that data.
`web/gr3/community-data.json` contains reference recipe values from the public
GRLife community catalog. The user-supplied modified firmware is used for
byte-level regression evidence; it is not distributed in this repository.

The GRLife Python browser core and three JavaScript fitting modules are
downloaded by `scripts/sync-grlife-runtime.mjs` into the ignored `.runtime/`
directory. Each fetched file is pinned by SHA-256 and verified before use.
GRLife source code is not bundled or relicensed by m10v. Users should review
GRLife's applicable license and terms before redistributing a packaged runtime.

The current GRLife runtime manifest SHA-256 is
`1dff66f9e243329ed4ab95b9b7bb4bef74846848f62ae29172d8f3c74574688b`.
Its film-bay extension and film data stay in the ignored local runtime;
m10v's independently written audit reads their pinned hashes and checks the
generated firmware. GRLife separately issues device-bound `FILMS.GRF` files
through its service. m10v does not call that issuer. Its alternative generator
signs plaintext records with a public project key, and its firmware overlay
replaces only the film-bay module's verification public key. This key grants no
access to GRLife's issuer. The original runtime stays hash-pinned and unmodified.

## GR IV reference core

`vendor/gr4/` contains a deterministic source snapshot of the GPL-2.0-only
`gr-custom-tool` distribution by DoYitNow. It includes the Python/native core,
browser source and Lightroom bridge. Three large calibration DNG samples remain local and are excluded from the Git source distribution; their original names and hashes remain in the provenance manifest for restoration. The precise
source commit, every included file hash and size, and intentional exclusions are
recorded in `vendor/gr4/PROVENANCE.json`. The standalone upstream HTTP server and
runtime data are excluded; m10v supplies its own loopback server and product UI.

## Darkslide GR preset metadata

`vendor/darkslide/gr3_v210.json` is copied from LiorMoment/darkslide-gr,
commit `9913169558d725d44400e297ff0bebe2c252abc7`, GPL-2.0-only.
The corresponding license is preserved at `vendor/darkslide/LICENSE`.
The new JS resource reader/editor is implemented in m10v from the GR III
layout, with Darkslide's slot metadata, name storage rules and findings credited.

RAW noise-reduction layout references `idontknownihil/gr3-film-mods`, commit
`04d5d5dd6e85d80089c6200bd0f0de5fff2d658f`; upstream code/notes are MIT.
The new XMP conversion uses the already pinned GPL gr-custom-tool reference
renderer and its Adobe DNG table format decoder, then fits GR III parameters.
It does not reuse GR IV firmware color tables or include an official BIN.
