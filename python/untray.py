# =====================================================================
#  untray.py  --  UnclonedTray-Py  v0.1.1
#  v0.1.1: custom tray icon (untray.ico via LoadImageW, system fallback)
#
#  Python port of UnclonedTray for machines where AutoHotkey is not
#  available (e.g. the interpreter got quarantined by a corporate EDR).
#
#  Design constraints, in order:
#    - pure standard library + ctypes: no pip installs, no compiled
#      binaries, nothing for an EDR to flag except python.exe itself;
#    - NO keyboard hook: lock-key enforcement listens to Raw Input
#      (WM_INPUT) notifications and re-asserts the toggle state right
#      after the key is touched. Registration-based, not interception;
#    - KeepAwake uses SetThreadExecutionState: no synthetic input;
#    - DownloadsSorter moves via MoveFileExW WITHOUT
#      MOVEFILE_REPLACE_EXISTING: the OS itself refuses to overwrite,
#      existence test and move are the same syscall (no TOCTOU window);
#    - shares UnclonedTray.ini with the AutoHotkey host (same sections,
#      same keys), so a machine can switch implementations freely.
#
#  Run with pythonw.exe for a windowless tray process.
#  Part of the Uncloned Math toolset -- https://uncloned.work
# =====================================================================

import ctypes
import os
import sys
import time
import winreg
import configparser
from ctypes import wintypes

APP_NAME = "UnclonedTray-Py"
VERSION  = "0.1.1"

user32   = ctypes.WinDLL("user32",   use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32  = ctypes.WinDLL("shell32",  use_last_error=True)

# ----------------------------- win32 ---------------------------------

WM_DESTROY   = 0x0002
WM_COMMAND   = 0x0111
WM_TIMER     = 0x0113
WM_INPUT     = 0x00FF
WM_APP       = 0x8000
WM_TRAY      = WM_APP + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10
NIIF_INFO = 0x1

MF_STRING, MF_CHECKED, MF_POPUP, MF_SEPARATOR = 0x0, 0x8, 0x10, 0x800
TPM_RETURNCMD, TPM_RIGHTBUTTON = 0x100, 0x2
IDI_APPLICATION = 32512
IMAGE_ICON      = 1
LR_LOADFROMFILE = 0x10
LR_DEFAULTSIZE  = 0x40

VK = {"Num": 0x90, "Caps": 0x14, "Scroll": 0x91}
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x1, 0x2

RIDEV_INPUTSINK   = 0x100
RID_INPUT         = 0x10000003
RIM_TYPEKEYBOARD  = 1

ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

TIMER_SORT, TIMER_ENFORCE = 1, 2
SORT_INTERVAL_MS = 30000
ENFORCE_DELAY_MS = 30

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", ctypes.c_wchar * 256), ("uVersion", wintypes.UINT),
                ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wintypes.DWORD)]

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT),
                ("Reserved", wintypes.USHORT), ("VKey", wintypes.USHORT),
                ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]

class RAWINPUT(ctypes.Structure):
    # keyboard-only: we register usage page 1 / usage 6 exclusively,
    # so the data member is always RAWKEYBOARD.
    _fields_ = [("header", RAWINPUTHEADER), ("keyboard", RAWKEYBOARD)]

# Explicit prototypes: on 64-bit Python default int coercion truncates
# handles, so every handle-bearing call gets argtypes/restype up front.
user32.CreateWindowExW.restype  = wintypes.HWND
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, ctypes.c_void_p, wintypes.HINSTANCE, ctypes.c_void_p]
user32.DefWindowProcW.restype   = ctypes.c_longlong
user32.DefWindowProcW.argtypes  = [wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
user32.RegisterClassW.argtypes  = [ctypes.POINTER(WNDCLASSW)]
user32.LoadIconW.restype        = wintypes.HICON
user32.LoadIconW.argtypes       = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadImageW.restype       = wintypes.HANDLE
user32.LoadImageW.argtypes      = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.CreatePopupMenu.restype  = ctypes.c_size_t
user32.AppendMenuW.argtypes     = [ctypes.c_size_t, wintypes.UINT,
                                   ctypes.c_size_t, wintypes.LPCWSTR]
user32.DestroyMenu.argtypes     = [ctypes.c_size_t]
user32.TrackPopupMenu.restype   = ctypes.c_int
user32.TrackPopupMenu.argtypes  = [ctypes.c_size_t, wintypes.UINT, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
user32.SetTimer.restype         = ctypes.c_size_t
user32.SetTimer.argtypes        = [wintypes.HWND, ctypes.c_size_t,
                                   wintypes.UINT, ctypes.c_void_p]
user32.KillTimer.argtypes       = [wintypes.HWND, ctypes.c_size_t]
user32.GetKeyState.restype      = ctypes.c_short
user32.GetRawInputData.restype  = wintypes.UINT
user32.GetRawInputData.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT), wintypes.UINT]
kernel32.GetModuleHandleW.restype   = wintypes.HMODULE
kernel32.MoveFileExW.argtypes       = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
kernel32.GetFileAttributesW.restype = wintypes.DWORD
kernel32.CreateMutexW.restype       = wintypes.HANDLE
shell32.Shell_NotifyIconW.argtypes  = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]


