# GR II native film detail controller and entry

This implements the approved native per-film controls on the identity-locked
GR II v0.03 executable. It does not establish device boot/display/capture or
complete GR II/GR2013 parity. Research component and packaging gates remain
closed. No GR III widget addresses or little-endian structures are reused.

## Original entry and scope

The original effect chooser template is `A0411A18`: handler `A03AD0C7`, generic
root type `1A`, definition `66`, input type byte `3` at root+38. Definition102
is a64-byte row at `A04330D8+102*64`; its property is `2B`, title105 is Effect,
and the original selected-row getter/setter are `A03C0A50/A03C0AD0`.

With the original root, six initialized graphics contexts and original fonts,
the list selects property2B value8. Original event delivery `A0398E6C` with
SPEC_TRASH `60002010` emits public detail route `6000400B`. It is not the
ordinary RIGHT/OK route: OK emits `6000401A` to leave the chooser. The original
TRASH/detail action is reused, rather than inventing another physical key.

The existing installed route veneer at `A03948C4` invokes the model-local
adapter before public route conversion. It consumes the detail route only
when the film owner is enabled, the handler/type/definition/input byte all
match, and current property2B is one of the five original carrier tones:
`9,10,11,18,8` map to slots0..4. Other effects/roots retain stock routing.
An allocation/backend failure consumes this owned route and retains the root
for retry; it must not enter an incompatible original detail editor.

## Controls and storage

`native/gr2/m10v_detail.c` owns a116-byte BE32 controller: the existing104-byte
v4 journal state plus slot/readiness/error. The callback ABI is12 bytes. It
uses the shared library's mutations and reset behavior, not a second state
format. Visible IDs match the GR III controller:

| IDs | Availability | Values |
| --- | --- | --- |
|0..2 halo gain/spread/threshold|800T33 and Phoenix67|0..8|
|3 grain|all selectable builtin/custom films|0..3|
|4 legacy soft|hidden; existing journal value retained|no UI writes|
|5 grain size|all|0..2|
|6 leak gain|all|0..8|
|7 leak position|all|0..5|
|8 leak spread|all|0..8|
|9 leak variation|all|0..1|
|10 EI|Phoenix67 / HARMAN RED68|EI200/120 / EI125/64/250|
|11 reset|all|OK resets current slot only|

The owned page uses the original36-byte overlay prefix and existing UI heap,
font/rectangle adapters and lifetime operations. Five rows are visible at a
time. UP/DOWN and dial move focus; LEFT/RIGHT save immediately, OK resets on
the reset row, DISP returns. Bounds do not cause journal writes. Raw keys are
consumed before stock translation, so one physical adjustment is applied once.

Each write reloads a valid journal first. A replacement film/custom data bank
invalidates the session before any write. Other fields/slots are preserved.
After a write, including failed close/activation, it reloads the backend's
actual journal. A failed read disables editing instead of presenting an
unverified value. Reset preserves the selected film/custom bank and does not
change the independent global HDF journal or104-byte film state ABI.

## Evidence and limits

Seven focused tests pass in19.837s (`/tmp/gr2-detail-values-green.log`). They
cover every selectable film's exact field/limit matrix, every allowed value
for representative normal/halo/EI/custom films against independent journal
bytes/CRC, hidden/out-of-range rejection, custom-bank reset, failed writes,
failed-close-but-committed state and replacement-film protection.

The integrated entry fixture executes original TRASH delivery, the installed
route veneer, real native allocation/attach, original DRAW/font bodies,
physical-key veneer and detach/destruction. Only the journal callbacks are
explicit fixture boundaries. It opens slot4 for tone8, changes351376 display
bytes, consumes raw keys without duplicate stock delivery, retains the root
and restores UI pool capacity. Focused original entry passes in5.234s.
The earlier14-test detail/settings regression passes in45.430s.

Ignored CPU-composited previews and proof are in
`data/research/gr2/implementation/native-runtime/detail-ui/` and
`detail-ui-proof.json`. These are original-font display-plane reconstructions,
not camera screenshots. The first/error/last views were checked at720x480;
error feedback and footer occupy separate rows. Runtime SHA at this checkpoint
is `9aa7c2e1195046f6bc85a59bfa85507c62a6f797796d8f04d8a8a675b5f4e03d`,
296056 code bytes /298692 memory bytes, BE32/no BE8/no undefined symbols.
The source research component is6428792 bytes; `can_package:false` and
`activation_ready:false`. Full213-test GR II/unity regression passes in614.209s
(`/tmp/gr2-detail-final-full.log`). The subsequently extended native FILE
integration passes separately in5.308s: actual journal/LUT reload and reset
retain custom-bank identity, both stamp settings and independent HDF2/seq21,
with all FILE metadata and pool storage released. This transaction executes
three full journal/LUT validations; its fixture needed30M instructions instead
of the generic10M budget. Actual UI/SD latency remains unmeasured. Real media changes, display timing and device behavior remain
unverified; remaining native tools and web workflows stay researching.
