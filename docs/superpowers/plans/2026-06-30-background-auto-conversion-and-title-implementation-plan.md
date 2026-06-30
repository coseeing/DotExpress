# Background Auto-Conversion and Window Title Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓非匯出文件操作立即保存 pending 內容並在單一背景 worker 轉譯，只讓匯出等待必要的轉譯，同時以版本機制阻止舊結果回寫，並將視窗標題固定為 `文件名 - DotExpress`。

**Architecture:** 新增不依賴 wx 的 `conversion.jobs`，以 session-only document id、單調遞增 `text_version`、唯一 `job_id` 管理單一背景 worker、queued replacement、logical cancellation 與結果 acceptance。`documents.workspace` 提供不轉譯的 pending save helper；`gui.py` 將非匯出操作接到 pending save/background queue，將手動轉譯與匯出接到 foreground continuation，所有 worker completion 再由 `wx.CallAfter` 回到 UI thread 更新 `Document`、`.dep` 與畫面。

**Tech Stack:** Python 3、`dataclasses`、`threading`、`collections.deque`、`unittest`、wxPython、gettext

---

## 檔案配置

- Create: `client/conversion/jobs.py` — conversion job model、document identity/version registry、單一背景 queue、logical cancellation 與 acceptance 判斷。
- Create: `client/tests/test_conversion_jobs.py` — queue replacement、單 worker、rename/delete、version rejection、manual cancellation 測試。
- Modify: `client/documents/workspace.py` — 新增不執行轉譯的 pending save helper，移除 save path 對同步 auto-convert 的依賴。
- Modify: `client/tests/test_document_workspace.py` — pending save 與 export 不允許空 braille 的測試。
- Modify: `client/gui.py` — 接入背景 queue、非阻塞文件操作、foreground export/manual conversion、close cancellation 與 title 更新。
- Create: `client/tests/test_document_flow.py` — 以不建立真實 wx frame 的 harness 測試 document save/queue/rename/delete/title helper 與 completion acceptance。
- Modify: `client/locales/dotexpress.pot` — 更新匯出轉譯失敗訊息。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — 新增匯出失敗訊息繁中翻譯。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 編譯 catalog。
- Reference: `docs/superpowers/specs/2026-06-30-background-auto-conversion-and-title-design.md`
- Reference: `docs/superpowers/specs/2026-06-30-background-auto-conversion-and-title-design_zh-TW.md`

## 實作約束

- `threading.Thread` 無法安全地強制終止。此處的「取消 running job」是立即將 job 標為 cancelled，使其結果永遠不可回寫；底層 converter 返回後 worker 才能取下一個背景 job。
- 手動轉譯與匯出使用 foreground thread，因此不必等待舊背景 job 返回。短時間內可能有一條已失效的背景 thread 與一條 foreground thread 同時存在，但同時間仍只有一個 background worker。
- worker thread 不得直接操作 wx control、`self.documents` 或 `.dep`。所有 completion 都必須透過注入的 dispatcher（GUI 使用 `wx.CallAfter`）回到 UI thread。
- `text_version`、document id、`job_id` 皆只存在於當次 process，不寫入 `.dep`。
- pending 的唯一持久化表示仍為 `Document.braille is None` 與既有 `.meta.json`，不改變 package schema。

### Task 1: 建立不轉譯的 pending save primitive

**Files:**
- Modify: `client/documents/workspace.py`
- Modify: `client/tests/test_document_workspace.py`

- [ ] **Step 1: 將既有同步 auto-convert 測試改為 pending save 測試**

在 `client/tests/test_document_workspace.py` 將 `prepare_document_for_save` import 改成 `prepare_document_for_pending_save`，並以以下測試取代兩個 `test_prepare_document_for_save_*`：

```python
    def test_prepare_document_for_pending_save_keeps_pending_document_pending(self) -> None:
        document = Document(name="lesson1", text="old", braille=None)

        prepared = prepare_document_for_pending_save(
            document,
            text="new text",
            braille="stale editor output",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille=None))

    def test_prepare_document_for_pending_save_preserves_completed_braille(self) -> None:
        document = Document(name="lesson1", text="old", braille="old braille")

        prepared = prepare_document_for_pending_save(
            document,
            text="new text",
            braille="edited braille",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="edited braille"))
```

- [ ] **Step 2: 執行測試並確認新 helper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_document_workspace.DocumentWorkspaceTest.test_prepare_document_for_pending_save_keeps_pending_document_pending tests.test_document_workspace.DocumentWorkspaceTest.test_prepare_document_for_pending_save_preserves_completed_braille -v`

Expected: FAIL with `ImportError: cannot import name 'prepare_document_for_pending_save'`.

- [ ] **Step 3: 以純資料轉換取代同步 auto-convert helper**

在 `client/documents/workspace.py` 移除 `prepare_document_for_save()`，加入：

```python
def prepare_document_for_pending_save(
    document: Document,
    *,
    text: str,
    braille: str,
) -> Document:
    return Document(
        name=document.name,
        text=text,
        braille=None if document.braille is None else braille,
    )
```

此 helper 不接收 converter，也不捕捉 conversion error，因此任何呼叫者都不可能在 save path 意外執行同步轉譯。

- [ ] **Step 4: 執行 workspace 測試**

Run: `cd client && python3 -m unittest tests.test_document_workspace -v`

Expected: all tests PASS.

- [ ] **Step 5: 提交 pending save primitive**

```bash
git add client/documents/workspace.py client/tests/test_document_workspace.py
git commit -m "refactor: separate pending document saves"
```

### Task 2: 建立 conversion job、版本 registry 與 acceptance 規則

**Files:**
- Create: `client/conversion/jobs.py`
- Create: `client/tests/test_conversion_jobs.py`

- [ ] **Step 1: 寫 document identity、版本與 job acceptance 的失敗測試**

建立 `client/tests/test_conversion_jobs.py`：

```python
import unittest

