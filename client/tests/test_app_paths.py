import ast
import inspect
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
        self.assertEqual(paths.script, root / "script")
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

    def test_the_script_folder_is_prepared_after_the_dictionary_folder(self) -> None:
        # F-18 (D1): created at startup next to dictionary/, like it.
        root = Path("C:/DotExpress")

        paths = app_paths.build_application_paths(root)

        self.assertEqual(
            paths.writable_directories,
            (root, root / "dictionary", root / "script", root / "workspace", root / "log", root / "dual_view"),
        )

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

        root = Path("C:/DotExpress")
        paths = app_paths.build_application_paths(root)

        self.assertEqual(config.ConfigStore(paths.config).path, root / "config.json")
        self.assertEqual(
            dictionary_manager.dictionary_path_for_name("default", paths.dictionary),
            root / "dictionary" / "default.csv",
        )
        self.assertEqual(
            document_workspace.document_package_path_for_name("alpha", paths.workspace),
            root / "workspace" / "alpha.dep",
        )


class ApplicationPathsApiTest(unittest.TestCase):
    """P2-6: the application root is resolved implicitly only by the composition roots and the logger."""

    CLIENT_DIR = Path(app_paths.__file__).resolve().parent

    def test_app_paths_offers_only_the_root_the_layout_and_the_startup_check(self) -> None:
        public = {
            name
            for name, value in vars(app_paths).items()
            if inspect.isfunction(value) and value.__module__ == app_paths.__name__ and not name.startswith("_")
        }

        self.assertEqual(
            public,
            {"get_application_root", "build_application_paths", "prepare_application_directories"},
        )
        paths = inspect.signature(app_paths.prepare_application_directories).parameters["paths"]
        self.assertIs(paths.default, inspect.Parameter.empty)

    def test_folder_parameters_have_no_default(self) -> None:
        import dictionaries.manager as manager
        import dictionaries.name_prompt as name_prompt
        import documents.workspace as workspace
        import dual_view.files as dual_view_files
        import text_scripts.manager as scripts

        cases = (
            (manager.dictionary_path_for_name, "dictionary_dir"),
            (manager.ensure_default_dictionary, "dictionary_dir"),
            (manager.list_dictionary_names, "dictionary_dir"),
            (manager.create_dictionary, "dictionary_dir"),
            (manager.import_dictionary, "dictionary_dir"),
            (manager.rename_dictionary, "dictionary_dir"),
            (manager.export_dictionary, "dictionary_dir"),
            (manager.delete_dictionary, "dictionary_dir"),
            (name_prompt.rename_dictionary_after_name_prompt, "dictionary_dir"),
            (scripts.script_path_for_name, "script_dir"),
            (scripts.ensure_no_processing_script, "script_dir"),
            (scripts.list_script_names, "script_dir"),
            (scripts.script_exists, "script_dir"),
            (scripts.create_script, "script_dir"),
            (scripts.import_script, "script_dir"),
            (scripts.rename_script, "script_dir"),
            (scripts.export_script, "script_dir"),
            (scripts.delete_script, "script_dir"),
            (workspace.ensure_workspace_directory, "workspace_dir"),
            (workspace.document_package_path_for_name, "workspace_dir"),
            (workspace.load_workspace_documents, "workspace_dir"),
            (dual_view_files.write_dual_view_html, "directory"),
            (dual_view_files.cleanup_dual_view_html, "directory"),
        )
        for function, name in cases:
            with self.subTest(function=f"{function.__module__}.{function.__name__}"):
                parameter = inspect.signature(function).parameters[name]
                self.assertIs(parameter.default, inspect.Parameter.empty)
                self.assertEqual(parameter.annotation, "Path")

    def test_only_the_composition_roots_and_the_logger_resolve_the_real_root(self) -> None:
        callers = set()
        for path in sorted(self.CLIENT_DIR.rglob("*.py")):
            relative = path.relative_to(self.CLIENT_DIR)
            if {"tests", ".venv", "__pycache__"} & set(relative.parts) or relative.parts[:2] == ("braille", "liblouis"):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or node.args or node.keywords:
                    continue
                function = node.func
                name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)
                if name == "build_application_paths":
                    callers.add(relative.as_posix())

        self.assertEqual(callers, {"gui.py", "log.py", "main.py"})


if __name__ == "__main__":
    unittest.main()
