import main
import ctypes
from ctypes import wintypes
import time

# standard definitions
WM_DROPFILES = 0x0233
GMEM_ZEROINIT = 0x0040

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL)
    ]

GlobalAlloc = ctypes.windll.kernel32.GlobalAlloc
GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
GlobalAlloc.restype = wintypes.HGLOBAL

GlobalLock = ctypes.windll.kernel32.GlobalLock
GlobalLock.argtypes = [wintypes.HGLOBAL]
GlobalLock.restype = ctypes.c_void_p

GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
GlobalUnlock.argtypes = [wintypes.HGLOBAL]
GlobalUnlock.restype = wintypes.BOOL

PostMessage = ctypes.windll.user32.PostMessageW
PostMessage.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
PostMessage.restype = wintypes.BOOL

def simulate_drop_on_app(app):
    hwnd = app.winfo_id()
    print(f"Simulating drop on HWND: {hwnd}")
    
    filepaths = "C:\\Windows\\notepad.exe\0"
    filepaths_bytes = filepaths.encode('utf-16le')
    
    struct_size = ctypes.sizeof(DROPFILES)
    total_size = struct_size + len(filepaths_bytes) + 2
    
    hglobal = GlobalAlloc(GMEM_ZEROINIT, total_size)
    ptr = GlobalLock(hglobal)
    
    df = DROPFILES()
    df.pFiles = struct_size
    df.pt = POINT(100, 100)
    df.fNC = False
    df.fWide = True
    
    ctypes.memmove(ptr, ctypes.byref(df), struct_size)
    ctypes.memmove(ptr + struct_size, filepaths_bytes, len(filepaths_bytes))
    
    GlobalUnlock(hglobal)
    
    res = PostMessage(hwnd, WM_DROPFILES, hglobal, 0)
    print(f"PostMessage result: {res}")

if __name__ == "__main__":
    print("Starting ClickPulseApp...")
    app = main.ClickPulseApp()
    
    # Schedule the simulated drop in 1.5 seconds
    app.after(1500, lambda: simulate_drop_on_app(app))
    
    # Auto-destroy after 4 seconds
    app.after(4000, app.destroy)
    
    app.mainloop()
    print("App exited normally.")
