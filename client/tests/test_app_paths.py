import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths


class ApplicationPathsTest(unittest.TestCase):
    def test_development_root_is_client_directory(self) -> None:
        with patch.object(app_paths.sys, "frozen", False, create=True):
            root = app_paths.get_application_root()

        self.assertEqual(root, Path(app_paths.__file__).resolve().parent)

    def test_frozen_root_is_executable_parent(self) -> None:
        executable = Path("C:/Portable/DotExpress/DotExpress.exe")
        with (
            patch.object(app_paths.sys, "frozen", True, create=True),
            patch.object(app_paths.sys, "executable", str(executable)),
        ):
            root = app_paths.get_application_root()

        self.assertEqual(root, executable.resolve().parent)

    def test_build_application_paths_uses_one_root(self) -> None:
        root = Path("C:/DotExpress")

        paths = app_paths.build_application_paths(root)

        self.assertEqual(paths.root, root)
        self.assertEqual(paths.config, root / "config.json")
        self.assertEqual(paths.dictionary, root / "dictionary")
        self.assertEqual(paths.workspace, root / "workspace")
        self.assertEqual(paths.log, root / "log")
        self.assertEqual(paths.dual_view, root / "dual_view")

    def test_prepare_creates_and_probes_every_writable_directory(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory) / "application"
            paths = app_paths.build_application_paths(root)
            probed: list[Path] = []

            class Probe:
                def __init__(self, path: Path):
                    self.path = path

                def __enter__(self):
                    probed.append(self.path)
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

            prepared = app_paths.prepare_application_directories(
                paths,
                probe_factory=lambda *, dir: Probe(Path(dir)),
            )

            self.assertEqual(prepared, paths)
            self.assertEqual(probed, list(paths.writable_directories))
            self.assertTrue(all(path.is_dir() for path in paths.writable_directories))

    def test_prepare_reports_the_exact_unwritable_directory(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            paths = app_paths.build_application_paths(Path(directory))

            class Probe:
                def __init__(self, path: Path):
                    self.path = path

                def __enter__(self):
                    if self.path == paths.log:
                        raise PermissionError("denied")
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

            with self.assertRaises(app_paths.ApplicationDataError) as raised:
                app_paths.prepare_application_directories(
                    paths,
                    probe_factory=lambda *, dir: Probe(Path(dir)),
                )

        self.assertEqual(raised.exception.path, paths.log)
        self.assertIsInstance(raised.exception.cause, PermissionError)

    def test_prepare_reports_an_existing_unwritable_config_file(self) -> None:
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            paths = app_paths.build_application_paths(Path(directory))
            paths.config.write_text("{}", encoding="utf-8")
            with patch.object(Path, "open", side_effect=PermissionError("read only")):
                with self.assertRaises(app_paths.ApplicationDataError) as raised:
                    app_paths.prepare_application_directories(paths)

        self.assertEqual(raised.exception.path, paths.config)
        self.assertIsInstance(raised.exception.cause, PermissionError)

    def test_consumers_use_the_common_application_root(self) -> None:
        import config
        import dictionaries.manager as dictionary_manager
        import documents.workspace as document_workspace

        paths = app_paths.build_application_paths()

        self.assertEqual(Path(config.CONFIG_PATH), paths.config)
        self.assertEqual(dictionary_manager.get_dictionary_directory(), paths.dictionary)
        self.assertEqual(document_workspace.get_workspace_directory(), paths.workspace)


if __name__ == "__main__":
    unittest.main()
