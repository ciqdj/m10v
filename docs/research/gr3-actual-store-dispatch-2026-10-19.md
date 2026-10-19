# Actual StoreImageProcess command and generic dispatcher trace

The v5 device log contained no events from either old file observer. Static investigation now explains a concrete branch difference, rather than adding another named file hook.

Locked official GR III 2.10 RTOS SHA256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

## Actual original topology

`StoreImageProcess` RTTI identifies vptr `0x53d0f7b8`, whose virtual +0xc is common receiver `0x53505c8c` and virtual +0x20 is handler `0x5350c764`. That handler examines **message+4**, not a guessed file controller:

- `0x01000001`: tailcalls `0x5350bfb0`, the main save routine constructing RAW/JPEG write descriptors and calling lower native services.
- `0x01000002`: tailcalls `0x5350b2fc`, containing the previous observer site `0x5350b380` and generic service call `0x53697658`.

The main command therefore bypasses the old BE service hook entirely. This is original CPU control-flow evidence; the next device run must establish the actual command and completion statuses.

Original scheduler producer `0x5351ea9c` constructs a message at `recipe+0x3b0+24*kind`. It calls original `0x5350e278`, which creates metadata at `recipe+0x5f0+32*kind`, stores metadata+20=recipe, and places that metadata pointer in message+12. Kinds range 0..23. The observer validates BOTH exact offsets plus recipe vptr and owned trace magic. It never follows image backing or guesses a recipe from an unrelated context.

Common receiver dispatch site `0x53505d78` executes `BLX r9` with module r8, message r7 and actual handler r9. Probes restore original SP before the displaced call; original outgoing stack arguments are unchanged. The return observer at `0x53505d7c` records original r0 before replaying `ldr r7,[fp,#-0x34]`.

## Optional Store-only caller drain

Third optional site `0x53505dbc` is the receiver's common rejoin after its reference-counter mutex is released:

- nonzero reference count: `0x53505db8` unlocks, then falls through;
- zero reference count: `0x53505dec` unlocks, destructor paths finish, then `0x53505e24` branches to rejoin;
- null reference count: direct branch to rejoin.

Recipe owner callback `0x53505e28` has **not** executed at this point, so it has not retired the recipe. Metadata remains in r5; actual handler remains in callee-saved r9. The optional sink only runs for exact original handler `0x5350c764`. It drains the existing bounded recipe trace via existing `recipe_take` and `m10v_debug_batch`, after handler return and before the owner callback. Other module handlers only append data and do not flush.

The local mutex/owner sequence is established from original instructions. Absence of **every transitive global filesystem lock** is not established; this remains an explicit integration/hardware validation limit. A drain attempt does not prove persistent SD logging, photo durability, or directory visibility. Ring contention/full capacity and retirement can still lose observations. No status or trace record controls a buffer release or image effect.

## New isolated module

- `native/gr3/m10v_module_dispatch_trace.c`
- `scripts/build_gr3_module_dispatch_trace.py`
- `tests/test_gr3_module_dispatch_trace.py`

Builder API: `build(out,base,mark,rtos=None,take=None,batch=None)`. Without take/batch it emits only the two data-only dispatcher probes. Supplying both enables the third Store-only sink. Symbols come from existing owner trace exports and existing debug runtime; no invented global RAM or heap is introduced. Existing extended recipe tails are untouched.

Events:

| Event | Arguments |
|---|---|
| 204 | recipe, kind, actual handler, module |
| 205 | recipe, kind, actual handler, original return |
| 206 | recipe, kind, Store command opcode, module |
| 207 | recipe, kind, original clock microseconds, seconds with high-bit clock-error marker |

Eight tests pass in ARM CPU emulation. They execute the **actual original scheduler producer for every 24 kinds**, execute original StoreImageProcess command selection for both opcodes, exercise installed dispatch/return patches with original stack arguments, inject adversarial D0..D31/FPSCR clobbers into the trace service, and check the Store-only sink rejoin preserves GPR/SP/LR/NZCV. These are CPU ABI/topology tests, not a physical SD, scheduler or file durability test.
