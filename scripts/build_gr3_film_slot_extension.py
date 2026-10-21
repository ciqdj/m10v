"""GR III 2.10 shooting-only tone extension; no stock parameter-bank proxies.

Exact official instructions and metadata pairs are checked again by the Node
packager. Movie and RAW-development enumeration keeps its original tables.
"""
import struct
from scripts.build_gr3_menu_patches import assembly, branch, movw


def build_appended_slots(base, native_base, stock, symbols):
    image = bytearray()
    patches = []
    def patch(at, expected, replacement):
        if struct.unpack_from('<I',stock,at-0x53000000)[0]!=expected:
            raise ValueError('appended slot preimage differs: '+hex(at))
        patches.append(dict(address=at,expected=expected,replacement=replacement))
    def hook(at, expected, source):
        entry=base+len(image)
        image.extend(assembly(source,entry))
        patch(at,expected,branch(at,entry))
        return entry
    count=hook(0x532c2a9c,0xe1a0c00d,
        'ldrb ip,[r0,#0x1b];cmp ip,#0;bne fallback;'
        'push {r4,lr};bl '+hex(native_base+0x80)+';cmp r0,#12;moveq r0,#17;pop {r4,pc};'
        'fallback:;mov ip,sp;b 0x532c2aa0')
    index=hook(0x532c2c80,0xe1a0c00d,
        'ldrb ip,[r0,#0x1b];cmp ip,#0;bne fallback;sub ip,r1,#12;cmp ip,#5;'
        'addlo r0,ip,#25;bxlo lr;fallback:;mov ip,sp;b 0x532c2c84')
    position=hook(0x532c2f08,0xe1a0c00d,
        'ldrb ip,[r0,#0x1b];cmp ip,#0;bne fallback;sub ip,r1,#25;cmp ip,#5;'
        'addlo r0,ip,#12;bxlo lr;fallback:;mov ip,sp;b 0x532c2f0c')
    maximum=hook(0x532c2b7c,0xe30d3368,'mov r0,#17;bx lr')
    display=hook(0x5326c240,branch(0x5326c240,0x5326c2a0),
        'sub r0,r3,#25;cmp r0,#5;movlo r0,r3;blo 0x5326c22c;b 0x5326c2a0')
    for at,old,name in [
        (0x531ab7a8,0x532a985c,'menu_name'),
        (0x531ab894,0x532a9988,'menu_icon'),(0x531ab8bc,0x532a9988,'menu_icon'),
        (0x531a05ac,0x532c2c80,'index'),(0x531a070c,0x532c2c80,'index'),
        (0x531a0588,0x532a985c,'adj_name'),(0x531a06e0,0x532a9988,'adj_icon'),
    ]:
        patch(at,branch(at,old,True),branch(at,symbols['m10v_tone_menu_'+name],True))
    for at,name in [(0x531abe0c,'menu_matches'),(0x531a1500,'adj_matches'),(0x531a0ba0,'adj_select')]:
        patch(at,0xe1a0c00d,branch(at,symbols['m10v_tone_menu_'+name]))
    # Preserve all official EXIF pairs, append distinct private ImageTone codes.
    table=base+len(image)
    pairs=stock[0xd2b6f4:0xd2b6f4+48]+b''.join(struct.pack('<BBH',25+i,0,0x10c+i) for i in range(5))
    if len(pairs)!=68:raise ValueError('invalid stock ImageTone pairs')
    image.extend(pairs)
    for at,old,new in [
        (0x53599df4,0xe3a00030,0xe3a00044),
        (0x53599e20,0xe30bc6f4,movw(12,table&65535)),
        (0x53599e2c,0xe345c3d2,0xe340c000|(((table>>16)&0xf000)<<4)|((table>>16)&0xfff)),
        (0x53599e30,0xe2801030,0xe2801044),
        (0x53599e4c,0xe353000c,0xe3530011),
        (0x53599e60,0xe2800030,0xe2800044),
    ]:patch(at,old,new)
    return bytes(image),dict(schema='m10v-gr3-appended-slots/v1',base=base,bytes=len(image),
        tones=[25,26,27,28,29],stock_choices=12,shooting_choices=17,
        library_index=19,movie_choices=10,raw_development_choices=12,
        entries=dict(count=count,index=index,position=position,maximum=maximum,display=display),
        exif_table=table,exif_bytes=68,patches=patches,
        stock_parameter_proxy=False,state_version=4,camera_tested=False)
