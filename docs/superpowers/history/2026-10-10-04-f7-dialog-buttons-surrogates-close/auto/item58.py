"""Items 58-60 (F-7, M-5): Windows ends the session while DotExpress is open.

Usage: python item58.py <exe> <work folder> <query|idle|end>
alpha and beta are created, the app is restarted, alpha is open. Each message goes to the
main window of this DotExpress process only, from a driver thread; Windows itself is
never asked to log off or shut down.
query (58, spec D9): type an edit; lock.py holds alpha.dep (share read); post WM_CLOSE;
    the close dialog opens. Send WM_QUERYENDSESSION (lParam ENDSESSION_LOGOFF, timeout
    10 s) and watch the close dialogs for 3 s. Then press Esc in each open close dialog,
    newest first. The app keeps running with the edit; unlock, Close, Enter (Retry): the
    app exits, and after a restart alpha holds the edit.
idle (59): no edit, no dialog; send WM_QUERYENDSESSION: the app closes by itself.
end (60): as query up to the dialog; send WM_ENDSESSION (wParam 1): wx exits at once.
Before F-7 (N-f6b), query shows two close dialogs (the nested close of M-5) and the call
returns only after the inner one is answered.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, F, dx  # noqa: E402

EXE, d, mode = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
app, w = F.setup_alpha_beta(EXE, d)
alpha = os.path.join(F.workspace(d), "alpha.dep")
before = F.package(alpha)
pid = app.process
holder = None
if mode in ("query", "end"):
	D.set_input(w, "alpha edited")
	holder = F.lock(alpha, "r")
	import win32con

	w.post_message(win32con.WM_CLOSE)
	dialog = F.close_dialog(w)
	print("close dialog:", F.describe(dialog) if dialog is not None else None)
if mode == "end":
	sender = G.SessionMessage(w.handle, G.WM_ENDSESSION, wparam=1)
else:
	sender = G.SessionMessage(w.handle, G.WM_QUERYENDSESSION)
sender.start()
if mode == "query":
	print("close dialogs within 3 s:", G.watch_close_dialogs(app), "call:", sender.state())
	print("esc in each close dialog:", G.answer_close_dialogs(app, sender=sender))
	sender.join(12)
	print("call:", sender.state())
	time.sleep(1)
	print("running:", app.is_process_running(), "close dialogs:", G.count_titled(app, G.CLOSE_DIALOG))
	print("input:", repr(D.get_input(w)), "title:", w.window_text())
	dialogs, outcome = F.close_and_answer(app, w, ["enter"], between={0: lambda: F.unlock(holder)})
	print("unlock, close, enter:", outcome, [dialog["title"] for dialog in dialogs])
else:
	sender.join(12)
	print("call:", sender.state())
	print("exit code:", G.exit_code(pid, 5))
	if holder is not None:
		F.unlock(holder)
print(
	"alpha members changed:", F.package(alpha)[0] != before[0],
	"text:", repr(F.member(alpha, "alpha.txt").decode("utf-8")),
	"files:", F.files(d), "tmp:", F.leftovers(d),
)
print("gui.log:", G.gui_log(d))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)))
print("close:", F.close_and_answer(app, w, []))
dx.kill_under(d)
