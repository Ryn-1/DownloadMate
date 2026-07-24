import ctypes
import ctypes.wintypes
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

import sorter as engine

NIM_ADD = 0
NIM_DELETE = 2

NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4

WM_APP = 0x8000
WM_TRAY_CALLBACK = WM_APP + 1
WM_DESTROY = 2
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x202
WM_RBUTTONUP = 0x205
WM_LBUTTONDBLCLK = 0x203

MF_STRING = 0
MF_SEPARATOR = 0x800
TPM_RIGHTBUTTON = 2
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x10
ERROR_CLASS_ALREADY_EXISTS = 1410

LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.wintypes.HICON),
        ("hCursor", ctypes.wintypes.HCURSOR),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.wintypes.UINT),
        ("uFlags", ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.wintypes.WCHAR * 128),
        ("dwState", ctypes.wintypes.DWORD),
        ("dwStateMask", ctypes.wintypes.DWORD),
        ("szInfo", ctypes.wintypes.WCHAR * 256),
        ("uVersion", ctypes.wintypes.UINT),
        ("szInfoTitle", ctypes.wintypes.WCHAR * 64),
        ("dwInfoFlags", ctypes.wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", ctypes.wintypes.HICON),
    ]


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

HWND = ctypes.wintypes.HWND
UINT = ctypes.wintypes.UINT
WPARAM = ctypes.wintypes.WPARAM
LPARAM = ctypes.wintypes.LPARAM

user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.DestroyWindow.argtypes = [HWND]
user32.DestroyWindow.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [HWND]
user32.SetForegroundWindow.restype = ctypes.c_bool
user32.GetCursorPos.restype = ctypes.c_bool