from conversion.jobs import ConversionJobRegistry


class ConversionJobRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ConversionJobRegistry()

    def test_text_change_increments_version_and_invalidates_old_job(self) -> None:
        document_id = self.registry.register("lesson", "first")
        old_job = self.registry.create_job(document_id, "first", payload="request")

        self.registry.record_text(document_id, "second")

        self.assertFalse(self.registry.accepts(old_job))
        self.assertEqual(self.registry.current_version(document_id), 1)

    def test_unchanged_text_keeps_version_and_accepts_current_job(self) -> None:
        document_id = self.registry.register("lesson", "same")
        job = self.registry.create_job(document_id, "same", payload="request")

        self.registry.record_text(document_id, "same")

        self.assertTrue(self.registry.accepts(job))
        self.assertEqual(self.registry.current_version(document_id), 0)

    def test_each_job_has_a_unique_job_id(self) -> None:
        document_id = self.registry.register("lesson", "text")

        first = self.registry.create_job(document_id, "text", payload="first")
        second = self.registry.create_job(document_id, "text", payload="second")

        self.assertNotEqual(first.job_id, second.job_id)
        self.assertEqual(first.text_version, second.text_version)

    def test_rename_preserves_document_identity_and_version(self) -> None:
        document_id = self.registry.register("old", "text")
        job = self.registry.create_job(document_id, "text", payload="request")

        self.registry.rename(document_id, "new")

        self.assertEqual(self.registry.document_name(document_id), "new")
        self.assertEqual(self.registry.document_id_for_name("new"), document_id)
        self.assertIsNone(self.registry.document_id_for_name("old"))
        self.assertTrue(self.registry.accepts(job))

    def test_unregister_rejects_late_result(self) -> None:
        document_id = self.registry.register("lesson", "text")
        job = self.registry.create_job(document_id, "text", payload="request")

        self.registry.unregister(document_id)

        self.assertFalse(self.registry.accepts(job))
        self.assertIsNone(self.registry.document_name(document_id))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試並確認 module 尚未存在**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs.ConversionJobRegistryTest -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'conversion.jobs'`.

- [ ] **Step 3: 實作 immutable job 與 session registry**

建立 `client/conversion/jobs.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from threading import RLock
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ConversionJob:
    document_id: str
    text_version: int
    job_id: int
    text: str
    payload: Any


@dataclass
class _DocumentState:
    name: str
    text: str
    text_version: int = 0


class ConversionJobRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._documents: dict[str, _DocumentState] = {}
        self._ids_by_name: dict[str, str] = {}
        self._job_ids = count(1)

    def register(self, name: str, text: str) -> str:
        with self._lock:
            existing = self._ids_by_name.get(name)
            if existing is not None:
                self.record_text(existing, text)
                return existing
            document_id = uuid4().hex
            self._documents[document_id] = _DocumentState(name=name, text=text)
            self._ids_by_name[name] = document_id
            return document_id

    def record_text(self, document_id: str, text: str) -> int:
        with self._lock:
            state = self._documents[document_id]
            if state.text != text:
                state.text = text
                state.text_version += 1
            return state.text_version

    def create_job(self, document_id: str, text: str, payload: Any) -> ConversionJob:
        with self._lock:
            version = self.record_text(document_id, text)
            return ConversionJob(document_id, version, next(self._job_ids), text, payload)

    def accepts(self, job: ConversionJob) -> bool:
        with self._lock:
            state = self._documents.get(job.document_id)
            return state is not None and state.text_version == job.text_version

    def current_version(self, document_id: str) -> int:
        with self._lock:
            return self._documents[document_id].text_version

    def document_name(self, document_id: str) -> str | None:
        with self._lock:
            state = self._documents.get(document_id)
            return state.name if state is not None else None

    def document_id_for_name(self, name: str) -> str | None:
        with self._lock:
            return self._ids_by_name.get(name)

    def rename(self, document_id: str, new_name: str) -> None:
        with self._lock:
            state = self._documents[document_id]
            self._ids_by_name.pop(state.name, None)
            state.name = new_name
            self._ids_by_name[new_name] = document_id

    def unregister(self, document_id: str) -> None:
        with self._lock:
            state = self._documents.pop(document_id, None)
            if state is not None:
                self._ids_by_name.pop(state.name, None)
```

- [ ] **Step 4: 執行 registry 測試**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs.ConversionJobRegistryTest -v`

Expected: 5 tests PASS.

- [ ] **Step 5: 提交 registry**

```bash
git add client/conversion/jobs.py client/tests/test_conversion_jobs.py
git commit -m "feat: track document conversion versions"
```

### Task 3: 實作單一背景 worker、queued replacement 與 logical cancellation

**Files:**
- Modify: `client/conversion/jobs.py`
- Modify: `client/tests/test_conversion_jobs.py`

- [ ] **Step 1: 寫 queue replacement、單 worker與 cancellation 的失敗測試**

在 `client/tests/test_conversion_jobs.py` 加入 imports：

```python
from threading import Event, Lock

from conversion.jobs import BackgroundConversionQueue, ConversionJobRegistry
```

並加入：