# ----------------------------- config --------------------------------

class Config:
    """Same file, same sections, same keys as the AutoHotkey host.
    AHK's IniWrite produces UTF-16 LE with BOM; we detect the BOM and
    keep whatever encoding the file already has."""

    def __init__(self, path):
        self.path = path
        self.encoding = "utf-8"
        self.cp = configparser.ConfigParser(interpolation=None)
        if os.path.exists(path):
            with open(path, "rb") as f:
                if f.read(2) in (b"\xff\xfe", b"\xfe\xff"):
                    self.encoding = "utf-16"
            try:
                self.cp.read(path, encoding=self.encoding)
            except (configparser.Error, UnicodeError):
                pass                       # unreadable INI == empty INI

    def get_bool(self, section, key, default):
        try:
            return self.cp.getboolean(section, key)
        except (configparser.Error, ValueError):
            return default

    def get_str(self, section, key, default):
        return self.cp.get(section, key, fallback=default)

    def set_val(self, section, key, value):
        if not self.cp.has_section(section):
            self.cp.add_section(section)
        if isinstance(value, bool):
            value = "1" if value else "0"
        self.cp.set(section, key, str(value))
        try:
            with open(self.path, "w", encoding=self.encoding) as f:
                self.cp.write(f)
        except OSError:
            pass                           # read-only location: run un-persisted


# ----------------------------- plugins -------------------------------

class Plugin:
    Name, Version = "?", "?"

    def __init__(self, host):
        self.host = host
        self.cfg = host.cfg
        self.enabled = True

    def init(self): pass
    def shutdown(self): pass
    def build_menu(self, menu): pass
    def status(self): return ""

    def notify(self, text):
        self.host.balloon(self.Name, text)


