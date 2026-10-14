r"""Item 127 (F-13 D3): a logoff during a conversion, many times.

Usage: python safe_run.py item127.py <exe> <work folder> [runs]
Each run (default 20) starts from a fresh work folder (F-9 item 93's workspace: alpha holds
the long pending text, about 15 s of conversion, and is open; beta is short). After the
start a stale dual_view\dual-view-f13probe.html is written: OnExit's cleanup removes it, so
its absence after the exit shows that OnExit ran. Ctrl+Enter on alpha; after 1 s
WM_QUERYENDSESSION (lParam ENDSESSION_LOGOFF) to the main window, then WM_ENDSESSION
(wParam 1): the answers, the exit code (read through a process handle opened after the
start), the probe file, the packages and gui.log. Windows itself is never asked to end the
session. Before F-13 (N-f12b): the exit code is sometimes -1073740940 (0xC0000374).
A run counts only if the conversion runs when the messages are sent (the source editor is
disabled, as during every conversion): in a few draft runs Ctrl+Enter did not reach the
app as Ctrl+Enter (a character was typed instead, and the query answered 1). Such a run
is recorded as "not converting" and another one is made, at most RUNS + 10 in all.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
from f13gui import A, F9, G, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 20
codes = []
run = 0
while len(codes) < RUNS and run < RUNS + 10:
	run += 1
	d = A.prepare(EXE, d)
	F9.pending(d, "alpha", F9.long_text())
	A.package(d, "beta", "beta body", "⠃")
	app, w, shown = H.start(d)
	if app is None:
		print(f"127 run {run:2d}: start failed {H.masked(d, shown)}")
		dx.kill_under(d)
		codes.append("no start")
		continue
	handle = F9.process_handle(app.process)
	probe = A.write(os.path.join(d, "dual_view", "dual-view-f13probe.html"), b"<html>stale</html>")
	# After a crash of the previous run, Windows can keep the foreground for a moment, and
	# SetForegroundWindow fails: try again (a tool problem, not the app's).
	for attempt in range(5):
		try:
			F9.convert(w)
			break
		except Exception as error:  # pywintypes.error from SetForegroundWindow, or safe_run's RuntimeError
			print(f"127 run {run:2d}: Ctrl+Enter not sent ({type(error).__name__}); trying again")
			time.sleep(3)
	time.sleep(1)
	converting = F9.box_open(app)
	busy = not w.children(class_name="Edit")[0].is_enabled()
	if not busy:
		print(f"127 run {run:2d}: not converting (Ctrl+Enter did not start a conversion); ended, not counted")
		dx.kill_under(d)
		continue
	query = G.SessionMessage(w.handle, G.WM_QUERYENDSESSION)
	query.start()
	query.join(12)
	end = G.SessionMessage(w.handle, G.WM_ENDSESSION, wparam=1)
	end.start()
	end.join(12)
	code = H.exit_code(handle, 10)
	codes.append(code)
	print(
		f"127 run {run:2d}: shown {H.placements(shown)} box before {converting} "
		f"query {F9.call_state(query)} end {F9.call_state(end)} exit code {code} "
		f"probe left {os.path.exists(probe)}"
	)
	print(f"127 run {run:2d}: alpha {F9.package(d, 'alpha')} | beta {F9.package(d, 'beta')} files {A.files(d)} gui.log {G.gui_log(d)}")
	if code is None:
		print(f"127 run {run:2d}: still running after 10 s; ended")
		dx.kill_under(d)
print(f"127 exit codes: {codes} (runs made: {run})")
print(f"127 summary: runs {len(codes)} code 0 {codes.count(0)} code -1073740940 {codes.count(-1073740940)} other {[c for c in codes if c not in (0, -1073740940)]}")