```python
class BackgroundConversionQueueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ConversionJobRegistry()
        self.completions = []
        self.queue = BackgroundConversionQueue(
            convert=lambda job: f"braille:{job.text}",
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )

    def tearDown(self) -> None:
        self.queue.shutdown()

    def test_newer_queued_job_replaces_older_job_for_same_document(self) -> None:
        gate = Event()
        started = Event()

        def convert(job):
            if job.text == "blocker":
                started.set()
                gate.wait(2)
            return f"braille:{job.text}"

        self.queue.shutdown()
        self.queue = BackgroundConversionQueue(
            convert=convert,
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )
        blocker_id = self.registry.register("blocker", "blocker")
        lesson_id = self.registry.register("lesson", "old")
        self.queue.submit(self.registry.create_job(blocker_id, "blocker", payload=None))
        self.assertTrue(started.wait(1))
        old_job = self.registry.create_job(lesson_id, "old", payload=None)
        self.queue.submit(old_job)
        new_job = self.registry.create_job(lesson_id, "new", payload=None)
        self.queue.submit(new_job)

        gate.set()
        self.assertTrue(self.queue.wait_until_idle(2))

        completed_ids = [result.job.job_id for result in self.completions]
        self.assertNotIn(old_job.job_id, completed_ids)
        self.assertIn(new_job.job_id, completed_ids)

    def test_worker_runs_only_one_background_conversion_at_a_time(self) -> None:
        active = 0
        maximum = 0
        lock = Lock()

        def convert(job):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            with lock:
                active -= 1
            return job.text

        self.queue.shutdown()
        self.queue = BackgroundConversionQueue(
            convert=convert,
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )
        for name in ("one", "two", "three"):
            document_id = self.registry.register(name, name)
            self.queue.submit(self.registry.create_job(document_id, name, payload=None))

        self.assertTrue(self.queue.wait_until_idle(2))
        self.assertEqual(maximum, 1)

    def test_cancelled_running_job_dispatches_no_completion(self) -> None:
        gate = Event()
        started = Event()

        def convert(job):
            started.set()
            gate.wait(2)
            return job.text

        self.queue.shutdown()
        self.queue = BackgroundConversionQueue(
            convert=convert,
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )
        document_id = self.registry.register("lesson", "text")
        job = self.registry.create_job(document_id, "text", payload=None)
        self.queue.submit(job)
        self.assertTrue(started.wait(1))

        self.queue.cancel_document(document_id)
        gate.set()
        self.assertTrue(self.queue.wait_until_idle(2))

        self.assertEqual(self.completions, [])

    def test_conversion_failure_is_returned_without_stopping_worker(self) -> None:
        self.queue.shutdown()
        self.queue = BackgroundConversionQueue(
            convert=lambda job: (_ for _ in ()).throw(ValueError(job.text)),
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )
        document_id = self.registry.register("lesson", "bad")
        self.queue.submit(self.registry.create_job(document_id, "bad", payload=None))

        self.assertTrue(self.queue.wait_until_idle(2))
        self.assertIsInstance(self.completions[0].error, ValueError)
        self.assertIsNone(self.completions[0].braille)
```

- [ ] **Step 2: 執行測試並確認 queue 尚未存在**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs.BackgroundConversionQueueTest -v`

Expected: FAIL with `ImportError: cannot import name 'BackgroundConversionQueue'`.

- [ ] **Step 3: 實作 queue 與 result model**

在 `client/conversion/jobs.py` 補上 imports：

```python
from collections import deque
from collections.abc import Callable
from threading import Condition, Thread
```

加入：

```python
@dataclass(frozen=True)
class ConversionResult:
    job: ConversionJob
    braille: str | None
    error: Exception | None


class BackgroundConversionQueue:
    def __init__(
        self,
        *,
        convert: Callable[[ConversionJob], str],
        dispatch: Callable[..., None],
        on_complete: Callable[[ConversionResult], None],
    ) -> None:
        self._convert = convert
        self._dispatch = dispatch
        self._on_complete = on_complete
        self._condition = Condition()
        self._queued: deque[ConversionJob] = deque()
        self._cancelled_job_ids: set[int] = set()
        self._running: ConversionJob | None = None
        self._stopping = False
        self._worker = Thread(target=self._run, name="document-auto-convert", daemon=True)
        self._worker.start()

    def submit(self, job: ConversionJob) -> None:
        with self._condition:
            retained = deque()
            for queued_job in self._queued:
                if queued_job.document_id == job.document_id:
                    self._cancelled_job_ids.add(queued_job.job_id)
                else:
                    retained.append(queued_job)
            retained.append(job)
            self._queued = retained
            self._condition.notify_all()

    def cancel_document(self, document_id: str) -> None:
        with self._condition:
            retained = deque()
            for job in self._queued:
                if job.document_id == document_id:
                    self._cancelled_job_ids.add(job.job_id)
                else:
                    retained.append(job)
            self._queued = retained
            if self._running is not None and self._running.document_id == document_id:
                self._cancelled_job_ids.add(self._running.job_id)
            self._condition.notify_all()

    def has_document(self, document_id: str) -> bool:
        with self._condition:
            return (
                self._running is not None and self._running.document_id == document_id
            ) or any(job.document_id == document_id for job in self._queued)

    def wait_until_idle(self, timeout: float) -> bool:
        with self._condition:
            return self._condition.wait_for(
                lambda: self._running is None and not self._queued,
                timeout=timeout,
            )

    def shutdown(self, *, wait: bool = True) -> None:
        with self._condition:
            self._stopping = True
            self._queued.clear()
            if self._running is not None:
                self._cancelled_job_ids.add(self._running.job_id)
            self._condition.notify_all()
        if wait:
            self._worker.join(timeout=1)

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopping or self._queued)
                if self._stopping:
                    return
                job = self._queued.popleft()
                self._running = job
            try:
                braille = self._convert(job)
                result = ConversionResult(job=job, braille=braille, error=None)
            except Exception as exc:
                result = ConversionResult(job=job, braille=None, error=exc)
            with self._condition:
                cancelled = job.job_id in self._cancelled_job_ids
                self._cancelled_job_ids.discard(job.job_id)
                self._running = None
                self._condition.notify_all()
            if not cancelled:
                self._dispatch(self._on_complete, result)
