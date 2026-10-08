from dataclasses import fields
from pathlib import Path
import unittest

from conversion.jobs import (
	ConversionJobFailure,
	ConversionJobRunner,
	ConversionJobSuccess,
)
from config import DEFAULT_CHARSET_MAPS
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from tests.conversion_harness import FakeThread, make_thread_factory


class ConversionJobRunnerTest(unittest.TestCase):
	def make_request(self) -> ConversionRequest:
		return ConversionRequest(
			raw_text="source",
			output_mode="unicode",
			width=40,
			dictionary_path=Path("dictionary/default.csv"),
			data_dir=Path("data"),
			translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
			lang="zh_TW",
			charset_maps=dict(DEFAULT_CHARSET_MAPS),
		)

	def make_runner(self, *, converter):
		successes: list[ConversionJobSuccess] = []
		failures: list[ConversionJobFailure] = []
		threads: list[FakeThread] = []

		def thread_factory(*, target, args=(), daemon=None):
			thread = FakeThread(target=target, args=args, daemon=daemon)
			threads.append(thread)
			return thread

		runner = ConversionJobRunner(
			runtime=object(),
			on_success=successes.append,
			on_failure=failures.append,
			call_after=lambda fn, *args: fn(*args),
			converter=converter,
			thread_factory=thread_factory,
		)
		return runner, successes, failures, threads

	def test_start_runs_conversion_and_reports_success(self) -> None:
		output = ConversionOutput("braille", ("segment",))

		def converter(request, *, runtime):
			self.assertEqual(request, self.make_request())
			self.assertIsNotNone(runtime)
			return output

		runner, successes, failures, threads = self.make_runner(converter=converter)

		job_id = runner.start(self.make_request())
		threads[0].run()

		self.assertEqual(job_id, 1)
		self.assertEqual(successes, [ConversionJobSuccess(job_id=1, conversion_output=output)])
		self.assertEqual(failures, [])

	def test_reports_conversion_stage_error_failure(self) -> None:
		error = ConversionStageError("translation", RuntimeError("boom"))

		def converter(_request, *, runtime):
			self.assertIsNotNone(runtime)
			raise error

		runner, successes, failures, threads = self.make_runner(converter=converter)

		job_id = runner.start(self.make_request())
		threads[0].run()

		self.assertEqual(successes, [])
		self.assertEqual(failures, [ConversionJobFailure(job_id=job_id, error=error)])

	def test_stale_job_completion_is_ignored(self) -> None:
		outputs = [
			ConversionOutput("first", ("old",)),
			ConversionOutput("second", ("new",)),
		]

		def converter(_request, *, runtime):
			self.assertIsNotNone(runtime)
			return outputs.pop(0)

		runner, successes, failures, threads = self.make_runner(converter=converter)

		first_job_id = runner.start(self.make_request())
		second_job_id = runner.start(self.make_request())
		threads[0].run()
		threads[1].run()

		self.assertEqual(first_job_id, 1)
		self.assertEqual(second_job_id, 2)
		self.assertEqual(
			successes,
			[
				ConversionJobSuccess(
					job_id=2,
					conversion_output=ConversionOutput("second", ("new",)),
				)
			],
		)
		self.assertEqual(failures, [])

	def test_stale_failure_completion_is_ignored(self) -> None:
		error = ConversionStageError("translation", RuntimeError("boom"))

		def converter(_request, *, runtime):
			self.assertIsNotNone(runtime)
			raise error

		runner, successes, failures, threads = self.make_runner(converter=converter)

		runner.start(self.make_request())
		second_job_id = runner.start(self.make_request())
		threads[0].run()
		threads[1].run()

		self.assertEqual(successes, [])
		self.assertEqual(failures, [ConversionJobFailure(job_id=second_job_id, error=error)])

	def test_each_start_creates_and_starts_one_daemon_thread(self) -> None:
		runner, _successes, _failures, threads = self.make_runner(
			converter=lambda _request, *, runtime: ConversionOutput("braille", ()),
		)

		self.assertEqual(runner.active_job_id, 0)
		self.assertFalse(runner.is_running())
		first_job_id = runner.start(self.make_request())
		self.assertEqual((first_job_id, runner.active_job_id, len(threads)), (1, 1, 1))
		second_job_id = runner.start(self.make_request())
		self.assertEqual((second_job_id, runner.active_job_id, len(threads)), (2, 2, 2))

		self.assertEqual([(thread.daemon, thread.started) for thread in threads], [(True, True), (True, True)])
		self.assertTrue(runner.is_running())

	def test_is_running_is_false_inside_completion_callbacks(self) -> None:
		seen: list[tuple[str, bool]] = []
		outcomes = [ConversionOutput("braille", ()), ConversionStageError("translation", RuntimeError("boom"))]

		def converter(_request, *, runtime):
			outcome = outcomes.pop(0)
			if isinstance(outcome, Exception):
				raise outcome
			return outcome

		thread_factory = make_thread_factory()
		runner = ConversionJobRunner(
			runtime=object(),
			on_success=lambda _result: seen.append(("success", runner.is_running())),
			on_failure=lambda _result: seen.append(("failure", runner.is_running())),
			call_after=lambda fn, *args: fn(*args),
			converter=converter,
			thread_factory=thread_factory,
		)

		# The synchronous call_after delivers while the worker thread is still alive.
		runner.start(self.make_request())
		thread_factory.threads[0].run()
		runner.start(self.make_request())
		thread_factory.threads[1].run()

		self.assertEqual(seen, [("success", False), ("failure", False)])

	def test_stale_delivery_keeps_the_current_job_running(self) -> None:
		runner, successes, failures, threads = self.make_runner(
			converter=lambda _request, *, runtime: ConversionOutput("braille", ()),
		)

		runner.start(self.make_request())
		runner.start(self.make_request())
		threads[0].run()

		self.assertEqual((successes, failures), ([], []))
		self.assertTrue(runner.is_running())
		self.assertEqual(runner.active_job_id, 2)

	def test_exception_outside_conversion_stage_error_delivers_nothing(self) -> None:
		def converter(_request, *, runtime):
			raise RuntimeError("unexpected")

		runner, successes, failures, threads = self.make_runner(converter=converter)

		runner.start(self.make_request())
		# KNOWN BUG (P1-4 spec, defect 6): nothing is delivered, so the UI would stay busy.
		with self.assertRaisesRegex(RuntimeError, "unexpected"):
			threads[0].run()

		self.assertEqual((successes, failures), ([], []))
		self.assertFalse(runner.is_running())
		self.assertEqual(runner.active_job_id, 1)


	def test_results_carry_only_the_job_id_and_the_outcome(self) -> None:
		self.assertEqual([field.name for field in fields(ConversionJobSuccess)], ["job_id", "conversion_output"])
		self.assertEqual([field.name for field in fields(ConversionJobFailure)], ["job_id", "error"])

if __name__ == "__main__":
	unittest.main()
