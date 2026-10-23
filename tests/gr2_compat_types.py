"""GR II five-slot v4 ABI types pinned independently of GR III v5."""
import ctypes as C

class Slot(C.Structure):
    _fields_ = [('film', C.c_uint16), ('grain', C.c_uint8), ('soft', C.c_uint8), ('halo_gain',C.c_uint8),('halo_spread',C.c_uint8),('halo_threshold',C.c_uint8),('halo_profile',C.c_uint8)]


class State(C.Structure):
    _fields_ = [('magic', C.c_uint32), ('version', C.c_uint16), ('size', C.c_uint16),
                ('sequence', C.c_uint32), ('slots', Slot * 5),
                ('stamp', C.c_uint8), ('format', C.c_uint8), ('corner', C.c_uint8),
                ('color', C.c_uint8), ('effects', (C.c_uint8*8)*5), ('reserved', C.c_uint32), ('crc', C.c_uint32)]


class Image(C.Structure):
    _fields_ = [('y', C.POINTER(C.c_uint8)), ('chroma', C.POINTER(C.c_uint8))] + [
        (n, C.c_uint32) for n in ('y_bytes', 'chroma_bytes', 'width', 'height', 'stride')]


class Date(C.Structure):
    _fields_ = [('year', C.c_uint16)] + [(n, C.c_uint8) for n in ('month', 'day', 'hour', 'minute')]

