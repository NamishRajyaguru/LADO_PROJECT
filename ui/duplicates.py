import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
from ui.theme import *

PAGE = 20
_cache = None


def clusters():
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("""SELECT hash,COUNT(*) cnt,SUM(size_mb) sz FROM files
                     WHERE hash IS NOT NULL AND hash!=''
                     GROUP BY hash HAVING cnt>1 ORDER BY sz DESC""")
        return c.fetchall()
    except: return []

def files_in(h):
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT path,name,size_mb,modified_time FROM files WHERE hash=?", (h,))
        return c.fetchall()
    except: return []


class SkeletonCluster(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=GLASS_BG,
                         border_color=GLASS_BORDER, border_width=1,
                         corner_radius=14, **kw)
        self._phase = 0; self._bars = []
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=18)
        for w, side in [(130, "left"), (80, "left"), (100, "left"), (150, "right")]:
            b = ctk.CTkFrame(row, fg_color=SK2, corner_radius=3, width=w, height=9)
            b.pack(side=side, padx=(0 if side == "right" else 12, 0))
            b.pack_propagate(False)
            self._bars.append(b)
        self._tick()

    def _tick(self):
        if not self.winfo_exists(): return
        self._phase = (self._phase + 1) % 24
        c = SK2 if self._phase < 12 else SK1
        for b in self._bars:
            if b.winfo_exists(): b.configure(fg_color=c)
        self.after(90, self._tick)


class Cluster(ctk.CTkFrame):
    def __init__(self, parent, data, idx, **kw):
        super().__init__(parent, fg_color=GLASS_BG,
                         border_color=GLASS_BORDER, border_width=1,
                         corner_radius=14, **kw)
        self._hash, self._cnt, sz = data
        self._sz = float(sz or 0)
        self._expanded = False
        self._detail = None
        wasted = self._sz * (self._cnt - 1) / self._cnt if self._cnt > 1 else 0

        hdr = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        hdr.pack(fill="x", padx=20, pady=16)
        hdr.bind("<Button-1>", self._toggle)

        self._arrow = ctk.CTkLabel(hdr, text="›",
            font=ctk.CTkFont(family=FONT_SANS, size=16, weight="bold"),
            text_color=TEXT_DIM, width=18)
        self._arrow.pack(side="left")
        self._arrow.bind("<Button-1>", self._toggle)

        ctk.CTkLabel(hdr, text=f"  Cluster {idx + 1}",
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color=TEXT).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  ·  {self._cnt} copies",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  ·  {self._sz:.1f} MB total",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=AMBER).pack(side="left")

        # Wasted badge
        badge = ctk.CTkFrame(hdr, fg_color=TEAL_DIM,
                             border_color=TEAL_BORDER, border_width=1,
                             corner_radius=8)
        badge.pack(side="right")
        ctk.CTkLabel(badge, text=f"  ↓ {wasted:.1f} MB free  ",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEAL).pack(padx=4, pady=5)

        ctk.CTkLabel(hdr, text=f"{self._hash[:10]}…",
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIM).pack(side="right", padx=(0, 12))

    def _toggle(self, e=None):
        self._expanded = not self._expanded
        self._arrow.configure(text="∨" if self._expanded else "›")
        if self._expanded:
            self._detail = ctk.CTkFrame(self, fg_color=GLASS_BG2,
                                        corner_radius=10)
            self._detail.pack(fill="x", padx=16, pady=(0, 16))
            for i, (path, name, mb, mod) in enumerate(files_in(self._hash)):
                row = ctk.CTkFrame(self._detail, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=5)
                dot = ctk.CTkFrame(row, fg_color=TEAL if i == 0 else TEXT_DIM,
                                   width=6, height=6, corner_radius=3)
                dot.pack(side="left", padx=(0, 8))
                dot.pack_propagate(False)
                ctk.CTkLabel(row, text=name,
                    font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                    text_color=TEXT).pack(side="left")
                ctk.CTkLabel(row, text=f"  {float(mb or 0):.1f} MB",
                    font=ctk.CTkFont(family=FONT_SANS, size=10),
                    text_color=AMBER).pack(side="left")
                ctk.CTkLabel(row, text=f"  {path}",
                    font=ctk.CTkFont(family=FONT_SANS, size=10),
                    text_color=TEXT_DIM).pack(side="left")
        else:
            if self._detail:
                self._detail.destroy()
                self._detail = None


class DuplicatesPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_DARK, **kw)
        self._all_rows = []
        self._shown = 0
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 0))
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Duplicates",
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Groups of identical files — expand to see paths",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_DIM).pack(anchor="w", pady=(2, 0))

        self._stats = ctk.CTkLabel(hdr, text="",
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
            text_color=TEAL)
        self._stats.pack(side="right")

        ctk.CTkFrame(self, fg_color=GLASS_BORDER, height=1).pack(
            fill="x", padx=32, pady=16)

        self._cnt = ctk.CTkLabel(self, text="",
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            text_color=TEXT_DIM)
        self._cnt.pack(anchor="w", padx=32, pady=(0, 10))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=GLASS_BG2,
            scrollbar_button_hover_color=GLASS_BORDER2)
        self._scroll.pack(fill="both", expand=True, padx=32, pady=(0, 8))

        self._load_more_btn = ctk.CTkButton(self, text="Load 20 more ↓",
            width=160, height=30,
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            fg_color=GLASS_BG2, hover_color=GLASS_BORDER,
            text_color=TEXT_DIM, corner_radius=8,
            command=self._load_more)

        global _cache
        if _cache is not None:
            self._all_rows = _cache
            self._shown = 0
            wasted = sum(float(sz or 0) * (cnt - 1) / cnt
                         for _, cnt, sz in _cache if cnt > 1)
            self._stats.configure(text=f"↓ {wasted:.1f} MB recoverable")
            self._cnt.configure(text=f"{len(_cache)} clusters found")
            self._render_next_page()
        else:
            for _ in range(5):
                SkeletonCluster(self._scroll).pack(fill="x", pady=5)
            threading.Thread(target=self._bg, daemon=True).start()

    def _bg(self):
        cl = clusters()
        self.after(0, lambda: self._render(cl))

    def _render(self, cl):
        global _cache
        if not self.winfo_exists(): return
        _cache = cl
        self._all_rows = cl
        self._shown = 0
        wasted = sum(float(sz or 0) * (cnt - 1) / cnt
                     for _, cnt, sz in cl if cnt > 1)
        for w in self._scroll.winfo_children(): w.destroy()
        self._stats.configure(text=f"↓ {wasted:.1f} MB recoverable")
        self._cnt.configure(text=f"{len(cl)} clusters found")
        if not cl:
            ctk.CTkLabel(self._scroll, text="No duplicates found.",
                font=ctk.CTkFont(family=FONT_SANS, size=13),
                text_color=TEXT_DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_next_page(self):
        start = self._shown
        end = min(start + PAGE, len(self._all_rows))
        for i in range(start, end):
            Cluster(self._scroll, self._all_rows[i], i).pack(fill="x", pady=5)
        self._shown = end
        if self._shown < len(self._all_rows):
            remaining = len(self._all_rows) - self._shown
            self._load_more_btn.configure(
                text=f"Load 20 more  ·  {remaining} remaining ↓")
            self._load_more_btn.pack(pady=(4, 20))
        else:
            self._load_more_btn.pack_forget()

    def _load_more(self):
        self._render_next_page()