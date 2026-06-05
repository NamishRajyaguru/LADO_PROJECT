import customtkinter as ctk, sqlite3, sys, os, threading, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
import ui._state as S

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
        self._val_lbl=None
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
        self._build()
        self._sync_state()

    def _build(self):
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

        self._scan_btn=ctk.CTkButton(hdr, text="⟳  Run Scan", width=120, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=ACCENT, text_color=BG, hover_color="#7aa5f5",
            corner_radius=8, command=self._toggle_scan)
        self._scan_btn.pack(side="right")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=36, pady=24)

        grid=ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=36)
        grid.columnconfigure((0,1,2,3), weight=1, uniform="c")

        s=fetch()
        defs=[
            ("TOTAL FILES",  s["files"],        ACCENT,  "indexed",       0),
            ("STORAGE USED", f"{s['size']} GB", ACCENTG, "scanned",       1),
            ("DUPLICATES",   s["dupes"],         ACCENTR, "wasted copies", 2),
            ("PENDING",      s["pending"],       ACCENTY, "suggestions",   3),
        ]
        for label,val,accent,sub,col in defs:
            c=Card(grid, label, val, accent, sub)
            c.grid(row=0, column=col, padx=8, pady=0, sticky="nsew")
            self._cards[label]=c

        scan_card=ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                               border_color=BORDER, border_width=1)
        scan_card.pack(fill="x", padx=36, pady=(16,0))
        ctk.CTkFrame(scan_card, fg_color=ACCENTP, height=2, corner_radius=0).pack(fill="x", side="top")
        sc_inner=ctk.CTkFrame(scan_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=22, pady=18)
        left2=ctk.CTkFrame(sc_inner, fg_color="transparent")
        left2.pack(side="left")
        ctk.CTkLabel(left2, text="LAST SCAN",
            font=ctk.CTkFont(family="Segoe UI", size=9), text_color=MUTED).pack(anchor="w")
        self._scan_lbl=ctk.CTkLabel(left2, text=s["scan"],
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=TEXT)
        self._scan_lbl.pack(anchor="w", pady=(4,0))
        right2=ctk.CTkFrame(sc_inner, fg_color="transparent")
        right2.pack(side="right")
        dot_row=ctk.CTkFrame(right2, fg_color="transparent")
        dot_row.pack(anchor="e")
        ctk.CTkFrame(dot_row, fg_color=ACCENTG, width=7, height=7,
                     corner_radius=4).pack(side="left", pady=2)
        ctk.CTkLabel(dot_row, text="  Backend active  ·  SQLite online",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=MUTED).pack(side="left")

        con_card=ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                              border_color=BORDER, border_width=1)
        con_card.pack(fill="x", padx=36, pady=(16,0))
        con_hdr=ctk.CTkFrame(con_card, fg_color="transparent")
        con_hdr.pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkLabel(con_hdr, text="SCAN OUTPUT",
            font=ctk.CTkFont(family="Segoe UI", size=9), text_color=MUTED).pack(side="left")
        rh=ctk.CTkFrame(con_hdr, fg_color="transparent")
        rh.pack(side="right")
        self._status_lbl=ctk.CTkLabel(rh, text="idle",
            font=ctk.CTkFont(family="Segoe UI", size=9), text_color=DIM)
        self._status_lbl.pack(side="right", padx=(4,0))
        self._status_dot=ctk.CTkFrame(rh, fg_color=DIM, width=7, height=7, corner_radius=4)
        self._status_dot.pack(side="right", pady=2)

        self._console=ctk.CTkTextbox(con_card, height=110,
            font=ctk.CTkFont(family="Courier New", size=9),
            fg_color=BG, text_color=ACCENTG, border_width=0, state="disabled")
        self._console.pack(fill="x", padx=12, pady=(0,12))

    def _sync_state(self):
        """Called every time panel is opened — restore scan state from S module."""
        # Replay all log lines collected so far
        if S.scan_log:
            self._console_write("".join(S.scan_log))
        else:
            self._console_write("Ready. Press 'Run Scan' to start.")

        if S.scan_active:
            self._scan_btn.configure(text="◼  Stop", fg_color=ACCENTR, hover_color="#c44")
            self._status_dot.configure(fg_color=ACCENTY)
            self._status_lbl.configure(text="running", text_color=ACCENTY)
            # re-attach listener so new lines still appear
            threading.Thread(target=self._listen_existing, daemon=True).start()
        else:
            self._scan_btn.configure(text="⟳  Run Scan", fg_color=ACCENT, hover_color="#7aa5f5")

    def _listen_existing(self):
        """Attach to already-running proc and forward new output."""
        if S.scan_proc is None: return
        try:
            for line in S.scan_proc.stdout:
                if not S.scan_active: break
                S.scan_log.append(line)
                self.after(0, lambda l=line: self._console_write(l))
            if S.scan_proc is not None:
                S.scan_proc.wait()
                rc=S.scan_proc.returncode
                if S.scan_active:
                    if rc==0: self.after(0, self._scan_ok)
                    else: self.after(0, lambda: self._scan_err(rc))
        except: pass

    def _toggle_scan(self):
        if S.scan_active: self._stop_scan()
        else: self._start_scan()

    def _start_scan(self):
        S.scan_active=True
        S.scan_proc=None
        S.scan_log=[]
        self._scan_btn.configure(text="◼  Stop", fg_color=ACCENTR, hover_color="#c44")
        self._status_dot.configure(fg_color=ACCENTY)
        self._status_lbl.configure(text="running", text_color=ACCENTY)
        self._console_clear()
        line="Starting scan...\n"
        S.scan_log.append(line)
        self._console_write(line)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _stop_scan(self):
        S.scan_active=False
        try:
            if S.scan_proc and S.scan_proc.poll() is None:
                S.scan_proc.terminate()
        except: pass
        S.scan_proc=None
        self._reset_btn()
        self._status_dot.configure(fg_color=DIM)
        self._status_lbl.configure(text="stopped", text_color=MUTED)
        msg="\nScan stopped."
        S.scan_log.append(msg)
        self._console_write(msg)

    def _scan_worker(self):
        try:
            main_py=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "main.py"
            )
            S.scan_proc=subprocess.Popen(
                [sys.executable, main_py],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                env={**os.environ, "PYTHONIOENCODING":"utf-8"},
            )
            for line in S.scan_proc.stdout:
                if not S.scan_active: break
                S.scan_log.append(line)
                self.after(0, lambda l=line: self._console_write(l))
            if S.scan_proc is not None:
                S.scan_proc.wait()
                rc=S.scan_proc.returncode
            else:
                return
            if S.scan_active:
                if rc==0: self.after(0, self._scan_ok)
                else: self.after(0, lambda: self._scan_err(rc))
        except Exception as e:
            if S.scan_active:
                self.after(0, lambda: self._scan_err(str(e)))

    def _scan_ok(self):
        S.scan_active=False; S.scan_proc=None
        self._reset_btn()
        self._status_dot.configure(fg_color=ACCENTG)
        self._status_lbl.configure(text="done", text_color=ACCENTG)
        msg="\nScan complete ✓  Updating stats..."
        S.scan_log.append(msg)
        self._console_write(msg)
        threading.Thread(target=self._bg_stats, daemon=True).start()

    def _scan_err(self, code):
        S.scan_active=False; S.scan_proc=None
        self._reset_btn()
        self._status_dot.configure(fg_color=ACCENTR)
        self._status_lbl.configure(text="error", text_color=ACCENTR)
        msg=f"\nScan error: {code}"
        S.scan_log.append(msg)
        self._console_write(msg)

    def _reset_btn(self):
        if self.winfo_exists():
            self._scan_btn.configure(text="⟳  Run Scan", fg_color=ACCENT,
                                     hover_color="#7aa5f5", state="normal")

    def _bg_stats(self):
        s=fetch()
        self.after(0, lambda: self._apply_stats(s))

    def _apply_stats(self, s):
        if not self.winfo_exists(): return
        m={"TOTAL FILES":s["files"],"STORAGE USED":f"{s['size']} GB",
           "DUPLICATES":s["dupes"],"PENDING":s["pending"]}
        for k,v in m.items():
            if k in self._cards: self._cards[k].update(v)
        self._scan_lbl.configure(text=s["scan"])
        msg=" Stats updated."
        S.scan_log.append(msg)
        self._console_write(msg)

    def _console_write(self, text):
        if not self.winfo_exists(): return
        self._console.configure(state="normal")
        self._console.insert("end", text)
        self._console.see("end")
        self._console.configure(state="disabled")

    def _console_clear(self):
        self._console.configure(state="normal")
        self._console.delete("1.0","end")
        self._console.configure(state="disabled")