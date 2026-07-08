from dataclasses import dataclass, field
import threading
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from conversion.service import (
	ConversionOutput,
	ConversionRequest,
	ConversionStageError,
	convert_text_with_alignment,
)


@dataclass(frozen=True)
class ConversionCompletionPolicy:
	on_success: Callable[[str], object] | None = None
	on_error: Callable[[str], object] | None = None
	update_output: bool = True
	show_success: bool = True


@dataclass(frozen=True)
class ConversionJobRequest:
	conversion_request: ConversionRequest
	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)


@dataclass(frozen=True)
class ConversionJobSuccess:
	job_id: int
	conversion_output: ConversionOutput
	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)


@dataclass(frozen=True)
class ConversionJobFailure:
	job_id: int
	error: ConversionStageError
	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)


ThreadFactory = Callable[..., threading.Thread]
CallAfter = Callable[..., object]


class ConversionJobRunner:
	def __init__(
		self,
		*,
		runtime: TranslationRuntime,
		on_success: Callable[[ConversionJobSuccess], None],
		on_failure: Callable[[ConversionJobFailure], None],
		call_after: CallAfter,
		converter: Callable[..., ConversionOutput] = convert_text_with_alignment,
		thread_factory: ThreadFactory = threading.Thread,
	):
		self._runtime = runtime
		self._on_success = on_success
		self._on_failure = on_failure
		self._call_after = call_after
		self._converter = converter
		self._thread_factory = thread_factory
		self._job_id = 0
		self._thread: threading.Thread | None = None

	@property
	def active_job_id(self) -> int:
		return self._job_id

	def is_running(self) -> bool:
		return self._thread is not None and self._thread.is_alive()

	def start(self, request: ConversionJobRequest) -> int:
		self._job_id += 1
		job_id = self._job_id
		self._thread = self._thread_factory(
			target=self._run_job,
			args=(job_id, request),
			daemon=True,
		)
		self._thread.start()
		return job_id

	def _run_job(self, job_id: int, request: ConversionJobRequest) -> None:
		try:
			conversion_output = self._converter(
				request.conversion_request,
				runtime=self._runtime,
			)
		except ConversionStageError as error:
			self._call_after(
				self._deliver_failure,
				ConversionJobFailure(
					job_id=job_id,
					error=error,
					completion_policy=request.completion_policy,
				),
			)
			return
		self._call_after(
			self._deliver_success,
			ConversionJobSuccess(
				job_id=job_id,
				conversion_output=conversion_output,
				completion_policy=request.completion_policy,
			),
		)

	def _deliver_success(self, result: ConversionJobSuccess) -> None:
		if result.job_id != self._job_id:
			return
		self._thread = None
		self._on_success(result)

	def _deliver_failure(self, result: ConversionJobFailure) -> None:
		if result.job_id != self._job_id:
			return
		self._thread = None
		self._on_failure(result)
