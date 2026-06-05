import customtkinter as ctk, sqlite3, sys, os, threading, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTG="#3ecf8e";ACCENTR="#e05c72";ACCENTY="#f0a84a";ACCENTP="#a78bfa"

def fetch():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); tf=c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); sz=round((c.fetchone()[0] or 0)/1024,2)
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pend=c.fetchone()[0]
        c.execute("SELECT MAX(modified_time) FROM files"); ls=str(c.fetchone()[0] or "—")[:16]
        return {"files":tf,"size":sz,"dupes":hf-uh,"pending":pend,"scan":ls}
    except:
        return {"files":0,"size":0.0,"dupes":0,"pending":0,"scan":"No DB yet"}


class Card(ctk.CTkFrame):
    def __init__(self, parent, label, value, accent, sub="", **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=14,
                         border_color=BORDER, border_width=1, **kw)
        self._val_lbl = None
        ctk.CTkFrame(self, fg_color=accent, height=2, corner_radius=0).pack(fill="x", side="top")
        body=ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=20)
        lrow=ctk.CTkFrame(body, fg_color="transparent")
        lrow.pack(anchor="w")
        ctk.CTkFrame(lrow, fg_color=accent, width=5, height=5, corner_radius=3).pack(side="left", pady=1)
        ctk.CTkLabel(lrow, text=f"  {label}",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=MUTED).pack(side="left")
        self._val_lbl=ctk.CTkLabel(body, text=str(value),
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT)
        self._val_lbl.pack(anchor="w", pady=(10,0))
        if sub:
            ctk.CTkLabel(body, text=sub,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=DIM).pack(anchor="w", pady=(2,0))

    def update(self, v):
        if self._val_lbl:
            self._val_lbl.configure(text=str(v))


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._cards={}
        self._scanning=False
        self._build()

    def _build(self):
        # Header
        hdr=ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=36, pady=(32,0))
        left=ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Overview",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Live snapshot of your file system",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED).pack(anchor="w", pady=(2,0))

        # Buttons row
        btn_row=ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(btn_row, text="↻  Refresh Stats", width=110, height=30,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="transparent", border_color=BORDER_HI, border_width=1,
            text_color=MUTED, hover_color=CARD2, corner_radius=8,
            command=self._refresh_stats).pack(side="right", padx=(8,0))

        self._scan_btn=ctk.CTkButton(btn_row, text="⟳  Run Scan", width=100, height=30,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=ACCENT, text_color=BG, hover_color="#7aa5f5",
            corner_radius=8, command=self._run_scan)
        self._scan_btn.pack(side="right")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=36, pady=24)

        # Cards grid
        grid=ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=36)
        grid.columnconfigure((0,1,2,3), weight=1, uniform="c")

        s=fetch()
        defs=[
            ("TOTAL FILES",  s["files"],         ACCENT,  "indexed",       0),
            ("STORAGE USED", f"{s['size']} GB",  ACCENTG, "scanned",       1),
            ("DUPLICATES",   s["dupes"],          ACCENTR, "wasted copies", 2),
            ("PENDING",      s["pending"],        ACCENTY, "suggestions",   3),
        ]
        for label,val,accent,sub,col in defs:
            c=Card(grid, label, val, accent, sub)
            c.grid(row=0, column=col, padx=8, pady=0, sticky="nsew")
            self._cards[label]=c

        # Last scan card
        scan_card=ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                               border_color=BORDER, border_width=1)
        scan_card.pack(fill="x", padx=36, pady=(16,0))
        ctk.CTkFrame(scan_card, fg_color=ACCENTP, height=2, corner_radius=0).pack(fill="x", side="top")
        sc_inner=ctk.CTkFrame(scan_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=22, pady=18)
        left2=ctk.CTkFrame(sc_inner, fg_color="transparent")
        left2.pack(side="left")
        ctk.CTkLabel(left2, text="LAST SCAN",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=MUTED).pack(anchor="w")
        self._scan_lbl=ctk.CTkLabel(left2, text=s["scan"],
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT)
        self._scan_lbl.pack(anchor="w", pady=(4,0))
        right2=ctk.CTkFrame(sc_inner, fg_color="transparent")
        right2.pack(side="right")
        dot_row=ctk.CTkFrame(right2, fg_color="transparent")
        dot_row.pack(anchor="e")
        ctk.CTkFrame(dot_row, fg_color=ACCENTG, width=7, height=7,
                     corner_radius=4).pack(side="left", pady=2)
        ctk.CTkLabel(dot_row, text="  Backend active  ·  SQLite online",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=MUTED).pack(side="left")

        # Scan output console
        self._console_frame=ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                                          border_color=BORDER, border_width=1)
        self._console_frame.pack(fill="x", padx=36, pady=(16,0))
        console_hdr=ctk.CTkFrame(self._console_frame, fg_color="transparent")
        console_hdr.pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkLabel(console_hdr, text="SCAN OUTPUT",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=MUTED).pack(side="left")
        self._status_dot=ctk.CTkFrame(console_hdr, fg_color=DIM,
                                       width=7, height=7, corner_radius=4)
        self._status_dot.pack(side="right", pady=2)
        self._status_lbl=ctk.CTkLabel(console_hdr, text="idle",
            font=ctk.CTkFont(family="Segoe UI", size=9), text_color=DIM)
        self._status_lbl.pack(side="right", padx=(0,6))

        self._console=ctk.CTkTextbox(self._console_frame,
            height=90, font=ctk.CTkFont(family="Courier New", size=9),
            fg_color=BG, text_color=ACCENTG, border_width=0,
            state="disabled")
        self._console.pack(fill="x", padx=12, pady=(0,12))
        self._console_write("Ready. Press 'Run Scan' to start a new scan.")

    # ── Scan stats ────────────────────────────────────────────
    def _refresh_stats(self):
        threading.Thread(target=self._bg_stats, daemon=True).start()

    def _bg_stats(self):
        s=fetch()
        self.after(0, lambda: self._apply_stats(s))

    def _apply_stats(self, s):
        m={"TOTAL FILES":s["files"],"STORAGE USED":f"{s['size']} GB",
           "DUPLICATES":s["dupes"],"PENDING":s["pending"]}
        for k,v in m.items():
            if k in self._cards: self._cards[k].update(v)
        self._scan_lbl.configure(text=s["scan"])

    # ── Run scan ──────────────────────────────────────────────
    def _run_scan(self):
        if self._scanning: return
        self._scanning=True
        self._scan_btn.configure(state="disabled", text="Scanning…", fg_color=DIM)
        self._status_dot.configure(fg_color=ACCENTY)
        self._status_lbl.configure(text="running", text_color=ACCENTY)
        self._console_clear()
        self._console_write("Starting scan...\n")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            # get path to main.py (one level up from ui/)
            main_py=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "main.py"
            )
            proc=subprocess.Popen(
                [sys.executable, main_py],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            for line in proc.stdout:
                self.after(0, lambda l=line: self._console_write(l))
            proc.wait()
            if proc.returncode==0:
                self.after(0, self._scan_done_ok)
            else:
                self.after(0, lambda: self._scan_done_err(proc.returncode))
        except Exception as e:
            self.after(0, lambda: self._scan_done_err(str(e)))

    def _scan_done_ok(self):
        self._scanning=False
        self._scan_btn.configure(state="normal", text="⟳  Run Scan", fg_color=ACCENT)
        self._status_dot.configure(fg_color=ACCENTG)
        self._status_lbl.configure(text="done", text_color=ACCENTG)
        self._console_write("\nScan complete. Click 'Refresh Stats' to update numbers.")
        self._refresh_stats()

    def _scan_done_err(self, code):
        self._scanning=False
        self._scan_btn.configure(state="normal", text="⟳  Run Scan", fg_color=ACCENT)
        self._status_dot.configure(fg_color=ACCENTR)
        self._status_lbl.configure(text=f"error ({code})", text_color=ACCENTR)
        self._console_write(f"\nScan exited with error: {code}")

    # ── Console helpers ───────────────────────────────────────
    def _console_write(self, text):
        self._console.configure(state="normal")
        self._console.insert("end", text)
        self._console.see("end")
        self._console.configure(state="disabled")

    def _console_clear(self):
        self._console.configure(state="normal")
        self._console.delete("1.0","end")
        self._console.configure(state="disabled")