import customtkinter as ctk, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG_BASE="#050508"; BG_SURFACE="#0c0c12"; BG_RAISED="#121219"; BG_HOVER="#1a1a24"
BORDER="#1e1e2e"; TEXT_PRI="#f0f0f8"; TEXT_SEC="#6b6b8a"; TEXT_MUT="#2e2e48"
BLUE="#4d9de0"; GREEN="#3ddc84"; AMBER="#f5a623"; RED="#e05c5c"; PURPLE="#9b72cf"

def fetch():
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); tf = c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); sz = round((c.fetchone()[0] or 0)/1024,2)
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pend=c.fetchone()[0]
        c.execute("SELECT MAX(modified_time) FROM files"); ls=c.fetchone()[0] or "—"
        return {"files":tf,"size":sz,"dupes":hf-uh,"pending":pend,"scan":str(ls)[:16]}
    except Exception as e:
        return {"files":0,"size":0.0,"dupes":0,"pending":0,"scan":f"DB error"}


class Card(ctk.CTkFrame):
    def __init__(self, parent, label, value, accent, sub="", **kw):
        super().__init__(parent, fg_color=BG_RAISED, corner_radius=10,
                         border_color=BORDER, border_width=1, **kw)
        self._val = value; self._accent = accent

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(18,0))

        # accent dot
        ctk.CTkFrame(top, fg_color=accent, width=6, height=6,
                     corner_radius=3).pack(side="left", pady=2)

        ctk.CTkLabel(top, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=TEXT_SEC).pack(side="left", padx=(8,0))

        self._val_lbl = ctk.CTkLabel(self, text=str(value),
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=TEXT_PRI)
        self._val_lbl.pack(anchor="w", padx=18, pady=(10,0))

        if sub:
            ctk.CTkLabel(self, text=sub,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=TEXT_SEC).pack(anchor="w", padx=18, pady=(2,16))
        else:
            ctk.CTkFrame(self, fg_color="transparent", height=16).pack()

        # bottom accent bar
        ctk.CTkFrame(self, fg_color=accent, height=2, corner_radius=0).pack(
            fill="x", side="bottom")

    def update(self, v):
        self._val_lbl.configure(text=str(v))


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._cards = {}
        self._build()

    def _build(self):
        # Page header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28,0))
        ctk.CTkLabel(hdr, text="Overview",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        ctk.CTkButton(hdr, text="Refresh", width=80, height=28,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="transparent", border_color=BORDER, border_width=1,
            text_color=TEXT_SEC, hover_color=BG_HOVER,
            command=self._refresh).pack(side="right")

        ctk.CTkLabel(hdr, text="File system snapshot",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SEC).pack(side="left", padx=(10,0))

        # Thin divider
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=32, pady=20)

        # Card grid — 3 cols
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=32)
        grid.columnconfigure((0,1,2), weight=1, uniform="c")

        s = fetch()
        defs = [
            ("TOTAL FILES",    s["files"],   BLUE,   "indexed",          0,0),
            ("STORAGE USED",   f"{s['size']} GB", GREEN, "scanned",      0,1),
            ("DUPLICATES",     s["dupes"],   RED,    "files",            0,2),
            ("PENDING",        s["pending"], AMBER,  "suggestions",      1,0),
            ("LAST SCAN",      s["scan"],    PURPLE, "",                 1,1),
        ]
        for label, val, accent, sub, row, col in defs:
            c = Card(grid, label, val, accent, sub)
            c.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._cards[label] = c

        # Status strip
        strip = ctk.CTkFrame(self, fg_color=BG_RAISED, corner_radius=8,
                             border_color=BORDER, border_width=1)
        strip.pack(fill="x", padx=32, pady=(16,0))

        dot = ctk.CTkFrame(strip, fg_color=GREEN, width=6, height=6, corner_radius=3)
        dot.pack(side="left", padx=(16,8), pady=14)
        ctk.CTkLabel(strip, text="LADO backend active  ·  SQLite memory layer online",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_SEC).pack(side="left")

    def _refresh(self):
        s = fetch()
        m = {"TOTAL FILES":s["files"],"STORAGE USED":f"{s['size']} GB",
             "DUPLICATES":s["dupes"],"PENDING":s["pending"],"LAST SCAN":s["scan"]}
        for k,v in m.items():
            if k in self._cards: self._cards[k].update(v)
