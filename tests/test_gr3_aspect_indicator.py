"""Execute the native ratio-to-icon ABI, including stock and invalid ratios."""
import struct
from tests.test_gr3_aspect import AspectTests, BASE
from unicorn.arm_const import UC_ARM_REG_R0

class AspectIndicatorTests(AspectTests):
    def test_live_ratio_icon_mapping_in_native_widget_abi(self):
        for ratio, icon in ((0,257),(3,256),(1,339),(4,855),(5,856),(2,0),(255,0)):
            with self.subTest(ratio=ratio):
                # The composer binds the two appended native-library icons.
                code=bytearray(self.code)
                marker=code.index(struct.pack('<3I',0x49413741,0,0))
                struct.pack_into('<2I',code,marker+4,855,856)
                original=self.code
                try:
                    self.code=code
                    u=self.call(self.entries['m10v_aspect_live_icon'],0,ratio)
                    self.assertEqual(u.reg_read(UC_ARM_REG_R0),icon)
                finally:
                    self.code=original

    def test_unbound_private_icons_are_hidden(self):
        for ratio in (4,5):
            self.assertEqual(self.call(self.entries['m10v_aspect_live_icon'],0,ratio).reg_read(UC_ARM_REG_R0),0)

    def test_live_overlay_draws_bound_native_tile_and_respects_visibility(self):
        from unicorn import UC_HOOK_CODE, arm_const as A
        for ratio in (4,5):
            for width,height in ((720,480),(360,240)):
                for visible in (False,True):
                    with self.subTest(ratio=ratio,width=width,visible=visible):
                        original=self.code
                        code=bytearray(original)
                        at=code.index(struct.pack('<3I',0x49413741,0,0))
                        struct.pack_into('<2I',code,at+4,855,856)
                        self.code=code
                        try:u=self.live_machine(ratio,0x3f800000)
                        finally:self.code=original
                        view,surface=0x55002000,0x55003000
                        u.mem_write(view+0x9e,bytes([visible]))
                        for offset in (0x30,0x64):u.mem_write(view+offset,struct.pack('<4I',0,0,width,height))
                        packets=[]
                        returns={0x540b8000:0,0x5320804c:0x55000400,0x532081ec:0x55000500,0x53208298:0x55000600,0x540b88b4:0}
                        def native(uc,address,size,data):
                            if address==0x5320a7a8:
                                self.assertEqual(uc.reg_read(A.UC_ARM_REG_R0),0x55000600)
                                packets.append(struct.unpack('<11I',uc.mem_read(uc.reg_read(A.UC_ARM_REG_R1),44)))
                            elif address not in returns:return
                            uc.reg_write(A.UC_ARM_REG_R0,returns.get(address,0))
                            uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
                        u.hook_add(UC_HOOK_CODE,native)
                        u.reg_write(A.UC_ARM_REG_R0,view);u.reg_write(A.UC_ARM_REG_R1,surface)
                        u.emu_start(self.entries['m10v_aspect_draw'],0x550ff000,count=10000)
                        expected=(surface,width-68,48,60,40,width-68,48,60,40,855+ratio-4,0)
                        self.assertEqual(packets,[expected] if visible else [])

    def test_artwork_preserves_factory_frame_and_rebuilds_from_native_glyphs(self):
        from scripts.generate_gr3_aspect_icons import generate, ROOT
        from tests.test_gr3_zoom_icon_style_arm import IconStyle
        tiles,payload,report=generate()
        self.assertEqual(payload,(ROOT/'native/gr3/m10v_aspect_icons.rgba').read_bytes())
        IconStyle.setUpClass()
        stock=IconStyle().native(339)
        for tile in tiles:
            for y in range(40):
                for x in range(60):
                    if 12<=x<48 and 7<=y<33:continue
                    self.assertEqual(bytes(tile.getpixel((x,y))),stock[(y*60+x)*4:(y*60+x+1)*4])