```

- [ ] **Step 4: 執行全部 job tests**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs -v`

Expected: 9 tests PASS and process exits without hanging worker threads.

- [ ] **Step 5: 提交 background queue**

```bash
git add client/conversion/jobs.py client/tests/test_conversion_jobs.py
git commit -m "feat: add background conversion queue"
```

### Task 4: 在 GUI 接入 pending save、背景 completion 與 session registry

**Files:**
- Modify: `client/gui.py`
- Create: `client/tests/test_document_flow.py`

- [ ] **Step 1: 寫純 harness 測試，鎖定 pending save、queue 與 stale completion**

建立 `client/tests/test_document_flow.py`。此測試不 import `wx`；它測試本 task 抽出的 `documents.session.apply_conversion_result`：

```python
import unittest

from conversion.jobs import ConversionJobRegistry, ConversionResult
from documents.session import apply_conversion_result
from documents.workspace import Document


class DocumentConversionFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ConversionJobRegistry()
        self.documents = [Document("lesson", "old", None)]
        self.document_id = self.registry.register("lesson", "old")

    def test_current_result_replaces_pending_document(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)
        result = ConversionResult(job=job, braille="braille", error=None)

        updated = apply_conversion_result(self.documents, self.registry, result)

        self.assertEqual(updated, Document("lesson", "old", "braille"))
        self.assertEqual(self.documents, [updated])

    def test_stale_result_does_not_replace_newer_text(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)
        self.registry.record_text(self.document_id, "new")
        self.documents[0] = Document("lesson", "new", None)
        result = ConversionResult(job=job, braille="stale", error=None)

        updated = apply_conversion_result(self.documents, self.registry, result)

        self.assertIsNone(updated)
        self.assertEqual(self.documents, [Document("lesson", "new", None)])

    def test_failed_result_keeps_document_pending(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)
        result = ConversionResult(job=job, braille=None, error=ValueError("boom"))

        updated = apply_conversion_result(self.documents, self.registry, result)

        self.assertIsNone(updated)
        self.assertEqual(self.documents, [Document("lesson", "old", None)])
```

- [ ] **Step 2: 執行測試並確認 apply helper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_document_flow -v`

Expected: FAIL with `ImportError: cannot import name 'apply_conversion_result'`.

- [ ] **Step 3: 在 session layer 實作 completion acceptance**

修改 `client/documents/session.py` imports：

```python
from conversion.jobs import ConversionJobRegistry, ConversionResult
```

加入：

```python
def apply_conversion_result(
    documents: list[Document],
    registry: ConversionJobRegistry,
    result: ConversionResult,
) -> Document | None:
    if result.error is not None or result.braille is None or not registry.accepts(result.job):
        return None
    name = registry.document_name(result.job.document_id)
    current = find_document(documents, name)
    if current is None:
        return None
    updated = Document(name=current.name, text=current.text, braille=result.braille)
    return updated if replace_document(documents, updated) else None
```

- [ ] **Step 4: 初始化 registry/queue，並改寫 open-document save**

在 `client/gui.py`：

1. import `BackgroundConversionQueue`, `ConversionJob`, `ConversionJobRegistry`, `ConversionResult`。
2. import `apply_conversion_result`。
3. 將 workspace import 的 `prepare_document_for_save` 改為 `prepare_document_for_pending_save`。
4. 在 `_initialize_conversion_state()` 建立：

```python
        self._conversion_registry = ConversionJobRegistry()
        self._background_conversions = BackgroundConversionQueue(
            convert=self._convert_background_job,
            dispatch=wx.CallAfter,
            on_complete=self._finish_background_conversion,
        )
        self._foreground_job = None
        self._foreground_continuation = None
```

5. 在 `_load_workspace_documents_at_startup()` 載入 documents 後逐一 register：

```python
        for document in self.documents:
            self._conversion_registry.register(document.name, document.text)
```

6. 將 `_save_open_document()` 改為只保存 pending 並回傳 `Document | None`：

```python
    def _save_open_document(self, *, queue_background: bool = True) -> Document | None:
        if not self._open_document_name:
            return None
        document = self._get_document_by_name(self._open_document_name)
        if document is None:
            return None
        updated_document = prepare_document_for_pending_save(
            document,
            text=self.input_txt.GetValue(),
            braille=self.output_txt.GetValue(),
        )
        self._replace_document(updated_document)
        document_id = self._conversion_registry.register(updated_document.name, updated_document.text)
        save_document_package(
            document_package_path_for_name(updated_document.name, self.workspace_dir),
            updated_document,
        )
        if queue_background and updated_document.braille is None:
            self._queue_background_conversion(document_id, updated_document)
        return updated_document
```

7. 將 `_save_open_document_with_feedback()` 改為只處理 `OSError`，不再顯示 automatic conversion error：

```python
    def _save_open_document_with_feedback(self, *, queue_background: bool = True) -> bool:
        try:
            self._save_open_document(queue_background=queue_background)
        except OSError as exc:
            self._show_file_error(_("Failed to save document: {error}"), exc)
            return False
        return True
