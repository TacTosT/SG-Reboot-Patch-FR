# -*- coding: utf-8 -*-
"""Capture OutputDebugString output (DebugView-style) to a log file."""
import ctypes, ctypes.wintypes as w, sys, time, os

OUT = sys.argv[1] if len(sys.argv) > 1 else "dbwin.log"
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

INVALID = w.HANDLE(-1)
PAGE_READWRITE, FILE_MAP_READ = 0x04, 0x0004
SYNCHRONIZE, EVENT_MODIFY_STATE = 0x00100000, 0x0002

k32.CreateEventW.restype = w.HANDLE
k32.CreateFileMappingW.restype = w.HANDLE
k32.CreateFileMappingW.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR]
k32.MapViewOfFile.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t]
k32.MapViewOfFile.restype = ctypes.c_void_p

ready = k32.CreateEventW(None, False, False, "DBWIN_BUFFER_READY")
data  = k32.CreateEventW(None, False, False, "DBWIN_DATA_READY")
if not ready or not data:
    sys.exit("cannot create DBWIN events (another DebugView running?) err=%d" % ctypes.get_last_error())
hmap = k32.CreateFileMappingW(INVALID, None, PAGE_READWRITE, 0, 4096, "DBWIN_BUFFER")
if not hmap:
    sys.exit("cannot create DBWIN_BUFFER err=%d" % ctypes.get_last_error())
buf = k32.MapViewOfFile(hmap, FILE_MAP_READ, 0, 0, 4096)
if not buf:
    sys.exit("cannot map DBWIN_BUFFER err=%d" % ctypes.get_last_error())

f = open(OUT, "w", encoding="utf-8", errors="replace")
f.write("--- capture started %s ---\n" % time.strftime("%H:%M:%S")); f.flush()
k32.SetEvent(ready)
try:
    while True:
        if k32.WaitForSingleObject(data, 1000) == 0:      # WAIT_OBJECT_0
            pid = ctypes.c_ulong.from_address(buf).value
            raw = ctypes.string_at(buf + 4, 4092)
            msg = raw.split(b"\0", 1)[0].decode("utf-8", "replace")
            if not msg:
                msg = raw.split(b"\0", 1)[0].decode("cp932", "replace")
            f.write("%s [%d] %s" % (time.strftime("%H:%M:%S"), pid, msg))
            if not msg.endswith("\n"):
                f.write("\n")
            f.flush()
            k32.SetEvent(ready)
finally:
    f.close()
