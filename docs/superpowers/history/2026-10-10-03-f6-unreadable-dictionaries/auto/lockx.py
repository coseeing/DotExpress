"""Hold a file open for reading without sharing: CreateFileW(GENERIC_READ, share 0).

Usage: python lockx.py <path> <seconds>
Prints "locked" once the handle is open. lock.py of 2026-10-09-03 knows only the share
modes r and rw; a file held like this cannot be opened by anyone else, for any access.
"""
import ctypes
import sys
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateFileW.argtypes = (
	wintypes.LPCWSTR,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.LPVOID,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.HANDLE,
)
kernel32.CreateFileW.restype = wintypes.HANDLE
handle = kernel32.CreateFileW(sys.argv[1], 0x80000000, 0, None, 3, 0x80, None)
if handle is None or handle == wintypes.HANDLE(-1).value:
	print("open failed", ctypes.get_last_error(), flush=True)
	sys.exit(1)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
