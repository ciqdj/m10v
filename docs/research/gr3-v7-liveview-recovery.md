# V7 independent LiveView / QuickView recovery research

Scope: read-only analysis of original RTOS `builds/gr3-extension-validation/official-rtos.bin`, SHA256 `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`, VA `0x53000000`. No production builder/hook changes. These results neither identify the real camera's stuck state nor establish a hardware repair.

## Important distinction

JPEG completion, a module handler returning 1, and LiveView being visible are three different contracts. Existing lifetime research establishes module owner notification is after the concrete handler (`0x53505d78` → `0x53505e28` → owner). This investigation finds a separate UI state machine whose own entry functions return 1 even when they have only queued a desired state. CPU render duration is consequently insufficient to explain persistent black display after all image processing has returned.

## LiveViewController state machine

Original function-name strings identify `0x5323830c` as `StartLiveView`, `0x5323a7bc` as `OnMsgIdEvtShootingLiveViewStateComplete`, and `0x53239398` as `OnCompleteLiveViewStateChange`.

Controller fields derived from ARM reads/writes:

| Field | Meaning supported by code |
| --- | --- |
| `+8` byte | Current state, written by complete-event decoder |
| `+9` byte | Desired/pending state, consumed by `0x53239398` |
| `+a` byte | Nonzero operation in flight; blocks fresh sends and pending consumption |
| `+c..+18` | Completion function object; `+14` manager and `+18` invoker |

`0x532380c4` sends message `0x4241080d` through `0x532286dc`; its second argument becomes message argument and controller `+a`. The separate sender `0x532381c0` uses `0x4241080e`, so it must not be casually substituted for the ordinary LiveView channel.

The stock shell at `0x53017ce8` labels request argument 4 as resume, sends `0x4241080d`, then labels completion at `0x53017d14`. Shell start/stop/pause use corresponding arguments 1/2/3. This is static code evidence, not proof that invoking a shell/UI API from a processing worker is safe.

`StartLiveView` accepts state 4 (paused): `0x532384c0` stores pending 2, then `0x532384cc` passes argument 4 to normal sender `0x532380c4` (resume). If `+a` is already nonzero, its early branch `0x53238340` merely returns 1 and stores pending 2. Three other entries behave analogously:

| Entry | Pending value on busy branch | Return |
| --- | --- | --- |
| `0x5323830c` | 2 | 1 |
| `0x53238b40` | 1 | 1 |
| `0x5323900c` | 4 | 1 |
| `0x532391d0` | 5 | 1 |

Thus a successful request result does **not** prove a state change or that any message was sent. If in-flight never clears, a new request only overwrites pending.

Complete handler `0x5323a7bc` reads event byte `message+4`: 1/4 → state2, 2 → state1, 3 → state4. At `0x5323a804` it clears in-flight, calls `0x5323a5cc`, posts local event `0x13e` via `0x532288b0`, and tail-calls pending consumer `0x53239398`. Consumer returns immediately when in-flight remains nonzero, or when `0x53235090` returns zero. Otherwise it clears pending, compares pending against current, dispatches pending1/2/3/4/5 through `0x53238b40` / `0x5323830c` / `0x53238724` / `0x5323900c` / `0x532391d0`, or invokes stored completion if no change is needed. Do not force-clear `+a`: it represents a real asynchronous request and protects ordering.

## QuickViewController owns a separate timeout and exit chain

RTTI `19QuickViewController` has primary vtable `0x53b41380`. Its local UI event dispatch is `0x531cbfc4`, current state is byte `+0x16c`; timer tokens are words `+0x178` and `+0x17c`. The timer listener secondary interface is `this+0x158`, thunk `0x531ca8f4` subtracts `0x158` and enters callback `0x531ca86c`.

The user-configured timeout is read by `0x532462d0` from settings `settings->data+0x900`; it corresponds to the `CustomQuickViewTimeMsec` setting. `0x531caa7c` cancels an old `+178` timer, then handles timeout 0 by immediately requesting controller transition, -1 by retaining indefinitely, and other values by calling `0x5322b468(timeout,this+158)` and storing returned token at `+178`.

Original callback behavior is unexpectedly selective and matters to black-screen diagnosis:

