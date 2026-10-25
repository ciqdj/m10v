#ifndef M10V_GR2_DETAIL_H
#define M10V_GR2_DETAIL_H
#include "../../compat/gr2-v1/native/gr3/m10v_library.h"
/* UI owner only. Same field IDs and immediate journal semantics as GR3,
 * with no dependency on its little-endian ImageControl widget layout. */
typedef struct {
 void *context;
 int (*load)(void *,m10v_library_state *);
 m10v_library_store store;
} gr2_detail_ops;
typedef struct {m10v_library_state saved;uint32_t slot,ready,error;} gr2_detail;
int gr2_detail_open(gr2_detail *,const gr2_detail_ops *,uint32_t slot);
uint32_t gr2_detail_field(const gr2_detail *,uint32_t row);
uint32_t gr2_detail_limit(const gr2_detail *,uint32_t field);
uint32_t gr2_detail_value(const gr2_detail *,uint32_t field);
/* packed = field<<8 | value. Field 11/value 0 resets just this slot. */
int gr2_detail_set(gr2_detail *,const gr2_detail_ops *,uint32_t packed);
#endif
