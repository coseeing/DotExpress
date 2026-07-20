import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call

from dual_view.browser import build_browser_command, find_browser_executable, open_html_in_browser


class DualViewBrowserTest(unittest.TestCase):
    def test_chromium_commands_request_new_window_and_size(self) -> None:
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        chrome = build_browser_command("chrome", Path("C:/Chrome/chrome.exe"), html_path, (900, 600))
        edge = build_browser_command("edge", Path("C:/Edge/msedge.exe"), html_path, (900, 600))

        self.assertEqual(chrome[:3], ["C:/Chrome/chrome.exe", "--new-window", "--window-size=900,600"])
        self.assertEqual(edge[:3], ["C:/Edge/msedge.exe", "--new-window", "--window-size=900,600"])
        self.assertTrue(chrome[-1].startswith("file:"))
        self.assertTrue(edge[-1].startswith("file:"))

    def test_firefox_command_requests_new_window_and_size(self) -> None:
        command = build_browser_command(
            "firefox",
            Path("C:/Firefox/firefox.exe"),
            Path("C:/DotExpress/dual_view/dual-view-one.html"),
            (1024, 768),
        )

        self.assertEqual(command[0:2], ["C:/Firefox/firefox.exe", "-new-window"])
        self.assertIn("file:", command[2])
        self.assertEqual(command[3:], ["-width", "1024", "-height", "768"])

    def test_discovery_prefers_path_before_standard_install_location(self) -> None:
        which = Mock(side_effect=lambda name: "C:/Path/chrome.exe" if name == "chrome.exe" else None)

        found = find_browser_executable(
            "chrome",
            which=which,
            environ={"LOCALAPPDATA": "C:/Users/me/AppData/Local"},
        )

        self.assertEqual(found, Path("C:/Path/chrome.exe"))
        self.assertEqual(which.call_args_list, [call("chrome.exe")])

    def test_discovery_uses_standard_install_location_when_path_misses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            program_files = Path(directory) / "Program Files"
            executable = program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"")

            found = find_browser_executable(
                "edge",
                which=Mock(return_value=None),
                environ={"PROGRAMFILES": str(program_files)},
            )

        self.assertEqual(found, executable)

    def test_launch_falls_through_chrome_edge_firefox_then_system(self) -> None:
        finder = Mock(side_effect=lambda browser: {
            "chrome": Path("C:/Chrome/chrome.exe"),
            "edge": Path("C:/Edge/msedge.exe"),
            "firefox": None,
        }[browser])
        popen = Mock(side_effect=[OSError("chrome failed"), OSError("edge failed")])
        startfile = Mock()
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        result = open_html_in_browser(
            html_path,
            (900, 600),
            finder=finder,
            popen=popen,
            startfile=startfile,
        )

        self.assertEqual(result, "system")
        self.assertEqual(finder.call_args_list, [call("chrome"), call("edge"), call("firefox")])
        self.assertEqual(popen.call_count, 2)
        startfile.assert_called_once_with(str(html_path.resolve()))

    def test_launch_stops_after_first_successful_process_creation(self) -> None:
        finder = Mock(return_value=Path("C:/Chrome/chrome.exe"))
        popen = Mock()
        startfile = Mock()

        result = open_html_in_browser(
            Path("C:/DotExpress/dual_view/dual-view-one.html"),
            (900, 600),
            finder=finder,
            popen=popen,
            startfile=startfile,
        )

        self.assertEqual(result, "chrome")
        finder.assert_called_once_with("chrome")
        popen.assert_called_once()
        startfile.assert_not_called()

    def test_missing_non_windows_fallback_raises_os_error(self) -> None:
        with self.assertRaisesRegex(OSError, "No supported browser"):
            open_html_in_browser(
                Path("/tmp/dual-view-one.html"),
                (900, 600),
                finder=lambda _browser: None,
                startfile=None,
            )

    def test_system_fallback_error_is_propagated(self) -> None:
        startfile = Mock(side_effect=OSError("association failed"))

        with self.assertRaisesRegex(OSError, "association failed"):
            open_html_in_browser(
                Path("C:/DotExpress/dual_view/dual-view-one.html"),
                (900, 600),
                finder=lambda _browser: None,
                startfile=startfile,
            )

        startfile.assert_called_once()
