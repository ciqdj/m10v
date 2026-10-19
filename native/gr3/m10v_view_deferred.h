#ifndef M10V_VIEW_DEFERRED_H
#define M10V_VIEW_DEFERRED_H
#include <stdint.h>
#define M10V_VIEW_DEFERRED_OFFSET 0x184u
#define M10V_VIEW_DEFERRED_BYTES 0x194u
#define M10V_VIEW_DEFERRED_MAGIC 0x37445651u
typedef struct {uint32_t magic,generation,pending_generation,reserved;} m10v_view_deferred;
/* Pure lifetime protocol: all storage belongs to the expanded native
 * QuickViewController, never a process-global or retired image recipe. */
void m10v_view_deferred_enter(m10v_view_deferred *);
void m10v_view_deferred_invalidate(m10v_view_deferred *);
uint32_t m10v_view_deferred_mark(m10v_view_deferred *,uint32_t quick_state,uint32_t busy);
uint32_t m10v_view_deferred_take(m10v_view_deferred *,uint32_t quick_state,uint32_t busy);
/* Camera-only owning UI boundary entrypoints, linked only by matching builder.
 * Event169 invokes the ORIGINAL handler first. It only records a deferred
 * native completion when that exact handler leaves state2 with real busy.
 * The original stop-response clear runs BEFORE retry. No forged UI event. */
void m10v_view_deferred_on_enter(uint32_t quick);
void m10v_view_deferred_on_producer(uint32_t model);
void m10v_view_deferred_on_169(uint32_t quick);
void m10v_view_deferred_on_capture_start(uint32_t model);
void m10v_view_deferred_on_stop_reply(uint32_t model);
#endif