* If input token matches `+178`, clear token. Only states 0 or 1 set `+180=1` and request transition `0x08000000` / `0x10000000` via `0x5316c9d8`. States 2..5 return after clearing token and **do not exit**.
* If input token matches `+17c`, clear token. Only state2 posts event `0xf2`; other states do not post. `0x531cac04` arms this timer for 2000ms; dispatcher only calls it for event `0xf3` when state2.
* If token matches neither field, callback returns with no transition or token change.

Entry `0x531cbde4` first sets state6, obtains requested state and updates it via `0x531cb7bc`; only state0/1 arms the user timeout. UI event `0x169` in state2 enters `0x531cbe78`, which can set state0, post `0xf1`, then arm the configured timeout. The event source/name needs more evidence before equating it to image save or hardware completion.

Many user-input exits exist. `0x531ca804` sets `+180=1` and asks the controller manager for the same exit transition; `0x531cc124` does likewise. Dispatcher events `0xb6` / `0xb7` reach the latter directly; `0xb8` only does so if `+182==0`; `0x86` / `0x87` only set `+180=1`. These **numeric events have not been proven to be half-press**. Do not label or inject them as half-press on this evidence alone. `0x531cab24` exit cleanup cancels both timers and consumes `+180`.

This creates a concrete alternative to 'slow render': if QuickView is waiting in state2 and never receives its readiness/transition event, the ordinary configured review timer does not force an exit. A physical input can still drive an unrelated controller-manager exit. This remains a hypothesis for the user's black screen until instrumented on device.

## Minimal next diagnostic hooks

All records should include monotonically sampled time, controller pointer, and compact scalar state; do not read image buffers or flush SD per hook.

1. Normal LiveView sender call site `0x53238114`: capture request argument, caller/controller identity, `+8/+9/+a` before and after send.
2. LiveView complete entry `0x5323a7bc`: capture event word and `message+4`, controller `+8/+9/+a`; post point `0x5323a824` captures resulting states. This distinguishes missing response, wrong payload and pending consumption failure.
3. QuickView state write `0x531cb828`: old/new `+16c`; timers `+178/+17c`; flags `+180/+181/+182`. This hook should be guarded by verified controller RTTI/vptr.
4. QuickView timer callback `0x531ca86c`: token/state/two registered tokens. Timer setup boundaries `0x531caac4` and `0x531cac30` capture timeout and token result.
5. UI dispatcher `0x531cbfc4`, tightly filtered to events `0x169,0xf3,0xf2,0xf1,0xb6,0xb7,0xb8` plus the actual hardware key event once identified. This links natural black recovery and manual half-press to the same trace without injecting input.
6. Preserve existing actual Store handler return and add owner-return completion, since current pre-owner handler observation cannot prove owner progress.

A production fix is **not yet justified**. Once a trace proves (a) QuickView's specific missing transition, repair its producer/notification ordering; or (b) native LV complete received but pending never consumed, repair that callback propagation. A bounded watchdog may only request an existing native controller transition on its owning UI thread after verifying current shooting mode/state, idle asynchronous operation, no capture ownership dependency, and a generation-matching transaction. Never call start/resume from a JPEG worker, manufacture a complete message, clear in-flight, release unknown buffers, or synthesize half-press.

## Executable evidence

Run `.venv/bin/python scripts/analyze_gr3_v7_liveview.py`. Unicorn requires the normal approved unsandboxed invocation on this machine. Result: **24 original ARM state probes PASS**. Probes execute the locked binary bytes: 4 complete-event mappings, 4 success-but-deferred request branches, busy pending consumer, 6 configured timeout state cases, 6 secondary timeout state cases, mismatched-token rejection, native backend event translation, and ShootingModel-to-UI169 dispatch. UI/OS send/notify/transition services are explicit stubs; this verifies ARM branching and state writes, not display, sensor, scheduling, or SD behavior. Production code and existing tests were untouched.


## Integration implementation and newly proven UI169 producer

New `native/gr3/m10v_view_recovery.[ch]` provides caller-owned snapshots, pure decision, caller-owned bounded trace and a narrowly gated original `StartLiveView` request. There is no filesystem, allocation, global mutable state or image-buffer operation in observation. `tests/test_gr3_view_recovery.py`: **9 tests PASS**, including the 24 stock ARM probes. C compiled with `-Wall -Wextra -Werror`.

