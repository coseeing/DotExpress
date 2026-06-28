import sys
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "win32", "requires the Windows liblouis runtime")
class LiblouisRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from braille import liblouis
        from braille import louis_helper

        cls.louis = liblouis
        cls.helper = louis_helper
        cls.helper.initialize()

    @classmethod
    def tearDownClass(cls):
        cls.helper.terminate()

    def test_built_wrapper_loads_bundled_dll(self):
        dll = Path(__file__).parents[1] / "braille" / "liblouis.dll"
        self.assertTrue(dll.is_file())
        self.assertGreater(self.louis.charSize(), 0)
        self.assertTrue(self.louis.version())

    def test_table_resolver_finds_bundled_table(self):
        resolved = list(self.helper._resolveTableInner(["en-ueb-g2.ctb"]))
        self.assertEqual(1, len(resolved))
        self.assertTrue(Path(resolved[0]).is_file())

    def test_chinese_default_table_translates(self):
        result = self.louis.translateString(["zh-tw.ctb"], "中文")
        self.assertTrue(result)

    def test_ueb_grade_1_translates(self):
        result = self.louis.translateString(["en-ueb-g1.ctb"], "hello")
        self.assertTrue(result)

    def test_ueb_grade_2_translates_and_contracts(self):
        grade_1 = self.louis.translateString(["en-ueb-g1.ctb"], "the")
        grade_2 = self.louis.translateString(["en-ueb-g2.ctb"], "the")
        self.assertTrue(grade_2)
        self.assertNotEqual(grade_1, grade_2)
