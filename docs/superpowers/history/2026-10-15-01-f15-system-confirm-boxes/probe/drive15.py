import os, sys
# The committed F-13 probe this one wraps, relative to this folder.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-10-14-02-f13-behavior-nvda", "probe"))
import drive_probe as d

d.PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "box15.py")
d.CAPTIONS = {"discard_nokey": "尚未儲存的變更"}
keys = {"esc": "{ESC}", "enter": "{ENTER}", "alt-f4": "%{F4}"}
for n in range(10):
	keys[f"alt-num{n}"] = "%{VK_NUMPAD" + str(n) + "}"
for name in ("MULTIPLY", "ADD", "SEPARATOR", "SUBTRACT", "DECIMAL", "DIVIDE"):
	keys[f"alt-{name.lower()}"] = "%{VK_" + name + "}"
for n in range(1, 13):
	keys[f"alt-f{n}"] = "%{F" + str(n) + "}"
for c in "sdby":
	keys[f"alt-{c}"] = "%" + c
d.KEYS = keys
d.ACTIONS = tuple(keys) + ("close",)
if __name__ == "__main__":
	d.main()
