"""Genuine stock MENU row construction, focus callback and captions on ARM."""
import struct
import unittest
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_PC,UC_ARM_REG_LR
from tests import test_gr3_m10v_redraw_arm as ui
from tests import test_gr3_appended_slots as slot_tests


class AppendedMenuRenderTests(unittest.TestCase):
    visible_film_count=47
    setUpClass=classmethod(slot_tests.AppendedSlotsTests.setUpClass.__func__)
    word=ui.NativeRedrawArmTests.word
    put=ui.NativeRedrawArmTests.put
    call=ui.NativeRedrawArmTests.call
    focus=ui.NativeRedrawArmTests.focus

    def setUp(self):
        self.firmware=self.rom
        self.bank=0
        ui.NativeRedrawArmTests.setUp(self)

    def boundaries(self,u,address,size,data):
        if address==0x532c26c4:
            self.tone=u.reg_read(UC_ARM_REG_R1)
            self.assertIn(self.tone,[11,12,13,14,15,16,17,18,19,20,21,22,25,26,27,28,29])
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if address in (0x532bd61c,0x532bd6d4):
            if address==0x532bd61c:self.bank=u.reg_read(UC_ARM_REG_R1)
            u.reg_write(UC_ARM_REG_R0,self.bank);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        ui.NativeRedrawArmTests.boundaries(self,u,address,size,data)

    def test_genuine_menu_draws_custom_one_two_then_five_film_icons(self):
        custom=[self.call(0x532a9988,0,value) for value in (23,24)]
        self.call(0x531ac074,ui.CONTROLLER)
        self.assertEqual([self.icons[i] for i in range(12,19)],custom+[704,705,706,707,703])
        for row,tone,caption in ((14,25,879),(15,26,880),(16,27,881),(17,28,882),(18,29,860)):
            self.focus(row)
            self.assertEqual(self.tone,tone)
            self.assertEqual(self.captions[-1],caption)
            self.assertEqual(self.bank,0)
        self.focus(12);self.assertEqual(self.bank,1)
        self.focus(13);self.assertEqual(self.bank,2)
        self.assertEqual(self.files,{})

    def test_actual_adj_rows_use_the_same_custom_first_order(self):
        self.put(ui.CONTROLLER+0x1f0,ui.VIEW)
        self.put(ui.CONTROLLER+0x164,0x55007000)
        custom=[self.call(0x532a9988,0,value) for value in (23,24)]
        for row in range(19):self.call(0x531a0690,ui.CONTROLLER,row)
        self.assertEqual([self.icons[i] for i in range(12,19)],custom+[704,705,706,707,703])
        for row,caption in ((14,879),(15,880),(16,881),(17,882),(18,860)):
            self.call(0x531a0538,ui.CONTROLLER,row)
            self.assertEqual(self.captions[-1],caption)
        self.tone=29;self.bank=0
        self.assertEqual([self.call(0x531a1500,ui.CONTROLLER,row) for row in range(19)],
                         [0]*18+[1])


if __name__=='__main__':unittest.main()
