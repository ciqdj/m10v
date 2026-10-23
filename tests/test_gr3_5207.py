"""5207 color-only CPU fallback and retired journal effect contracts."""
import ctypes as C
import unittest
import zlib
from tests import test_gr3_m10v_library as harness
from tests.test_gr3_m10v_library import STORE, State

class Film5207Tests(unittest.TestCase):
    setUpClass=classmethod(harness.NativeFilmLibraryTests.setUpClass.__func__)
    state=harness.NativeFilmLibraryTests.state
    image=harness.NativeFilmLibraryTests.image
    render=harness.NativeFilmLibraryTests.render

    def test_5207_selection_resets_effects_without_touching_other_slots(self):
        state=self.state();ok=STORE(lambda _,p:0)
        self.lib.m10v_library_texture(C.byref(state),0,3,3,ok,None)
        self.lib.m10v_library_halation(C.byref(state),0,8,8,0,3,ok,None)
        others=bytes(state.slots)[8:]
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,66,ok,None),0)
        self.assertEqual(self.lib.m10v_library_name(66),b'5207')
        self.assertEqual((state.slots[0].grain,state.slots[0].soft,state.slots[0].halo_gain),(0,0,0))
        self.assertEqual(bytes(state.slots)[8:],others)
        self.assertEqual((state.version,state.size),(4,C.sizeof(State)))

    def test_retired_effect_update_is_rejected_and_neutral_store_failure_is_atomic(self):
        state=self.state();ok=STORE(lambda _,p:0);bad=STORE(lambda _,p:-1)
        self.lib.m10v_library_select(C.byref(state),0,66,ok,None)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        for field in range(5):
            before=bytes(state)
            self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,field,1,ok,None),-1)
            self.assertEqual(bytes(state),before)
        state.effects[0][1]=8;state.crc=zlib.crc32(bytes(state)[:-4]);before=bytes(state)
        self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,1,0,bad,None),-2)
        self.assertEqual(bytes(state),before)

    def test_imported_leak_is_inert_for_all_films_and_reset_preserves_halation(self):
        ok=STORE(lambda _,p:0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        for film in range(1,79):
            with self.subTest(film=film):
                state=self.state();self.lib.m10v_library_select(C.byref(state),0,film,ok,None)
                im,y,uv,tmp=self.image(16,2);self.assertEqual(self.render(im,state,tmp),0);base=bytes(y),bytes(uv)
                state.effects[0][0:5]=[2,8,5,8,1];state.crc=zlib.crc32(bytes(state)[:-4])
                im,y,uv,tmp=self.image(16,2);self.assertEqual(self.render(im,state,tmp),0)
                self.assertEqual(base,(bytes(y),bytes(uv)))
                halo=bytes(state.slots[0])[4:]
                self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,5,0,ok,None),0)
                self.assertEqual(state.slots[0].film,film);self.assertEqual(bytes(state.effects[0])[:5],bytes(5))
                self.assertEqual(bytes(state.slots[0])[4:],halo)

    def test_5207_rejects_800t_halation_controls(self):
        state=self.state();ok=STORE(lambda _,p:0)
        self.lib.m10v_library_select(C.byref(state),0,66,ok,None);before=bytes(state)
        self.assertLess(self.lib.m10v_library_halation(C.byref(state),0,8,8,0,3,ok,None),0)
        self.assertEqual(bytes(state),before)

if __name__=='__main__':unittest.main()