```

8. 新增 background request、queue 與 completion：

```python
    def _create_conversion_job(self, document_id: str, document: Document) -> ConversionJob:
        table_file = language_map_translate_table.get("default")
        if not table_file:
            raise ValueError(_("Please select a translation table first."))
        settings = self.translation_settings
        request = self._build_conversion_request(
            document.text,
            table_file,
            settings.output_mode,
            settings.width,
            self._get_selected_dictionary_path(),
        )
        return self._conversion_registry.create_job(document_id, document.text, request)

    def _queue_background_conversion(self, document_id: str, document: Document) -> None:
        try:
            job = self._create_conversion_job(document_id, document)
        except ValueError:
            return
        self._background_conversions.submit(job)

    def _convert_background_job(self, job: ConversionJob) -> str:
        return convert_text_for_output(job.payload)

    def _finish_background_conversion(self, result: ConversionResult) -> None:
        updated = apply_conversion_result(self.documents, self._conversion_registry, result)
        if updated is None:
            return
        try:
            save_document_package(
                document_package_path_for_name(updated.name, self.workspace_dir),
                updated,
            )
        except OSError:
            pending = Document(updated.name, updated.text, None)
            self._replace_document(pending)
            return
        if self._open_document_name == updated.name:
            self.output_txt.SetValue(updated.braille or "")
```

- [ ] **Step 5: 在 source text 變更當下遞增版本**

在 `_bind_events()` 加入：

```python
        self.input_txt.Bind(wx.EVT_TEXT, self.on_input_text_changed)
```

新增 handler：

```python
    def on_input_text_changed(self, event: wx.CommandEvent) -> None:
        document_id = self._conversion_registry.document_id_for_name(self._open_document_name or "")
        if document_id is not None:
            self._conversion_registry.record_text(document_id, self.input_txt.GetValue())
        event.Skip()
```

這個 event 必須在使用者編輯當下 invalidates running result，而不是等到切換/匯出/手動轉譯觸發 save 才遞增。`_load_document_into_editors()` 的 `SetValue()` 也會觸發 event，但 registry 比對到相同 text 時不增加版本。

- [ ] **Step 6: register 新建與匯入文件**

在 `_create_document()` 成功 append 後加入：

```python
        self._conversion_registry.register(document.name, document.text)
```

在 `_persist_documents()` 每份成功保存的 document append 前加入：

```python
            self._conversion_registry.register(document.name, document.text)
```

匯入完成後，對每份 `braille is None` 的 `saved_documents` 呼叫 `_queue_background_conversion()`；單份匯入仍立即開啟，不等待 queue。

- [ ] **Step 7: 執行 state 與 workspace 測試**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs tests.test_document_flow tests.test_document_session tests.test_document_workspace -v`

Expected: all tests PASS.

- [ ] **Step 8: 提交 GUI background integration**

```bash
git add client/gui.py client/documents/session.py client/tests/test_document_flow.py
git commit -m "feat: save pending documents before background conversion"
```

### Task 5: 將 rename/delete/close 改為不等待並正確搬移或取消 job

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_conversion_jobs.py`
- Modify: `client/tests/test_document_flow.py`

- [ ] **Step 1: 補 rename queued ownership 與 delete cancellation 測試**

在 `BackgroundConversionQueueTest` 加入：

```python
    def test_cancel_document_removes_queued_job(self) -> None:
        gate = Event()
        started = Event()

        def convert(job):
            if job.text == "blocker":
                started.set()
                gate.wait(2)
            return job.text

        self.queue.shutdown()
        self.queue = BackgroundConversionQueue(
            convert=convert,
            dispatch=lambda callback, *args: callback(*args),
            on_complete=lambda result: self.completions.append(result),
        )
        blocker_id = self.registry.register("blocker", "blocker")
        deleted_id = self.registry.register("deleted", "deleted")
        self.queue.submit(self.registry.create_job(blocker_id, "blocker", payload=None))
        self.assertTrue(started.wait(1))
        deleted_job = self.registry.create_job(deleted_id, "deleted", payload=None)
        self.queue.submit(deleted_job)

        self.queue.cancel_document(deleted_id)
        self.registry.unregister(deleted_id)
        gate.set()
        self.assertTrue(self.queue.wait_until_idle(2))

        self.assertNotIn(deleted_job.job_id, [result.job.job_id for result in self.completions])
```

在 `DocumentConversionFlowTest` 加入：

```python
    def test_result_after_rename_updates_document_under_new_name(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)
        self.registry.rename(self.document_id, "renamed")
        self.documents[0] = Document("renamed", "old", None)
        result = ConversionResult(job=job, braille="braille", error=None)

        updated = apply_conversion_result(self.documents, self.registry, result)

        self.assertEqual(updated, Document("renamed", "old", "braille"))
```

- [ ] **Step 2: 執行測試並確認現有 primitive 支援 rename/delete**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs tests.test_document_flow -v`

Expected: PASS；這一步確認 GUI 可以只組合已測試 primitive，不需要在 worker 上加入 filename mutation。

- [ ] **Step 3: 改寫 rename flow**

在 `on_rename_document()`：

- 保留操作開始時的 `_save_open_document_with_feedback()`，它現在只做 pending save 並立即返回。
- 取得 `document_id = self._conversion_registry.document_id_for_name(selected_document.name)`。
- `.dep` rename 成功且 `rename_document_in_list()` 成功後，執行：

```python
        if document_id is not None:
            self._conversion_registry.rename(document_id, renamed_document.name)
        if self._open_document_name == selected_document.name:
            self._open_document_name = renamed_document.name
            self._update_window_title()
```

不要 cancel 或重新 queue；既有 job 以 stable document id 完成，callback 會解析目前新名稱並寫入新 `.dep`。

- [ ] **Step 4: 改寫 delete one/delete all flow**

在 `on_delete_document()`：

- 刪除操作前仍保存目前 open document，但使用 `_save_open_document_with_feedback(queue_background=False)`，避免剛 queue 又立即取消。
- confirmation 通過後，取得 selected document id。
- unlink 成功後執行：

```python
        if document_id is not None:
            self._background_conversions.cancel_document(document_id)
            self._conversion_registry.unregister(document_id)
```

在 `on_delete_all_documents()`：