class NumLockPlugin(Plugin):
    Name, Version = "NumLock", "0.2.0"

    MODES    = ["Always On", "Always Off", "On", "Off", "Normal"]
    KEYS     = ["Num", "Caps", "Scroll"]
    LABEL    = {"Num": "Num Lock", "Caps": "Caps Lock", "Scroll": "Scroll Lock"}
    DEFAULTS = {"Num": "Always On", "Caps": "Always Off", "Scroll": "Normal"}

    def init(self):
        self.current = {}
        for key in self.KEYS:
            mode = self.cfg.get_str(self.Name, key, self.DEFAULTS[key])
            if mode not in self.MODES:          # guard against hand-edited INI
                mode = self.DEFAULTS[key]
            self.current[key] = mode
            self.apply(key)

    def is_on(self, key):
        return bool(user32.GetKeyState(VK[key]) & 1)

    def set_toggle(self, key, want_on):
        if self.is_on(key) != want_on:
            vk = VK[key]
            user32.keybd_event(vk, 0x45, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk, 0x45, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

    def apply(self, key):
        mode = self.current[key]
        if mode in ("Always On", "On"):
            self.set_toggle(key, True)
        elif mode in ("Always Off", "Off"):
            self.set_toggle(key, False)
        # "Normal": leave the current state alone

    def enforce(self):
        # Runs ENFORCE_DELAY_MS after a lock key was physically touched.
        # By then the OS has committed the toggle; we simply put it back.
        # The window in which the wrong state exists is a few tens of ms --
        # too short for a typed keystroke to land inside it in practice.
        for key in self.KEYS:
            mode = self.current[key]
            if mode == "Always On":
                self.set_toggle(key, True)
            elif mode == "Always Off":
                self.set_toggle(key, False)

    def on_lock_key(self, vkey):
        user32.SetTimer(self.host.hwnd, TIMER_ENFORCE, ENFORCE_DELAY_MS, None)

    def select_mode(self, key, mode):
        self.current[key] = mode
        self.apply(key)
        self.cfg.set_val(self.Name, key, mode)

    def build_menu(self, menu):
        for key in self.KEYS:
            sub = self.host.new_menu()
            for mode in self.MODES:
                self.host.add_item(sub, mode,
                    lambda k=key, md=mode: self.select_mode(k, md),
                    checked=(self.current.get(key) == mode))
            self.host.add_submenu(menu, self.LABEL[key], sub)

    def status(self):
        parts = [f"{k}: {self.current[k]}" for k in self.KEYS
                 if self.current.get(k, "Normal") != "Normal"]
        return ", ".join(parts) if parts else "all normal"


class KeepAwakePlugin(Plugin):
    Name, Version = "KeepAwake", "0.2.0"

    def init(self):
        # Off by default -- deliberate opt-in (persisted across runs).
        self.awake        = self.cfg.get_bool(self.Name, "Awake", False)
        self.keep_display = self.cfg.get_bool(self.Name, "KeepDisplay", True)
        self.apply()

    def apply(self):
        flags = ES_CONTINUOUS
        if self.awake:
            flags |= ES_SYSTEM_REQUIRED
            if self.keep_display:
                flags |= ES_DISPLAY_REQUIRED
        kernel32.SetThreadExecutionState(flags)

    def toggle_awake(self):
        self.awake = not self.awake
        self.cfg.set_val(self.Name, "Awake", self.awake)
        self.apply()
        self.notify("Keep awake: " + ("ON" if self.awake else "OFF"))

    def toggle_display(self):
        self.keep_display = not self.keep_display
        self.cfg.set_val(self.Name, "KeepDisplay", self.keep_display)
        self.apply()                    # re-apply immediately if hold is active

    def build_menu(self, menu):
        self.host.add_item(menu, "Keep awake", self.toggle_awake, self.awake)
        self.host.add_item(menu, "Keep display on", self.toggle_display,
                           self.keep_display)

    def shutdown(self):
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)   # release the hold

    def status(self):
        if not self.awake:
            return "off"
        return "system + display" if self.keep_display else "system only"


