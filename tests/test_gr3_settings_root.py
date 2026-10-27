"""Original ARM TopMenu loader evidence, not hardware integration tests."""
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('settings_audit', ROOT/'scripts/analyze_gr3_settings.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SettingsRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('M10V_GR3_ORIGINAL_RTOS', '/tmp/m10v-sd-research/rtos.bin'))
        if not path.exists():
            raise unittest.SkipTest('set M10V_GR3_ORIGINAL_RTOS to official GR III 2.10 RTOS')
        cls.data = audit.read_firmware(path)

    def test_crop_root_enters_unified_editor_without_duplicate_setup_row(self):
        from collections import defaultdict
        from scripts.build_gr3_settings_hooks import build_settings_hooks
        _, report = build_settings_hooks(0x540c0000, defaultdict(lambda:0x540c1000))
        patched=bytearray(self.data)
        for patch in report['patches']:
            at=patch['address']-audit.BASE
            expected=bytes.fromhex(patch['expected'])
            self.assertEqual(patched[at:at+len(expected)],expected)
            patched[at:at+len(expected)]=bytes.fromhex(patch['replacement'])
        old,_=audit.emulate_loader(self.data)
        new,_=audit.emulate_loader(bytes(patched))
        self.assertEqual(struct.unpack_from('<I',old,0x3e4+28*4)[0],0x02000074)
        self.assertEqual(struct.unpack_from('<I',new,0x3e4+28*4)[0],0x0200f105)
        self.assertEqual(new[4*0x384+0x2b3],32)
        for category in range(5):
            for row in range([38,18,16,22,30][category]):
                if (category,row)==(0,28):continue
                offset=category*0x384+0x3e4+row*4
                self.assertEqual(new[offset:offset+4],old[offset:offset+4])

    def test_sha_fails_closed(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'not official firmware'); f.flush()
            with self.assertRaises(ValueError): audit.read_firmware(f.name)

    def test_descriptor_capacities(self):
        cats = audit.describe(self.data)
        self.assertEqual([c['count'] for c in cats], [38,18,16,22,30])
        self.assertEqual(cats[4]['starts'], [0,7,11,13,15,17,20,23,25,27,29])
        self.assertEqual(cats[4]['pages'], 11)

    def test_original_loader_exact_rows(self):
        output, _ = audit.emulate_loader(self.data)
        for category, desc in enumerate(audit.describe(self.data)):
            c = category*0x384
            self.assertEqual(output[c+0x2b3], desc['count'])
            for i, row in enumerate(desc['rows']):
                self.assertEqual(list(struct.unpack_from('<II',output,c+0x2b4+i*8)),row['render'])
                self.assertEqual(struct.unpack_from('<I',output,c+0x3e4+i*4)[0],row['route'])
                self.assertEqual(list(struct.unpack_from('<II',output,c+0x47c+i*8)),row['predicate'])

    def test_append_preserves_every_original_row_and_other_categories(self):
        for predicate in (False, True):
            old, _ = audit.emulate_loader(self.data, predicate=predicate)
            new, _ = audit.emulate_loader(self.data, append=True, predicate=predicate)
            c=4*0x384
            self.assertEqual(old[:c+0x228],new[:c+0x228])
            self.assertEqual(new[c+0x2b3],32)
            self.assertEqual(new[c+0x290],11)
            self.assertEqual(old[c+0x2a8:c+0x2b3],new[c+0x2a8:c+0x2b3])
            for offset,stride in ((0x2b4,8),(0x3e4,4),(0x47c,8)):
                self.assertEqual(old[c+offset:c+offset+30*stride],new[c+offset:c+offset+30*stride])
            for row in (30,31):
                self.assertEqual(struct.unpack_from('<I',new,c+0x3e4+row*4)[0],0x0200f000+row)

    def test_owner_extension_has_single_direct_ctor_site(self):
        sites=[]
        for offset in range(0,len(self.data)-3,4):
            word=struct.unpack_from('<I',self.data,offset)[0]
            if word & 0x0e000000 == 0x0a000000:
                immediate=word & 0xffffff
                if immediate & 0x800000: immediate-=0x1000000
                if audit.BASE+offset+8+immediate*4 == 0x5319aa68: sites.append(audit.BASE+offset)
        self.assertEqual(sites,[0x5316fcf8])
        self.assertEqual(self.data[0x16fcec:0x16fcf0],bytes.fromhex('bc0301e3'))
        # This confirms the site/size; it does not prove a custom ctor/dtor wrapper.

class SettingsKeyRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SettingsRootTests.setUpClass()
        cls.data=SettingsRootTests.data

    def test_new_routes_require_key_selector_extension(self):
        self.assertEqual(audit.emulate_key_route(self.data,0x0200004a),0x53215004)
        self.assertEqual(audit.emulate_key_route(self.data,0x0200004e),0x53218fa4)
        for route in (0x0200f100,0x0200f101):
            self.assertEqual(audit.emulate_key_route(self.data,route),0x536b93d0)

    def test_imagecontrol_mapper_does_not_offer_horizontal_events(self):
        expected={9:[0xd1],10:[0xd0],11:[0xd8],14:[0xd8],16:[0xde],
                  22:[0xde],27:[0xd4],30:[0xd5],32:[0xd8],35:[0xde],
                  50:[0xd8],7:[0x86],19:[0x89],57:[0xda]}
        for key,events in expected.items():
            with self.subTest(key=key):
                self.assertEqual(audit.emulate_topmenu_key(self.data,key,image_control=True),events)

    def test_topmenu_key_to_semantic_events(self):
        expected={9:[0xd1],10:[0xd0],11:[0xce],12:[0xce],14:[0xd8],
                  16:[0xcf],17:[0xd3],24:[0xd1],25:[0xd0],26:[0xd0],
                  27:[0xd4],29:[0xd1],30:[0xd5],32:[0xce],33:[0xce],
                  35:[0xcf],36:[0xd3],50:[0xd8],5:[0x86],7:[0x86],63:[0x86]}
        for key,events in expected.items():
            with self.subTest(key=key): self.assertEqual(audit.emulate_topmenu_key(self.data,key),events)
        for key in (0,65,0xffffffff): self.assertEqual(audit.emulate_topmenu_key(self.data,key),[])


if __name__ == '__main__': unittest.main()