- 使用 `_save_open_document_with_feedback(queue_background=False)`。
- confirmation 通過後，先收集所有 document ids。
- 每份 unlink 成功後 cancel/unregister 對應 id。
- 若中途 unlink 失敗，只 unregister 已成功刪除者，重新載入後為剩餘文件重新 register。

- [ ] **Step 5: 改寫 close flow**

將 `_on_close()` 改為：

```python
    def _on_close(self, evt: wx.CloseEvent):
        if not self._save_open_document_with_feedback(queue_background=False):
            if evt.CanVeto():
                evt.Veto()
            return
        self._background_conversions.shutdown(wait=False)
        self._convert_job_id += 1
        self._foreground_job = None
        self._foreground_continuation = None
        self._close_converting_dialog()
        evt.Skip()
```

移除「foreground conversion thread alive 時 veto close」的判斷。增加 `_closing` flag 並讓 foreground callback 在 frame closing 後直接丟棄，避免 daemon thread 返回後操作已銷毀的 wx frame。

- [ ] **Step 6: 執行 focused tests**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs tests.test_document_flow tests.test_document_session tests.test_document_workspace -v`

Expected: all tests PASS.

- [ ] **Step 7: 提交 non-export lifecycle**

```bash
git add client/gui.py client/tests/test_conversion_jobs.py client/tests/test_document_flow.py
git commit -m "feat: cancel background jobs on document removal"
```

### Task 6: 讓手動轉譯取消背景 job 並只接受最新 foreground result

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_document_flow.py`

- [ ] **Step 1: 寫 foreground acceptance helper 測試**

在 `client/documents/session.py` 加入下列 pure helper 的測試至 `client/tests/test_document_flow.py`：

```python
from documents.session import apply_conversion_result, accepts_foreground_result

    def test_manual_result_is_rejected_after_text_changes(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)
        self.registry.record_text(self.document_id, "new")

        self.assertFalse(accepts_foreground_result(self.registry, job, job.job_id))

    def test_manual_result_requires_current_foreground_job_id(self) -> None:
        job = self.registry.create_job(self.document_id, "old", payload=None)

        self.assertFalse(accepts_foreground_result(self.registry, job, job.job_id + 1))
        self.assertTrue(accepts_foreground_result(self.registry, job, job.job_id))
```

- [ ] **Step 2: 執行測試並確認 helper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_document_flow -v`

Expected: FAIL with `ImportError: cannot import name 'accepts_foreground_result'`.

- [ ] **Step 3: 實作 foreground acceptance helper**

在 `client/documents/session.py` 加入：

```python
def accepts_foreground_result(
    registry: ConversionJobRegistry,
    job: ConversionJob,
    current_job_id: int | None,
) -> bool:
    return current_job_id == job.job_id and registry.accepts(job)
```

並從 `conversion.jobs` import `ConversionJob`。

- [ ] **Step 4: 將 manual convert 建立為 registry job**

改寫 `on_convert()`：

1. 取得 open document；若不存在則 return。
2. 先以 editor text 呼叫 `_save_open_document_with_feedback(queue_background=False)`。
3. 取得 document id 並呼叫 `_background_conversions.cancel_document(document_id)`。
4. 以最新 `Document` 呼叫 `_create_conversion_job()`。
5. 呼叫統一的 `_start_foreground_conversion(job, continuation=self._complete_manual_conversion)`。

foreground worker 固定執行 `convert_text_for_output(job.payload)`，並以 `wx.CallAfter` 傳回 job/result。`_finish_foreground_conversion()` 必須先以 `accepts_foreground_result()` 檢查 job id 與 text version；被取消或 stale 時只關閉 dialog/busy state，不更新 output、不顯示完成訊息。

manual completion：

```python
    def _complete_manual_conversion(self, result: ConversionResult) -> None:
        updated = apply_conversion_result(self.documents, self._conversion_registry, result)
        if updated is None:
            return
        try:
            save_document_package(
                document_package_path_for_name(updated.name, self.workspace_dir),
                updated,
            )
        except OSError as exc:
            self._show_file_error(_("Failed to save document: {error}"), exc)
            return
        if self._open_document_name == updated.name:
            self.output_txt.SetValue(updated.braille or "")
            self.output_txt.SetFocus()
        wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
```

- [ ] **Step 5: 確認手動轉譯只取消同文件背景工作**

不要清空整個 background queue。`cancel_document(document_id)` 只 invalidates 同文件 queued/running job；其他文件仍由單 worker 依序處理。

- [ ] **Step 6: 執行 focused tests**

Run: `cd client && python3 -m unittest tests.test_conversion_jobs tests.test_document_flow -v`

Expected: all tests PASS.

- [ ] **Step 7: 提交 manual priority**

```bash
git add client/gui.py client/documents/session.py client/tests/test_document_flow.py
git commit -m "feat: prioritize manual document conversion"
```

### Task 7: 將三種匯出流程改為必要時 foreground 轉譯並在成功後續行

**Files:**
- Modify: `client/gui.py`
- Modify: `client/documents/workspace.py`
- Modify: `client/tests/test_document_workspace.py`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: 寫 export primitive 拒絕 pending document 的失敗測試**

在 `client/tests/test_document_workspace.py` 加入：

```python
    def test_export_document_brl_rejects_pending_document(self) -> None:
        output_path = Path(self._tmpdir.name) / "pending.brl"

        with self.assertRaisesRegex(ValueError, "pending"):
            export_document_brl(output_path, Document("pending", "text", None))

        self.assertFalse(output_path.exists())

    def test_batch_export_rejects_pending_document_before_writing_any_file(self) -> None:
        export_dir = Path(self._tmpdir.name) / "export"

        with self.assertRaisesRegex(ValueError, "pending"):
            batch_export_documents_to_folder(
                export_dir,
                [
                    Document("ready", "text", "braille"),
                    Document("pending", "text", None),
                ],
                format_key="brl",
                overwrite=True,
            )

        self.assertFalse((export_dir / "ready.brl").exists())
