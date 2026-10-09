# Hold a file open for reading with share mode r (FILE_SHARE_READ) or rw (READ|WRITE).
import ctypes, sys, time
from ctypes import wintypes
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = wintypes.HANDLE
share = {"r": 1, "rw": 3}[sys.argv[3] if len(sys.argv) > 3 else "r"]
h = k.CreateFileW(sys.argv[1], 0x80000000, share, None, 3, 0x80, None)
if h == wintypes.HANDLE(-1).value:
	print("open failed", ctypes.get_last_error(), flush=True); sys.exit(1)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