class DownloadsSorterPlugin(Plugin):
    Name, Version = "DownloadsSorter", "0.2.0"

    FRESH_SECONDS = 15         # do not touch files younger than N seconds
    OTHER_FOLDER  = "Other"
    MAX_COLLISION = 999        # give up rather than spin forever

    CATEGORIES = {
        "Images":        ["jpg","jpeg","png","gif","bmp","webp","svg","tif","tiff","ico","heic"],
        "Documents":     ["pdf","doc","docx","txt","rtf","odt","md","tex"],
        "Spreadsheets":  ["xls","xlsx","csv","ods"],
        "Presentations": ["ppt","pptx","odp"],
        "Archives":      ["zip","rar","7z","tar","gz","xz","iso"],
        "Video":         ["mp4","mkv","avi","mov","webm","wmv","m4v"],
        "Audio":         ["mp3","wav","flac","aac","ogg","m4a"],
        "Installers":    ["exe","msi","msix"],
        "Code":          ["py","js","ts","java","c","cpp","h","cs","ahk",
                          "json","xml","html","css","sh","bat","ps1","jar"],
    }
    SKIP_EXT = {"crdownload", "part", "tmp", "download"}   # incomplete downloads

    def init(self):
        self.ext_cat = {}
        for cat, exts in self.CATEGORIES.items():
            for e in exts:
                self.ext_cat[e] = cat
        self.auto = self.cfg.get_bool(self.Name, "Auto", True)
        if self.auto:
            user32.SetTimer(self.host.hwnd, TIMER_SORT, SORT_INTERVAL_MS, None)

    def toggle_auto(self):
        self.auto = not self.auto
        self.cfg.set_val(self.Name, "Auto", self.auto)
        if self.auto:
            user32.SetTimer(self.host.hwnd, TIMER_SORT, SORT_INTERVAL_MS, None)
        else:
            user32.KillTimer(self.host.hwnd, TIMER_SORT)
        self.notify("Auto-watch: " + ("ON" if self.auto else "OFF"))

    def downloads_path(self):
        # Registry-first (OneDrive-aware), env fallback -- mirrors the AHK host.
        guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        base = r"Software\Microsoft\Windows\CurrentVersion\Explorer"
        for hive in ("User Shell Folders", "Shell Folders"):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + hive) as k:
                    raw, _ = winreg.QueryValueEx(k, guid)
                path = os.path.expandvars(raw)
                if os.path.isdir(path):
                    return path
            except OSError:
                pass
        return os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")

    def run_sort(self, manual):
        n = self.sort_once()
        if manual or n > 0:
            self.notify(f"Files moved: {n}")

    def sort_once(self):
        """Sorts loose files in the Downloads ROOT once. Subfolders are
        never touched; nothing is ever deleted. Returns files moved."""
        dl = self.downloads_path()
        if not os.path.isdir(dl):
            return 0
        try:      # collect first, then move (do not mutate during enumeration)
            entries = [e for e in os.scandir(dl) if e.is_file()]
        except OSError:
            return 0
        moved, now = 0, time.time()
        for e in entries:
            attrs = kernel32.GetFileAttributesW(e.path)
            if attrs != 0xFFFFFFFF and (attrs & 0x6):     # hidden(2) / system(4)
                continue
            ext = os.path.splitext(e.name)[1].lstrip(".").lower()
            if ext in self.SKIP_EXT:
                continue
            try:
                if now - e.stat().st_mtime < self.FRESH_SECONDS:
                    continue                              # still being written
            except OSError:
                continue
            cat = self.ext_cat.get(ext, self.OTHER_FOLDER)
            if self.move_atomic(e.path, os.path.join(dl, cat), e.name):
                moved += 1
        return moved

    def move_atomic(self, src, target_dir, name):
        """MoveFileExW WITHOUT MOVEFILE_REPLACE_EXISTING: if the destination
        exists the OS refuses the call and nothing is touched. The existence
        test and the move are the same syscall -- no check-then-act window
        for anyone to race. Same primitive as the AHK module."""
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            return False
        base, ext = os.path.splitext(name)
        n = 1
        while n <= self.MAX_COLLISION:
            dest = os.path.join(target_dir,
                                name if n == 1 else f"{base} ({n}){ext}")
            if kernel32.MoveFileExW(src, dest, 0):
                return True
            err = ctypes.get_last_error()
            if err not in (80, 183):    # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
                return False            # locked/busy/permission: next scan's problem
            n += 1
        return False                    # absurd collision count -- give up safely

    def build_menu(self, menu):
        self.host.add_item(menu, "Sort now", lambda: self.run_sort(True))
        self.host.add_item(menu, "Auto-watch", self.toggle_auto, self.auto)
        self.host.add_sep(menu)
        self.host.add_item(menu, "Show folder",
                           lambda: os.startfile(self.downloads_path()))

    def shutdown(self):
        user32.KillTimer(self.host.hwnd, TIMER_SORT)

    def status(self):
        return "auto" if self.auto else "manual"


# ----------------------------- autostart -----------------------------

class Autostart:
    KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
    NAME = "UnclonedTray-Py"

    @staticmethod
    def command():
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable
        return f'"{pyw}" "{os.path.abspath(__file__)}"'

    @staticmethod
    def is_enabled():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Autostart.KEY) as k:
                winreg.QueryValueEx(k, Autostart.NAME)
            return True
        except OSError:
            return False

    @staticmethod
    def toggle():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Autostart.KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if Autostart.is_enabled():
                winreg.DeleteValue(k, Autostart.NAME)
                return False
            winreg.SetValueEx(k, Autostart.NAME, 0, winreg.REG_SZ,
                              Autostart.command())
            return True


# ----------------------------- host ----------------------------------