```

- [ ] **Step 2: 執行測試並確認目前會輸出空 braille**

Run: `cd client && python3 -m unittest tests.test_document_workspace.DocumentWorkspaceTest.test_export_document_brl_rejects_pending_document tests.test_document_workspace.DocumentWorkspaceTest.test_batch_export_rejects_pending_document_before_writing_any_file -v`

Expected: FAIL because current export silently writes an empty string.

- [ ] **Step 3: 在 workspace export boundary 拒絕 pending**

在 `client/documents/workspace.py` 加入：

```python
def require_completed_braille(document: Document) -> None:
    if document.braille is None:
        raise ValueError(f'Document "{document.name}" is pending braille conversion.')
```

`export_document_brl()` 寫檔前呼叫此 helper。`batch_export_documents_to_folder()` 先保留現有 conflict discovery/early return；當 `overwrite=True` 或沒有 conflicts、即將開始寫檔前，再對全部 documents 呼叫此 helper。DEP 與 BRL 都必須有 completed braille，因為 spec 規定匯出 `.dep` 不得繞過必要轉譯。

- [ ] **Step 4: 建立 `_ensure_document_ready_for_export` continuation**

移除 `_prepare_document_for_export()` 與所有 `prepare_document_for_save()` 使用。新增：

```python
    def _ensure_document_ready_for_export(
        self,
        document: Document,
        continuation,
    ) -> None:
        if document.braille is not None:
            continuation(document)
            return
        document_id = self._conversion_registry.document_id_for_name(document.name)
        if document_id is None:
            document_id = self._conversion_registry.register(document.name, document.text)
        self._background_conversions.cancel_document(document_id)
        try:
            job = self._create_conversion_job(document_id, document)
        except ValueError as exc:
            self._show_file_error(_("Automatic conversion failed while exporting: {error}"), exc)
            return
        self._start_foreground_conversion(
            job,
            continuation=lambda result: self._complete_export_conversion(result, continuation),
        )

    def _complete_export_conversion(self, result: ConversionResult, continuation) -> None:
        if result.error is not None:
            self._show_file_error(_("Automatic conversion failed while exporting: {error}"), result.error)
            return
        updated = apply_conversion_result(self.documents, self._conversion_registry, result)
        if updated is None:
            return
        try:
            save_document_package(
                document_package_path_for_name(updated.name, self.workspace_dir),
                updated,
            )
        except OSError as exc:
            self._show_file_error(_("Failed to save document: {error}"), exc)
            return
        if self._open_document_name == updated.name:
            self.output_txt.SetValue(updated.braille or "")
        continuation(updated)
