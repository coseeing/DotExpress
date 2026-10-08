import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "sync-nvda.py"
NVDA_HELPER = ROOT / "include" / "nvda" / "source" / "louisHelper.py"
RUNTIME_HELPER = ROOT / "vendor" / "nvda" / "liblouis" / "runtime" / "louis_helper.py"


def _load_sync_nvda():
    spec = importlib.util.spec_from_file_location("sync_nvda_snapshot", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(NVDA_HELPER.is_file(), "include/nvda submodule is not checked out")
class VendorHelperSnapshotTests(unittest.TestCase):
    def test_runtime_helper_snapshot_is_the_adapted_nvda_helper(self):
        expected = _load_sync_nvda()._adapt_helper(NVDA_HELPER.read_text(encoding="utf-8"))

        self.assertEqual(
            expected,
            RUNTIME_HELPER.read_bytes().decode("utf-8"),
            "regenerate vendor/nvda/liblouis/runtime/louis_helper.py with _adapt_helper",
        )


if __name__ == "__main__":
    unittest.main()
