import customtkinter as ctk, os, sys, threading
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try: from config import LOG_DIR
except: LOG_DIR = None

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTG="#3ecf8e";ACCENTR="#e05c72";ACCENTY="#f0a84a"

_cache = None

LEVEL_CLR = {
    "ERROR":   ACCENTR,
    "WARNING": ACCENTY,
    "INFO":    ACCENTG,
    "DEBUG":   MUTED,
}

def get_log_files():
    if not LOG_DIR or not os.path.exists(LOG_DIR): return []
    files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")], reverse=True)
    return files[:7]  # last 7 days

def read_log(filename):
    try:
        path = os.path.join(LOG_DIR, filename)
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines if l.strip()]
    except: return []

def parse_level(line):
    for lvl in ["ERROR","WARNING","INFO","DEBUG"]:
        if lvl in line.upper():
            return lvl
    return "INFO"


class LogLine(ctk.CTkFrame):
    def __init__(self, parent, line, idx, **kw):
        bg = CARD if idx%2==0 else SURFACE
        super().__init__(parent, fg_color=bg, corner_radius=0, height=24, **kw)
        self.pack_propagate(False)
        lvl = parse_level(line)
        clr = LEVEL_CLR.get(lvl, MUTED)

        # level badge
        ctk.CTkLabel(self, text=f" {lvl[:4]} ",
            font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
            text_color=BG, fg_color=clr, corner_radius=3,
            width=36).pack(side="left", padx=(12,8), pady=4)

        ctk.CTkLabel(self, text=line[:160],
            font=ctk.CTkFont(family="Courier New", size=9),
            text_color=TEXT if lvl=="ERROR" else MUTED,
            anchor="w").pack(side="left", fill="x", expand=True, padx=(0,12))


class LogsPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._selected_file = None
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=36, pady=(32,0))
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Logs",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Activity and audit trail from LADO backend",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED).pack(anchor="w", pady=(2,0))

        self._cnt = ctk.CTkLabel(hdr, text="",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=MUTED)
        self._cnt.pack(side="right")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=36, pady=24)

        # File picker strip
        files = get_log_files()
        if not files:
            ctk.CTkLabel(self, text="No log files found. Run python main.py first.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=DIM).pack(pady=60)
            return

        picker = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10,
                              border_color=BORDER, border_width=1)
        picker.pack(fill="x", padx=36, pady=(0,16))

        self._file_btns = {}
        for f in files:
            label = f.replace(".log","")
            is_today = f == datetime.now().strftime("%Y-%m-%d") + ".log"
            btn = ctk.CTkButton(picker, text=f"{'Today' if is_today else label}",
                width=110, height=30,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                fg_color=ACCENT if is_today else "transparent",
                text_color=BG if is_today else MUTED,
                hover_color=CARD2, corner_radius=8,
                command=lambda x=f: self._select(x))
            btn.pack(side="left", padx=5, pady=5)
            self._file_btns[f] = btn

        # Scroll area
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=36, pady=(0,28))

        # Auto-select today or first
        first = datetime.now().strftime("%Y-%m-%d") + ".log"
        self._select(first if first in files else files[0])

    def _select(self, filename):
        self._selected_file = filename
        # update button states
        for f, btn in self._file_btns.items():
            btn.configure(
                fg_color=ACCENT if f==filename else "transparent",
                text_color=BG if f==filename else MUTED
            )
        self._load(filename)

    def _load(self, filename):
        for w in self._scroll.winfo_children(): w.destroy()
        # loading indicator
        lbl = ctk.CTkLabel(self._scroll, text="Reading log…",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=MUTED)
        lbl.pack(pady=20)
        threading.Thread(target=lambda: self._bg(filename), daemon=True).start()

    def _bg(self, filename):
        lines = read_log(filename)
        self.after(0, lambda: self._render(lines))

    def _render(self, lines):
        if not self.winfo_exists(): return
        for w in self._scroll.winfo_children(): w.destroy()
        if not lines:
            ctk.CTkLabel(self._scroll, text="Log file is empty.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=DIM).pack(pady=40)
            self._cnt.configure(text="0 entries")
            return
        # show last 100 lines (most recent activity)
        shown = lines[-100:]
        self._cnt.configure(text=f"{len(shown)} of {len(lines)} entries")
        for i, line in enumerate(shown):
            LogLine(self._scroll, line, i).pack(fill="x")