```

「接管 existing background job」在 Python thread 無法 transfer callback，因此實作為 logical cancel existing job，再以相同最新 text/version 建立 foreground job。這保留正確性、立即顯示 converting feedback，且舊 background result 永遠不能回寫。

- [ ] **Step 5: 改寫 export one 與 Ctrl+S**

`on_export_document()` 先以 `_save_open_document_with_feedback(queue_background=False)` 保存 editor，再顯示 destination dialog。使用者確認路徑後才呼叫 `_ensure_document_ready_for_export(document, write_export)`，避免使用者取消 dialog 卻白做轉譯。

將 `_export_document_with_dialog()` 拆成：

```python
    def _choose_export_path(self, document: Document, format_key: str) -> Path | None:
        default_file = f"{document.name}.dep" if format_key == "dep" else f"{document.name}.brl"
        wildcard = self._get_dep_wildcard() if format_key == "dep" else self._get_brl_wildcard()
        with wx.FileDialog(
            self,
            _("Export Document"),
            defaultFile=default_file,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return None
            destination_path = Path(file_dialog.GetPath())
        target_suffix = ".dep" if format_key == "dep" else ".brl"
        if destination_path.suffix.casefold() != target_suffix:
            destination_path = destination_path.with_suffix(target_suffix)
        return destination_path
```

以及：

```python
    def _write_document_export(self, document: Document, format_key: str, destination_path: Path) -> None:
        try:
            if format_key == "dep":
                save_document_package(destination_path, document, include_pending_metadata=False)
            else:
                export_document_brl(destination_path, document)
        except (OSError, ValueError) as exc:
            self._show_file_error(_("Failed to export document: {error}"), exc)
```

Ctrl+S 呼叫同一 `on_export_document`/helper，不保留獨立 auto-convert path。

- [ ] **Step 6: 改寫 export all 為逐份 ensure 後一次寫出**

在選擇 destination 與 overwrite confirmation 後，建立 snapshot names 與 serial continuation：

```python
    def _prepare_export_documents(
        self,
        names: list[str],
        prepared: list[Document],
        on_ready,
    ) -> None:
        if not names:
            on_ready(prepared)
            return
        document = self._get_document_by_name(names[0])
        if document is None:
            return
        self._ensure_document_ready_for_export(
            document,
            lambda ready: self._prepare_export_documents(
                names[1:],
                [*prepared, ready],
                on_ready,
            ),
        )
```

全部成功後才呼叫 `batch_export_documents_to_folder(..., overwrite=True)`。任何一份 conversion failure 都停止整批，不寫空 braille，也不顯示舊的 “exported with empty braille” issues dialog。

- [ ] **Step 7: 更新翻譯 catalog**

將新字串加入 POT 與 PO：

```po
msgid "Automatic conversion failed while exporting: {error}"
msgstr "匯出時自動轉譯失敗：{error}"
```

移除不再使用的：

```po
"Automatic conversion failed while exporting. The document was exported with empty braille output.\n\n{error}"
"Some documents were exported with empty braille output because automatic conversion failed."
```

在 Windows 執行：

Run: `cd client && msgfmt locales/zh_TW/LC_MESSAGES/dotexpress.po -o locales/zh_TW/LC_MESSAGES/dotexpress.mo`

Expected: exit 0.

若目前環境沒有 `msgfmt`，記錄未執行原因，保留 `.po`/`.pot` source changes，並在 Windows verification task 執行 `scripts\generate_pot.bat` 後重新編譯 `.mo`。

- [ ] **Step 8: 執行 workspace 與 flow tests**

Run: `cd client && python3 -m unittest tests.test_document_workspace tests.test_conversion_jobs tests.test_document_flow -v`

Expected: all tests PASS.

- [ ] **Step 9: 提交 export waiting behavior**

```bash
git add client/gui.py client/documents/workspace.py client/tests/test_document_workspace.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "fix: require completed braille for document exports"
```

### Task 8: 將視窗標題綁定 open document

**Files:**
- Modify: `client/documents/session.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_document_session.py`

- [ ] **Step 1: 寫 title formatting 的失敗測試**

在 `client/tests/test_document_session.py` import `format_window_title` 並加入：

```python
    def test_window_title_uses_open_document_name(self) -> None:
        self.assertEqual(format_window_title("lesson"), "lesson - DotExpress")

    def test_window_title_falls_back_to_application_name(self) -> None:
        self.assertEqual(format_window_title(None), "DotExpress")
```

- [ ] **Step 2: 執行測試並確認 helper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_document_session.DocumentSessionTest.test_window_title_uses_open_document_name tests.test_document_session.DocumentSessionTest.test_window_title_falls_back_to_application_name -v`

Expected: FAIL with `ImportError: cannot import name 'format_window_title'`.

- [ ] **Step 3: 實作 title formatter**

在 `client/documents/session.py` 加入：

```python
def format_window_title(open_name: str | None) -> str:
    return f"{open_name} - DotExpress" if open_name else "DotExpress"
```

- [ ] **Step 4: 集中 GUI title update**

在 `client/gui.py` import `format_window_title`，新增：

```python
    def _update_window_title(self) -> None:
        self.SetTitle(format_window_title(self._open_document_name))
```

呼叫點：

- `_initialize_frame()` 仍先設定 `DotExpress`，因為 state 尚未建立。
- `_open_document_by_name()` 在設定/清空 `_open_document_name` 後立即呼叫。
- rename open document 更新 `_open_document_name` 後呼叫。
- delete open document 清空名稱後呼叫；自動 open 下一份/default 文件時 `_open_document_by_name()` 再更新。
- `_clear_document_editors()` 不自行改 title，避免左側 selection 或暫時清空 editor 影響 open-document semantics。

- [ ] **Step 5: 執行 title/session tests**

Run: `cd client && python3 -m unittest tests.test_document_session -v`

Expected: all tests PASS.

- [ ] **Step 6: 提交 window title**

```bash
git add client/gui.py client/documents/session.py client/tests/test_document_session.py
git commit -m "feat: show open document in window title"
```

### Task 9: 回歸驗證與文件化

**Files:**
- Modify only if verification exposes a defect in files already listed above.

- [ ] **Step 1: 執行所有不依賴 Windows liblouis runtime 的 client tests**

Run: `cd client && python3 -m unittest discover -s tests -p "test_*.py" -v`

Expected: all runnable tests PASS；Windows-only tests may report SKIP for unavailable `WINFUNCTYPE`/liblouis runtime。

- [ ] **Step 2: 執行 compile check**

Run: `python3 -m compileall -q client`

Expected: exit 0.

- [ ] **Step 3: 在 Windows 做 wx smoke test**

Run: `cd client && python gui.py`

逐項確認：

1. 啟動後 title 為目前文件名加 ` - DotExpress`。
2. 只在左側選取另一份文件不改 title；開啟後才改。
3. 大型 pending 文件切換、新增、匯入、rename 時操作立即完成，背景轉譯後 `.dep` 與目前 open document output 正確更新。
4. 刪除 pending 文件不觸發轉譯，late completion 不重建已刪除 `.dep`。
5. rename running 文件後 completion 寫到新名稱 `.dep`，不重建舊名稱。
6. close 不等待 background/foreground conversion。
7. pending 文件匯出單份、匯出全部與 Ctrl+S 均顯示 converting dialog，成功後才寫檔。
8. export conversion failure 不產生空 `.brl`/completed `.dep`。
9. background queued/running 文件按手動轉譯後，只顯示並保存 manual 最新結果。

Expected: all nine behaviors match the approved spec.

- [ ] **Step 4: 檢查 commit scope**

Run: `git status --short`

Expected: plan implementation files clean；任何原先存在的 unrelated changes 保持 untouched。

Run: `git log --oneline --max-count=9`

Expected: 本 plan 產生 scoped commits，至少包含：

```text
feat: show open document in window title
fix: require completed braille for document exports
feat: prioritize manual document conversion
feat: cancel background jobs on document removal
feat: save pending documents before background conversion
feat: add background conversion queue
feat: track document conversion versions
refactor: separate pending document saves
```

- [ ] **Step 5: 若 smoke test 需要修正，提交單一 verification fix**

只在實際發現問題時執行：

```bash
git add client/gui.py client/conversion/jobs.py client/documents/session.py client/documents/workspace.py client/tests/test_conversion_jobs.py client/tests/test_document_flow.py client/tests/test_document_session.py client/tests/test_document_workspace.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "fix: correct background conversion lifecycle"
```

不得把原先 unrelated worktree changes 納入 commit。
