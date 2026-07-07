from pathlib import Path
import unittest

from conversion.jobs import (
	ConversionJobFailure,
	ConversionJobRequest,
	ConversionJobRunner,
	ConversionJobSuccess,
)
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError


class FakeThread:
	def __init__(self, *, target, args=(), daemon=None):
		self._target = target
		self._args = args
		self.daemon = daemon
		self.started = False
		self._alive = False

	def start(self) -> None:
		self.started = True
		self._alive = True

	def is_alive(self) -> bool:
		return self._alive

	def run(self) -> None:
		try:
			self._target(*self._args)
		finally:
			self._alive = False


class ConversionJobRunnerTest(unittest.TestCase):
	def make_request(self) -> ConversionJobRequest:
		return ConversionJobRequest(
			conversion_request=ConversionRequest(
				raw_text="source",
				table_file="zh-tw.ctb",
				output_mode="unicode",
				width=40,
				dictionary_path=Path("dictionary/default.csv"),
				data_dir=Path("data"),
				translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
			)
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
			self.assertEqual(request, self.make_request().conversion_request)
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
		self.assertEqual(successes, [ConversionJobSuccess(job_id=2, conversion_output=ConversionOutput("second", ("new",)))])
		self.assertEqual(failures, [])


if __name__ == "__main__":
	unittest.main()
