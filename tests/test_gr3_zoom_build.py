import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ZoomBuildTests(unittest.TestCase):
    def test_compiled_module_and_verified_hook_inventory(self):
        path=ROOT/'scripts/build_gr3_zoom.py'
        self.assertTrue(path.exists(),'zoom runtime is not integrated into the build')
        spec=importlib.util.spec_from_file_location('zoom_builder',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        from scripts.build_gr3_m10v_library import capture_stock_rtos
        stock=capture_stock_rtos()
        blob,report=module.build(0x54180000,stock,aspect=True)
        self.assertGreater(len(blob),0)
        for p in report['patches']:
            self.assertEqual(int.from_bytes(stock[p['address']-0x53000000:p['address']-0x53000000+4],'little'),p['expected'])
            self.assertNotEqual(p['expected'],p['replacement'])
        for name in ('m10v_zoom_menu_open','m10v_zoom_camera_save','m10v_zoom_capture_resolution_hook','m10v_zoom_set'):
            self.assertGreaterEqual(report['symbols'][name],0x54180000)
            self.assertLess(report['symbols'][name],0x54180000+len(blob))
        bad=bytearray(stock);bad[0x1b6bf0]^=1
        with self.assertRaisesRegex(ValueError,'preimage'):
            module.build(0x54180000,bad,aspect=True)

    def test_shared_linker_keeps_gr4_view_independent_of_zoom(self):
        import os, shutil, subprocess, tempfile
        from scripts.build_gr3_m10v_library import FLAGS, link_object
        compiler=os.environ.get('M10V_LLVM_CLANG') or shutil.which('clang')
        self.assertTrue(compiler)
        with tempfile.TemporaryDirectory() as folder:
            obj=Path(folder)/'gr4-view.o'
            subprocess.run([compiler,*FLAGS,'-I',str(ROOT/'native/gr3'),'-c',str(ROOT/'native/gr4/m10v_settings_view.c'),'-o',str(obj)],check=True,capture_output=True)
            code,symbols=link_object(obj.read_bytes(),0x54400000,{'m10v_library_name':0x54410000},prefix='m10v_settings_view_')
            self.assertTrue(code)
            self.assertEqual(set(symbols),{'m10v_settings_view_create','m10v_settings_view_draw','m10v_settings_view_destroy'})
            with self.assertRaisesRegex(ValueError,'runtime API incomplete'):
                link_object(obj.read_bytes(),0x54400000,{'m10v_library_name':0x54410000},prefix='m10v_settings_view_',additional_exports=('m10v_settings_view_zoom',))