class App(tk.Tk):
    def __init__(self, config_path=None):
        super().__init__()
        if config_path is None:
            engine.init_config()
            config_path = engine.SCRIPT_DIR / "config.json"
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.folder_frames = {}
        self.skip_frames = {}

        self.poll_interval_ms = self.config.get("poll_interval_sec", 3) * 1000
        self.stability_threshold = self.config.get("stability_checks", 2)
        self._pending = {}
        self._daemon_running = True
        self._nid = None
        self._tray_hwnd = None

        self.title("DownloadMate")
        self.geometry("550x350")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        icon_file = engine.SCRIPT_DIR / "assets" / "Icon.ico"
        if icon_file.exists():
            try:
                self.iconbitmap(str(icon_file))
            except Exception:
                pass

        self._setup_tray()
        self._build_ui()
        self.after(self.poll_interval_ms, self._poll)

    def _setup_tray(self):
        hinstance = kernel32.GetModuleHandleW(None)

        self._tray_wndproc_cb = WNDPROC(self._tray_wndproc)

        wc = WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = self._tray_wndproc_cb
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = "DownloadOrganizerTray"

        if not user32.RegisterClassW(ctypes.byref(wc)):
            err = ctypes.get_last_error()
            if err != ERROR_CLASS_ALREADY_EXISTS:
                raise ctypes.WinError(err)

        self._tray_hwnd = user32.CreateWindowExW(
            0, "DownloadOrganizerTray", "Download Organizer Tray",
            0, 0, 0, 0, 0,
            ctypes.wintypes.HWND(-3),
            None, hinstance, None
        )

        icon_path = engine.SCRIPT_DIR / "assets" / "Icon.ico"
        hicon = None
        if icon_path.exists():
            hicon = user32.LoadImageW(
                None, str(icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE
            )

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._tray_hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY_CALLBACK
        nid.hIcon = hicon
        nid.szTip = "DownloadMate"

        self._nid = nid
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _remove_tray_icon(self):
        if self._nid is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None

    def _tray_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY_CALLBACK:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self._show_window()
            elif lparam == WM_RBUTTONUP:
                self._show_context_menu()
        elif msg == WM_COMMAND:
            item_id = wparam & 0xFFFF
            if item_id == 1002:
                self._show_window()
            elif item_id == 1003:
                self._on_exit()
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_context_menu(self):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, 1002, "Open Config")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, 1003, "Exit")

        pos = POINT()
        user32.GetCursorPos(ctypes.byref(pos))
        user32.SetForegroundWindow(self._tray_hwnd)
        user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON, pos.x, pos.y, 0, self._tray_hwnd, None)
        user32.DestroyMenu(menu)

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _hide_to_tray(self):
        self.withdraw()

    def _on_exit(self):
        self._daemon_running = False
        self._remove_tray_icon()
        if self._tray_hwnd:
            user32.DestroyWindow(self._tray_hwnd)
            self._tray_hwnd = None
        self.quit()

    def _make_scrollable_tab(self, notebook, text, bg=None):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=text)

        canvas = tk.Canvas(tab, borderwidth=0, highlightthickness=0, bg=bg)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        inner = ttk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_wheel)

        def _on_leave(event):
            canvas.unbind_all("<MouseWheel>")

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_canvas_configure(event):
            canvas.itemconfig(inner_window, width=event.width)
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

        return inner

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("xpnative")

        c = {
            "bg": "#f0f0f0",
            "bg_dark": "#d9d9d9",
            "bg_input": "#ffffff",
            "fg": "#2c2c2c",
            "fg_label": "#555555",
        }

        style.configure(".", background=c["bg"])
        style.configure("TLabel", foreground=c["fg_label"])
        style.configure("TEntry", fieldbackground=c["bg_input"], foreground=c["fg"])
        style.configure("TButton", background=c["bg_dark"], foreground=c["fg"])
        style.map("TButton", background=[("active", "#cce4f7")])
        style.configure("TSpinbox", fieldbackground=c["bg_input"], foreground=c["fg"])
        style.configure("TNotebook", background=c["bg"])
        style.configure("TNotebook.Tab", background=c["bg_dark"], foreground=c["fg"], padding=[10, 2])
        style.map("TNotebook.Tab", background=[("selected", c["bg"])])
        style.configure("Vertical.TScrollbar", background=c["bg_dark"])
        style.configure("TFrame", background=c["bg"])

        self.configure(bg=c["bg"])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.general_frame = self._make_scrollable_tab(notebook, "General", bg=c["bg"])

        ttk.Label(self.general_frame, text="Downloads Path:").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 0)
        )
        self.downloads_path_var = tk.StringVar(value=self.config["downloads_path"])
        ttk.Entry(self.general_frame, textvariable=self.downloads_path_var, width=30).grid(
            row=0, column=1, sticky="w", padx=(0, 10), pady=(10, 0)
        )

        ttk.Label(self.general_frame, text="").grid(row=1, column=0, pady=3)

        ttk.Label(self.general_frame,
                  text="How often the app scans the Downloads folder"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 0))

        ttk.Label(self.general_frame, text="Poll Interval (sec):").grid(
            row=3, column=0, sticky="w", padx=10, pady=(10, 0)
        )
        self.poll_interval_var = tk.IntVar(value=self.config.get("poll_interval_sec", 3))
        ttk.Spinbox(self.general_frame, from_=1, to=60,
                    textvariable=self.poll_interval_var, width=5).grid(
            row=3, column=1, sticky="w", padx=(0, 10), pady=(10, 0)
        )

        ttk.Label(self.general_frame, text="").grid(row=4, column=0, pady=3)

        ttk.Label(self.general_frame,
                  text="Times a file must stay unchanged before sorting"
                  ).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 0))

        ttk.Label(self.general_frame, text="Stability Checks:").grid(
            row=6, column=0, sticky="w", padx=10, pady=(10, 0)
        )
        self.stability_checks_var = tk.IntVar(value=self.config.get("stability_checks", 2))
        ttk.Spinbox(self.general_frame, from_=1, to=10,
                     textvariable=self.stability_checks_var, width=5).grid(
            row=6, column=1, sticky="w", padx=(0, 10), pady=(10, 0)
        )

        ttk.Label(self.general_frame, text="Extensions to Skip:").grid(
            row=0, column=2, columnspan=2, sticky="w", padx=10, pady=(10, 0)
        )

        ttk.Button(self.general_frame, text="+ Add Extension", command=self.add_skip).grid(
            row=1, column=2, sticky="w", padx=10, pady=(10, 5)
        )

        for i, ext in enumerate(self.config.get("skip_extensions", []), start=2):
            self.create_skip_row(i, ext)

        self.folders_frame = self._make_scrollable_tab(notebook, "Folders", bg=c["bg"])

        ttk.Button(self.folders_frame, text="+ Add Folder", command=self.add_folder).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5)
        )

        for i, (folder_name, extensions) in enumerate(self.config.get("folders", {}).items(), start=1):
            self.create_folder_row(i, folder_name, extensions)

        ttk.Button(self, text="Save", command=self.on_save).pack(fill="x", padx=10, pady=(0, 10))

    def _load_config(self):
        with open(self.config_path) as f:
            return json.load(f)

    def _save_config(self, config):
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def create_folder_row(self, row, folder_name="", extensions=None):
        name_var = tk.StringVar(value=folder_name)
        ext_var = tk.StringVar(value=", ".join(extensions) if extensions else "")

        name_entry = ttk.Entry(self.folders_frame, textvariable=name_var, width=20)
        name_entry.grid(row=row, column=0, padx=(10, 5), pady=5)
        ext_entry = ttk.Entry(self.folders_frame, textvariable=ext_var, width=40)
        ext_entry.grid(row=row, column=1, padx=5, pady=5)
        remove_button = ttk.Button(self.folders_frame, text="X", width=3,
                                   command=lambda r=row: self.remove_folder(r))
        remove_button.grid(row=row, column=2, padx=(5, 10), pady=5)

        self.folder_frames[row] = (name_var, ext_var, name_entry, ext_entry, remove_button)

    def add_folder(self):
        existing_rows = list(self.folder_frames.keys())
        next_row = max(existing_rows, default=0) + 1
        self.create_folder_row(next_row)

    def remove_folder(self, row):
        if row in self.folder_frames:
            name_var, ext_var, name_entry, ext_entry, remove_button = self.folder_frames.pop(row)
            name_entry.destroy()
            ext_entry.destroy()
            remove_button.destroy()

    def create_skip_row(self, row, ext=""):
        ext_var = tk.StringVar(value=ext)
        frame = ttk.Frame(self.general_frame)
        frame.grid(row=row, column=2, columnspan=2, sticky="w", padx=10, pady=2)
        ttk.Entry(frame, textvariable=ext_var, width=20).pack(side="left")
        ttk.Button(frame, text="X", width=3,
                   command=lambda r=row: self.remove_skip(r)).pack(side="left", padx=(5, 0))
        self.skip_frames[row] = (ext_var, frame)

    def add_skip(self):
        existing_rows = list(self.skip_frames.keys())
        next_row = max(existing_rows, default=2) + 1
        self.create_skip_row(next_row)

    def remove_skip(self, row):
        if row in self.skip_frames:
            ext_var, frame = self.skip_frames.pop(row)
            frame.destroy()

    def on_save(self):
        downloads_path = Path(self.downloads_path_var.get().strip())
        old_folders = set(self.config.get("folders", {}).keys())

        self.config["downloads_path"] = str(downloads_path)
        self.config["poll_interval_sec"] = self.poll_interval_var.get()
        self.config["stability_checks"] = self.stability_checks_var.get()

        skip_extensions = []
        for ext_var, _ in self.skip_frames.values():
            ext = ext_var.get().strip()
            if ext and ext not in skip_extensions:
                skip_extensions.append(ext)
        self.config["skip_extensions"] = skip_extensions

        folders = {}
        for name_var, ext_var, _, _, _ in self.folder_frames.values():
            folder_name = name_var.get().strip()
            extensions_raw = ext_var.get().strip()
            if folder_name and extensions_raw:
                extensions = [e.strip() for e in extensions_raw.split(",") if e.strip()]
                if extensions and folder_name not in folders:
                    folders[folder_name] = extensions
        self.config["folders"] = folders

        new_folders = set(folders.keys())

        for folder_name in new_folders:
            folder_path = downloads_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

        for folder_name in old_folders - new_folders:
            folder_path = downloads_path / folder_name
            if folder_path.is_dir():
                if not any(folder_path.iterdir()):
                    folder_path.rmdir()
                else:
                    messagebox.showwarning("Warning",
                        f"Folder '{folder_name}' is not empty and was not deleted.")

        self._save_config(self.config)
        self.poll_interval_ms = self.poll_interval_var.get() * 1000
        self.stability_threshold = self.stability_checks_var.get()
        messagebox.showinfo("Saved", "Config saved successfully.")

    def _sort_now(self):
        try:
            engine.organize(str(self.config_path))
        except Exception as e:
            print(f"Sort error: {e}")

    def _poll(self):
        if not self._daemon_running:
            return
        try:
            self._poll_once()
        except Exception as e:
            print(f"Poll error: {e}")
        self.after(self.poll_interval_ms, self._poll)

    def _poll_once(self):
        try:
            downloads_path, skip_extensions, extension_to_folder, unsorted_folder = (
                engine.configure(str(self.config_path))
            )
        except Exception as e:
            print(f"Config reload error: {e}")
            return

        current_files = set()
        try:
            for entry in downloads_path.iterdir():
                if not entry.is_file():
                    continue
                current_files.add(entry.name)
                self._check_file(entry, skip_extensions, extension_to_folder, unsorted_folder,
                                 downloads_path)
        except FileNotFoundError:
            return

        for file_name in list(self._pending.keys()):
            if file_name not in current_files:
                del self._pending[file_name]

    def _check_file(self, entry, skip_extensions, extension_to_folder, unsorted_folder,
                    downloads_path):
        file_name = entry.name

        if engine.should_skip(entry, skip_extensions):
            self._pending.pop(file_name, None)
            return

        folder_name = engine.get_target_folder(entry, extension_to_folder, unsorted_folder)
        if not folder_name:
            return

        try:
            stats = entry.stat()
        except OSError:
            return

        if file_name in self._pending:
            if self._pending[file_name]["size"] == stats.st_size:
                self._pending[file_name]["stability_count"] += 1
            else:
                self._pending[file_name] = {"size": stats.st_size, "stability_count": 0}

            if self._pending[file_name]["stability_count"] >= self.stability_threshold:
                if engine.move_file(entry, folder_name, downloads_path):
                    del self._pending[file_name]
        else:
            self._pending[file_name] = {"size": stats.st_size, "stability_count": 0}


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