Correction in terminology: the `+8/+9/+a` state machine resides in **ShootingModel**, whose exact vptr is `0x53b4e7b0`, singleton `0x55067958`, initialized guard `0x55064398` bit1. The stock `0x5320b19c` accessor proves this address. `LiveViewController` delegates to it. The earlier state-machine branch findings remain correct. `0x5320bcdc` is QuickView **model**, singleton `0x55063ddc`; it is not the QuickViewController.

The actual QuickViewController is cached by ControllerFactory. Original `0x5316f350` returns singleton `0x55063914`, initialized guard `0x55063910` bit1. Factory lookup `0x531709f0..0x53170a0c` reads slot `factory+0xd8`, allocates `0x184` bytes if needed, calls `0x531cacc4` constructor and stores it back. Observation reads existing slot only and follows it only for RAM/alignment/exact `0x53b41380` vptr. It does not call the factory lookup, model accessor, UIroot accessor or any lazy initializer. The caller must serialize on the owning UI thread for a coherent snapshot; a snapshot taken from Store is observational and may be concurrent.

UI169 now has an **actual ARM-proven producer chain**:

1. Internal original backend callback `0x5382fc8c`, argument `0x0408100a`, selects `0x5382ff98`; sender `0x5382fb9c` receives event `0x22408e31`, zero payload.
2. ShootingModel original dispatcher `0x5323a878` compares `0x22408e31` at `0x5323aa20`; branch `0x5323aaf8` tail-calls `0x53236734`.
3. That producer calls `0x532af2c8` through another model, then posts UI event `0x169` at `0x53236768`, sets ShootingModel `+0x8a3=1`, and clears `+0x31/+0x2f`.
4. QuickViewController dispatcher `0x531cbfc4` consumes UI169 only in state2 and calls `0x531cbe78`. That function checks `0x532372c0` (ShootingModel `+0x2f`, falling back to `+0x30`); if busy, it returns without advancing state. Otherwise it sets QuickView state0, posts f1 and arms configured review timeout.

No event has been synthesized. Backend native event `0x22408e31` is a stronger completion boundary than Store handler return; trace its real delivery/consumer. A missed UI169, premature delivery while `+0x30` remains busy, or missing UI dispatch are now separable. **Do not call `0x53236734` as a repair**: it mutates shooting flags and would forge native completion. Observe and repair the real event propagation/order once a device trace proves which branch is stranded.

Integration ABI:

* `m10v_view_snapshot_camera(&caller_snapshot)` is the low-level data-only observation entry, including ShootingModel fields and existing cached QuickView controller state/timers.
* `m10v_view_trace_append(&caller_trace,boundary,time,payload,&snapshot)` copies scalars into a caller-owned 16-record buffer. It is single-writer and intentionally does not choose a hidden owner or store a global pointer. Drain only in an existing safe consumer.
* `m10v_view_recovery_decide(snapshot,facts)` returns CAN_REQUEST only for native paused state4, idle pending/inflight, clear shooting flags and **all** five caller-proven facts: owning UI thread, native owner completion, native save completion, QuickView inactive and normal still mode. Actual state2 returns ALREADY_RUNNING, which says nothing about visible display.
* `m10v_view_recovery_request(...)` re-reads current native state and can call only original `0x5323830c` with an empty stock function object. It never clears in-flight, injects input or sends a manufactured completion. Return REQUEST_ACCEPTED means only that original API returned nonzero; it never means success on LCD. If QuickView is stranded state2, QUICK_INACTIVE cannot be honestly supplied, so this API must not mask the missing event with a resume.

The five facts are an integration contract, **not assertions inferred by this module**. A BE/Store hook does not establish owning UI thread, capture/save owner completion or QuickView inactivity. Root integration should initially install only the boundary data collection and obtain these facts at actual native UI/owner boundaries before enabling requests.

## Implemented repair: defer the real completion until the real stop reply

The proposed synchronous `Send169` race was **not established**. Original `0x532288b0` builds a 12-byte UI event, locks its bounded ring, appends the event, unlocks and signals `0x536a9d1c`; it contains no controller invocation. Native backend event routing `0x53225818..0x5322582c` also enters ShootingModel through the UI model route. Accordingly, no producer shooting flags were moved before notification on speculative race grounds.

