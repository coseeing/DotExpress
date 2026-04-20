import unittest

import startup_client_init


class _Thread:
    def __init__(self, target, daemon):
        self._target = target
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True
        self._target()


class StartupClientInitTest(unittest.TestCase):
    def test_background_check_starts_daemon_thread(self) -> None:
        calls = []
        threads = []

        def thread_factory(*, target, daemon):
            thread = _Thread(target, daemon)
            threads.append(thread)
            return thread

        thread = startup_client_init.start_client_init_background(
            run_client_init=lambda: calls.append("run"),
            thread_factory=thread_factory,
        )

        self.assertIs(thread, threads[0])
        self.assertTrue(thread.daemon)
        self.assertTrue(thread.started)
        self.assertEqual(calls, ["run"])

    def test_background_check_swallows_client_init_errors(self) -> None:
        def fail():
            raise RuntimeError("offline")

        thread = startup_client_init.start_client_init_background(
            run_client_init=fail,
            thread_factory=lambda *, target, daemon: _Thread(target, daemon),
        )

        self.assertTrue(thread.started)


if __name__ == "__main__":
    unittest.main()
