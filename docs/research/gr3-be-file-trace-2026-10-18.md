# Actual BE blocking file operation trace

`build_gr3_be_file_trace.build(out,base,trace_exports,flush,rtos=None)` produces the actual BE file trace module and two SHA/instruction-checked patches. It requires existing save trace `init` and `append` exports and a synchronous `m10v_lifecycle_file_flush` sink. It has zero writable global data. Camera behavior remains unverified.

The locked5350b2fc caller reserves30h stack bytes after its ten-register prologue. Thus its SP is fp-54. It constructs a24h-byte descriptor at fp-4c; descriptor offsets0 and10 are the frame slot and stage status. Immediately before BL5350b380, SP+0 andSP+4 contain no arguments to53697658. The callee consumes r0 manager, r1 descriptor, r2 extra and has no incoming positive-fp-offset loads throughout53697658..53697afc. Its body initializes its own frame and obtains other state from these registers and manager fields. Its saved registers and local allocations are below incoming SP. Original r3 happens to contain a context+3c value and is preserved exactly even though the callee overwrites r3 before consumption.

The pre-hook stores an optional656-byte heap trace pointer in original[SP], initializes the trace, records begin time, restores all r0-r12/LR/NZCV and tail-branches53697658. Stock receives the same original SP, register arguments, LR5350b384, descriptor pointer and descriptor bytes. No caller-frame expansion or callee-local memory slot is used. Downward stack growth cannot overwrite owner[SP]. After synchronous return, replacement branch5350b384 invokes the post-hook. It reads and clears owner[SP], records the exact original result and descriptor status, flushes synchronously, frees the trace, restores registers/flags/SP, replays displaced `ldrb r3,[fp,#-3c]`, then resumes5350b388. Original later diagnostic calls reuse the outgoing slots only after the trace owner has been cleared.

Identity is original caller r1, preserved by the stock caller in r5, and is an opaque **context cookie**. It is never dereferenced by instrumentation and is never labeled recipe or file number. Trace pointer is call-local, not a global manager-to-recipe association. Optional allocation failure continues the original call with owner zero; post-hook performs no clock/flush/free in that case.

Events are:

-200 `(context_cookie,begin_usec,begin_sec,clock_status)`.
-201 `(context_cookie,end_usec,end_sec,file_result_with_clock_status)`.
-202 `(context_cookie,stage_status,frame_slot,file_result)`.
-203 `(context_cookie,context_vptr,parameters_pointer_value,shooting_info_pointer_value)`.

Clock errors set high bit80000000 in the timestamp record's final value, matching the older file trace convention. Stage0 is native success,2 OPEN ERROR,4 META DATA ERROR,6 CLOSE ERROR. It is not inferred from the function return alone. This boundary encloses the actual manager file open, metadata operation and close flow with its original waits intact. Its completion still does not prove physical media durability or correlate the RAW source recipe.

The instrumentation contains no filesystem call in the service callback. Its flush sink executes only after the original blocking function returns, in5350b2fc's task. **A global filesystem-mutex proof is still absent**: neither this caller nor inner frame establishes the complete task's lock ownership. The sink must remain synchronous and satisfy integration's existing logging-safety contract; this module does not claim all locks have released. Heap allocation also occurs in that caller task, outside the callback.

Validation:11 targeted linked ARM tests pass, covering eight BE file cases (four native stage statuses times allocation success/failure), exact stock SP/register/NZCV/LR arguments, writes throughout512 bytes below original SP, descriptor integrity, output stage and original result, register/flag restoration, original displaced load, owner clear before flush, flush-before-free, and previous recipe/file/pool regression tests. Services are intercepted ARM boundaries; no camera result is claimed.

Event203 reads only three scalar fields of the original live context, after an aligned RAM extent84h check. Stock caller already accesses through context+82. It never follows the stored pointer values. It is intended to establish later ownership correlation without assuming these generic context fields currently identify a BEStillRecipe. Tests assert its exact fields; no recipe relation is asserted.