Original f2 is **not a completion retry**: `0x532254e8 → 0x532255ec → 0x5328a3d4 → 0x5328a388` reads property through `0x5354af80`, posts UI150 and updates that model+5. Its 2-second timer semantics remain unchanged.

The implemented narrower repair follows a real outstanding native request:

* Original `0x53237194` requires `model+2f!=0`, `+31==0`, `+30==0`, `+7e9==5`. It sets `+30=1` at `0x53237200`, then sends **native request `0x42410921`**. This is a real in-flight native state, never a flag the patch can clear.
* Original response `0x53239b80` updates native state, posts UI15d, calls original `0x53239ad8`, then clears `+30` at `0x53239bc0`. If a real UI169 had earlier been refused solely because this request remained busy, original response does not revisit QuickView completion; the ARM fixture reproduces QuickView state2 persisting after that real clear.
* New module remembers that exact refused completion and revisits **original `0x531cbe78`** after the real native response clear. It does not manufacture169, input or LiveView completion, and does not invoke a BE worker recovery. Existing native handler performs state0/f1/user timeout exactly as normal.

New implementation: `native/gr3/m10v_view_deferred.[ch]`. New independent builder: `scripts/build_gr3_view_deferred.py`, API `build(out,base,rtos=None)`; root builder must choose a non-overlapping appendRX base and install **all six** patches together. Standalone default `0x54100000` is only an isolated test address.

The coordinated original allocation changes QuickViewController factory bytes `0x184 → 0x194` at `0x531709fc`; the new 16-byte token lives at controller+184. No global mutable pointer or image memory backs control. Entry at `0x531cbdf0` starts a new generation, invalidating pending completion. Original native capture-start at `0x5323abf8` also invalidates generation. Real backend completion producer at `0x53236768` publishes that generation before delegating to the unchanged original UI sender. The real169 handler at `0x531cc1cc` always executes original `0x531cbe78` first; only a remaining QuickView state2, actual model+30 nonzero, model+2f/+31 zero and **a producer published in this same generation** can arm deferred completion. Thus an old queued169 after a new native capture cannot borrow the new controller generation.

Only actual native response clear at `0x53239bc0` can consume deferred completion. Model+31 must remain zero, QuickView must still have exact original vptr and state2, model+2f/+30 must both be zero, and token generation must match. Token is consumed before calling native handler, so a duplicate response cannot complete twice. The patch never clears native busy/inflight, changes save requests, touches frame buffers, uses a timer, writes files or injects input. It retains all original producer shooting flag stores after original sender.

Validation: `tests/test_gr3_view_recovery.py` now **10 tests PASS**, including `scripts/analyze_gr3_view_deferred.py`. The independent ARM fixture runs original backend producer, original UI169 dispatcher/handler, original busy getter and original native response bytes. Stock reproduces the retained state2; patched execution reaches state0 and posts f1 once. Actual original state-setting UI/OS services are declared stubs, while the native gate and repair code execute real ARM. New controller entry, new native capture, stale queued169 across new capture,169 without a current native producer, and duplicate response all refuse an unsafe replay. Three arbitrary instruction-site adapters preserve **all GPR/LR/SP/NZCV** at their exact original continuations. ABI validation uses explicit code-boundary stops so cached Unicorn translation blocks cannot execute a naked stock epilogue without its original frame. This is a CPU/control-path repair demonstration, **not proof the user's camera hit this path or LCD recovery on hardware**.

Final hook hardening: all four assembly boundaries preserve **d0-d31 and FPSCR** in addition to GPR/LR/SP/NZCV. Adversarial ARM tests overwrite every D register and FPSCR inside each added C helper; the reply test additionally executes original `0x531cbe78` and overwrites FP again in its UI service boundary. Exact original continuations retain every saved value. The producer adapter is separately checked through its original sender tail call. Linked default-base module is **1584 bytes**, SHA256 `e6df3178212a5f47d54e13df76ccc6b50f87e95ec4a458e2290c90f2983a23ad`; addresses/hash naturally change when the integration builder chooses a different base. Final focused suite remains **10 tests PASS**. These tests require Unicorn execution outside this machine's sandbox.