class TrayHost:
    MODULES = None    # filled after class definitions

    def __init__(self):
        self.cfg = Config(self.find_ini())
        self.plugins = []
        self.actions = {}          # menu command id -> callable
        self.next_id = 1000
        self.hwnd = None
        self.nid = None
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")

    @staticmethod
    def find_ini():
        here = os.path.dirname(os.path.abspath(__file__))
        for cand in (os.path.join(here, "UnclonedTray.ini"),
                     os.path.join(os.path.dirname(here), "UnclonedTray.ini")):
            if os.path.exists(cand):
                return cand
        return os.path.join(here, "UnclonedTray.ini")

    def by_name(self, name):
        for p in self.plugins:
            if p.Name == name:
                return p
        return None

    # ------------------------- window --------------------------------

    def create_window(self):
        self.wndproc = WNDPROC(self._wndproc)      # keep a ref: no GC
        wc = WNDCLASSW()
        wc.lpfnWndProc   = self.wndproc
        wc.lpszClassName = APP_NAME + "_Host"
        wc.hInstance     = kernel32.GetModuleHandleW(None)
        if not user32.RegisterClassW(ctypes.byref(wc)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.hwnd = user32.CreateWindowExW(0, wc.lpszClassName, APP_NAME,
                                           0, 0, 0, 0, 0, None, None,
                                           wc.hInstance, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAY:
                if lparam in (WM_RBUTTONUP, WM_LBUTTONUP):
                    self.show_menu()
                return 0
            if msg == WM_TIMER:
                if wparam == TIMER_SORT:
                    p = self.by_name("DownloadsSorter")
                    if p and p.enabled:
                        p.run_sort(False)
                elif wparam == TIMER_ENFORCE:
                    user32.KillTimer(hwnd, TIMER_ENFORCE)
                    p = self.by_name("NumLock")
                    if p and p.enabled:
                        p.enforce()
                return 0
            if msg == WM_INPUT:
                self.handle_raw_input(lparam)
                return 0
            if msg == self.taskbar_created:
                # Explorer restarted: the tray area is new, re-add the icon.
                self.add_tray_icon()
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass          # a wndproc must never propagate into foreign frames
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # ------------------------- raw input ------------------------------

    def register_raw_input(self):
        rid = RAWINPUTDEVICE(1, 6, RIDEV_INPUTSINK, self.hwnd)   # generic kbd
        user32.RegisterRawInputDevices(ctypes.byref(rid), 1,
                                       ctypes.sizeof(RAWINPUTDEVICE))

    def handle_raw_input(self, lparam):
        size = wintypes.UINT(0)
        user32.GetRawInputData(ctypes.c_void_p(lparam), RID_INPUT, None,
                               ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
        if size.value == 0:
            return
        buf = ctypes.create_string_buffer(size.value)
        got = user32.GetRawInputData(ctypes.c_void_p(lparam), RID_INPUT, buf,
                                     ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
        if got != size.value:
            return
        ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        if ri.header.dwType != RIM_TYPEKEYBOARD:
            return
        if ri.keyboard.VKey in (VK["Num"], VK["Caps"], VK["Scroll"]):
            p = self.by_name("NumLock")
            if p and p.enabled:
                p.on_lock_key(ri.keyboard.VKey)

    # ------------------------- tray icon ------------------------------

    def load_app_icon(self):
        # untray.ico next to the script (multi-size, generated once with
        # Pillow -- NOT a runtime dependency); system default as fallback.
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "untray.ico")
        if os.path.exists(ico):
            h = user32.LoadImageW(None, ico, IMAGE_ICON, 0, 0,
                                  LR_LOADFROMFILE | LR_DEFAULTSIZE)
            if h:
                return h
        return user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))

    def add_tray_icon(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.load_app_icon()
        nid.szTip = f"{APP_NAME} v{VERSION}"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self.nid = nid

    def balloon(self, title, text):
        if not self.nid:
            return
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_INFO
        self.nid.szInfoTitle = title[:63]
        self.nid.szInfo = text[:255]
        self.nid.dwInfoFlags = NIIF_INFO
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

    # ------------------------- menu -----------------------------------

    def new_menu(self):
        return user32.CreatePopupMenu()

    def _bind(self, fn):
        self.next_id += 1
        self.actions[self.next_id] = fn
        return self.next_id

    def add_item(self, menu, label, fn, checked=False):
        flags = MF_STRING | (MF_CHECKED if checked else 0)
        user32.AppendMenuW(menu, flags, self._bind(fn), label)

    def add_sep(self, menu):
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)

    def add_submenu(self, menu, label, sub):
        user32.AppendMenuW(menu, MF_POPUP, sub, label)

    def show_menu(self):
        # Rebuilt from scratch on every open: check marks always reflect
        # the current state and there is no stale-handle bookkeeping.
        self.actions = {}
        self.next_id = 1000
        root = self.new_menu()
        for p in self.plugins:
            sub = self.new_menu()
            if p.enabled:
                p.build_menu(sub)
                self.add_sep(sub)
            self.add_item(sub, "Enabled",
                          (lambda pp=p: self.toggle_module(pp)), p.enabled)
            self.add_submenu(root, p.Name, sub)
        self.add_sep(root)
        self.add_item(root, "Run at startup", self.toggle_autostart,
                      Autostart.is_enabled())
        self.add_sep(root)
        self.add_item(root, "About", self.show_about)
        self.add_item(root, "Exit", self.quit)

        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)   # menu must close on outside click
        cmd = user32.TrackPopupMenu(root, TPM_RETURNCMD | TPM_RIGHTBUTTON,
                                    pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, 0, 0, 0)  # MS-recommended WM_NULL nudge
        user32.DestroyMenu(root)
        fn = self.actions.get(cmd)
        if fn:
            try:
                fn()
            except Exception as e:
                self.msgbox(f"Action failed:\n{e}")

    # ------------------------- actions --------------------------------

    def toggle_module(self, p):
        if p.enabled:
            try:
                p.shutdown()
            except Exception:
                pass
            p.enabled = False
        else:
            p.enabled = True
            try:
                p.init()
            except Exception as e:
                p.enabled = False
                self.msgbox(f"Module '{p.Name}' failed to start:\n{e}")
                return
        self.cfg.set_val(p.Name, "Enabled", p.enabled)
        self.balloon(APP_NAME,
                     f"{p.Name}: {'enabled' if p.enabled else 'disabled'}")

    def toggle_autostart(self):
        on = Autostart.toggle()
        self.balloon(APP_NAME, "Run at startup: " + ("ON" if on else "OFF"))

    def show_about(self):
        lines = [f"{APP_NAME} v{VERSION}", "",
                 "Python port of UnclonedTray: pure stdlib + ctypes,",
                 "no keyboard hooks, no compiled binaries.", "", "Modules:"]
        for p in self.plugins:
            line = (f"  {p.Name}  v{p.Version}  -- "
                    f"{'enabled' if p.enabled else 'disabled'}")
            if p.enabled:
                st = p.status()
                if st:
                    line += f"  ({st})"
            lines.append(line)
        lines += ["", f"Config: {self.cfg.path}", "", "Python  |  uncloned.work"]
        self.msgbox("\n".join(lines))

    def msgbox(self, text):
        user32.MessageBoxW(None, text, APP_NAME, 0x40)   # MB_ICONINFORMATION

    # ------------------------- lifecycle ------------------------------

    def start(self):
        self.create_window()
        for cls in TrayHost.MODULES:
            p = cls(self)
            p.enabled = self.cfg.get_bool(p.Name, "Enabled", True)
            self.plugins.append(p)
            if p.enabled:
                try:
                    p.init()
                except Exception as e:
                    p.enabled = False
                    self.msgbox(f"Module '{p.Name}' failed to start "
                                f"and was disabled:\n{e}")
        # Registered unconditionally; the WM_INPUT handler gates on the
        # NumLock module being enabled. Registration alone is passive.
        self.register_raw_input()
        self.add_tray_icon()
        active = ", ".join(p.Name for p in self.plugins if p.enabled)
        self.balloon(f"{APP_NAME} v{VERSION}",
                     "Active: " + (active or "no modules"))

    def run(self):
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def quit(self):
        for p in self.plugins:
            if p.enabled:
                try:
                    p.shutdown()
                except Exception:
                    pass
        if self.nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
        user32.DestroyWindow(self.hwnd)


TrayHost.MODULES = [NumLockPlugin, KeepAwakePlugin, DownloadsSorterPlugin]


def main():
    kernel32.CreateMutexW(None, False, APP_NAME + "_SingleInstance")
    if ctypes.get_last_error() == 183:            # ERROR_ALREADY_EXISTS
        user32.MessageBoxW(None, APP_NAME + " is already running.",
                           APP_NAME, 0x30)        # MB_ICONWARNING
        return
    host = TrayHost()
    host.start()
    host.run()


if __name__ == "__main__":
    main()
