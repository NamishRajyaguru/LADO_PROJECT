import customtkinter as ctk, sqlite3, sys, os, threading, subprocess, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
import ui._state as S
from ui.watcher import register_callback, unregister_callback
from ui.theme import *

def fetch():
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); tf = c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); sz = round((c.fetchone()[0] or 0) / 1024, 2)
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pend = c.fetchone()[0]
        return {"files": tf, "size": sz, "dupes": hf - uh, "pending": pend}
    except:
        return {"files": 0, "size": 0.0, "dupes": 0, "pending": 0}


class GlassCard(ctk.CTkFrame):
    def __init__(self, parent, label, value, accent_color, accent_dim, sub="", **kw):
        super().__init__(parent,
            fg_color=GLASS_BG,
            border_color=GLASS_BORDER,
            border_width=1,
            corner_radius=18, **kw)
        self._val_lbl = None
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=18)

        # Label row with colored dot
        lrow = ctk.CTkFrame(body, fg_color="transparent")
        lrow.pack(anchor="w")
        dot = ctk.CTkFrame(lrow, fg_color=accent_color,
                           width=6, height=6, corner_radius=3)
        dot.pack(side="left", pady=1)
        dot.pack_propagate(False)
        ctk.CTkLabel(lrow, text=f"  {label}",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_DIM).pack(side="left")

        self._val_lbl = ctk.CTkLabel(body, text=str(value),
            font=ctk.CTkFont(family=FONT_SANS, size=32, weight="bold"),
            text_color=TEXT)
        self._val_lbl.pack(anchor="w", pady=(10, 0))

        if sub:
            ctk.CTkLabel(body, text=sub,
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color=TEXT_DIM).pack(anchor="w", pady=(2, 0))

    def update(self, v):
        if self._val_lbl and self.winfo_exists():
            self._val_lbl.configure(text=str(v))


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_DARK, **kw)
        self._cards = {}
        self._success_fired = False
        self._build()
        self._sync_state()
        register_callback(self._on_watcher_event)

    def _on_watcher_event(self):
        self.after(0, lambda: threading.Thread(
            target=self._bg_stats, daemon=True).start())
        self.after(0, lambda: self._console_write(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] File change detected — refreshing stats.\n"))

    def destroy(self):
        unregister_callback(self._on_watcher_event)
        super().destroy()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 0))
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Overview",
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Live snapshot of your file system",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_DIM).pack(anchor="w", pady=(2, 0))

        self._scan_btn = ctk.CTkButton(hdr,
            text="⟳  Run Scan", width=140, height=38,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            fg_color=PURPLE, hover_color="#5c2dff",
            text_color=TEXT, corner_radius=12,
            command=self._toggle_scan)
        self._scan_btn.pack(side="right")

        # Main content
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=28, pady=(16, 20))

        left_col = ctk.CTkFrame(main, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right_col = ctk.CTkFrame(main, fg_color="transparent", width=340)
        right_col.pack(side="right", fill="both")
        right_col.pack_propagate(False)

        # Stat cards grid
        grid = ctk.CTkFrame(left_col, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1, uniform="c")

        s = fetch()
        defs = [
            ("TOTAL FILES",  s["files"],        PURPLE, PURPLE_DIM, "indexed"),
            ("STORAGE USED", f"{s['size']} GB", TEAL,   TEAL_DIM,   "scanned"),
            ("DUPLICATES",   s["dupes"],         PINK,   PINK_DIM,   "wasted copies"),
            ("PENDING",      s["pending"],       AMBER,  AMBER_DIM,  "suggestions"),
        ]
        for i, (label, val, color, dim, sub) in enumerate(defs):
            c = GlassCard(grid, label, val, color, dim, sub)
            c.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")
            self._cards[label] = c

        # Last scan card
        scan_card = ctk.CTkFrame(left_col,
            fg_color=GLASS_BG, border_color=GLASS_BORDER,
            border_width=1, corner_radius=18)
        scan_card.pack(fill="x", padx=5, pady=(10, 0))
        sc_inner = ctk.CTkFrame(scan_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=20, pady=16)

        lft = ctk.CTkFrame(sc_inner, fg_color="transparent")
        lft.pack(side="left")
        ctk.CTkLabel(lft, text="LAST SCAN",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_DIM).pack(anchor="w")
        self._scan_lbl = ctk.CTkLabel(lft,
            text=S.last_scan_time if S.last_scan_time else "—",
            font=ctk.CTkFont(family=FONT_SANS, size=17, weight="bold"),
            text_color=TEXT)
        self._scan_lbl.pack(anchor="w", pady=(4, 0))

        rgt = ctk.CTkFrame(sc_inner, fg_color="transparent")
        rgt.pack(side="right")
        self._pill = ctk.CTkFrame(rgt, fg_color=TEAL_DIM,
                                   corner_radius=20)
        self._pill.pack()
        self._pill_lbl = ctk.CTkLabel(self._pill, text="● Ready",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEAL)
        self._pill_lbl.pack(padx=14, pady=6)

        # Console card
        con = ctk.CTkFrame(right_col,
            fg_color=GLASS_BG, border_color=GLASS_BORDER,
            border_width=1, corner_radius=18)
        con.pack(fill="both", expand=True, padx=5, pady=5)

        con_hdr = ctk.CTkFrame(con, fg_color="transparent")
        con_hdr.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkLabel(con_hdr, text="SCAN OUTPUT",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_DIM).pack(side="left")

        rh = ctk.CTkFrame(con_hdr, fg_color="transparent")
        rh.pack(side="right")
        self._status_lbl = ctk.CTkLabel(rh, text="idle",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_DIM)
        self._status_lbl.pack(side="right", padx=(5, 0))
        self._status_dot = ctk.CTkFrame(rh, fg_color=TEXT_DIM,
                                         width=6, height=6, corner_radius=3)
        self._status_dot.pack(side="right", pady=2)
        self._status_dot.pack_propagate(False)

        self._console = ctk.CTkTextbox(con,
            font=ctk.CTkFont(family=FONT_MONO, size=10),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            border_width=0, corner_radius=0, state="disabled")
        self._console.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _sync_state(self):
        if S.scan_log:
            self._console_write("".join(S.scan_log))
        else:
            self._console_write("Ready. Press 'Run Scan' to start.\n")
        if S.last_scan_time:
            self._scan_lbl.configure(text=S.last_scan_time)
            self._pill_lbl.configure(text="● Up to date", text_color=TEAL)
        threading.Thread(target=self._bg_stats, daemon=True).start()
        if S.scan_active:
            self._set_scanning_ui()
            threading.Thread(target=self._listen_existing, daemon=True).start()

    def _listen_existing(self):
        if S.scan_proc is None: return
        try:
            for line in S.scan_proc.stdout:
                if not S.scan_active: break
                S.scan_log.append(line)
                self.after(0, lambda l=line: self._console_write(l))
                if "LADO run complete" in line and not self._success_fired:
                    self._success_fired = True
                    self.after(0, self._scan_ok)
                    return
        except: pass

    def _toggle_scan(self):
        if S.scan_active: self._stop_scan()
        else: self._start_scan()

    def _start_scan(self):
        S.scan_active = True; S.scan_proc = None; S.scan_log = []
        self._success_fired = False
        self._set_scanning_ui()
        self._console_clear()
        line = "Starting scan...\n"
        S.scan_log.append(line)
        self._console_write(line)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _set_scanning_ui(self):
        self._scan_btn.configure(text="◼  Stop", fg_color=RED, hover_color="#cc2200")
        self._status_dot.configure(fg_color=AMBER)
        self._status_lbl.configure(text="running", text_color=AMBER)
        self._pill_lbl.configure(text="● Scanning…", text_color=AMBER)

    def _stop_scan(self):
        S.scan_active = False
        try:
            if S.scan_proc and S.scan_proc.poll() is None:
                S.scan_proc.terminate()
        except: pass
        S.scan_proc = None
        self._reset_btn()
        self._status_dot.configure(fg_color=TEXT_DIM)
        self._status_lbl.configure(text="stopped", text_color=TEXT_DIM)
        self._pill_lbl.configure(text="● Stopped", text_color=TEXT_DIM)
        msg = "\nScan stopped.\n"
        S.scan_log.append(msg)
        self._console_write(msg)

    def _scan_worker(self):
        try:
            main_py = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "main.py")
            S.scan_proc = subprocess.Popen(
                [sys.executable, main_py],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            for line in S.scan_proc.stdout:
                if not S.scan_active: break
                S.scan_log.append(line)
                self.after(0, lambda l=line: self._console_write(l))
                if "LADO run complete" in line and not self._success_fired:
                    self._success_fired = True
                    self.after(0, self._scan_ok)
                    return
        except Exception as e:
            if S.scan_active and not self._success_fired:
                self.after(0, lambda: self._scan_err(str(e)))

    def _scan_ok(self):
        S.scan_active = False
        self._reset_btn()
        self._status_dot.configure(fg_color=TEAL)
        self._status_lbl.configure(text="done", text_color=TEAL)
        msg = "\nScan complete ✓  Refreshing stats...\n"
        S.scan_log.append(msg)
        self._console_write(msg)
        threading.Thread(target=self._bg_stats_after_scan, daemon=True).start()

    def _scan_err(self, code):
        S.scan_active = False; S.scan_proc = None
        self._reset_btn()
        self._status_dot.configure(fg_color=RED)
        self._status_lbl.configure(text="error", text_color=RED)
        self._pill_lbl.configure(text="● Error", text_color=RED)
        msg = f"\nScan error: {code}\n"
        S.scan_log.append(msg)
        self._console_write(msg)

    def _reset_btn(self):
        if self.winfo_exists():
            self._scan_btn.configure(text="⟳  Run Scan",
                fg_color=PURPLE, hover_color="#5c2dff")

    def _bg_stats_after_scan(self):
        time.sleep(0.5)
        s = fetch()
        S.last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.after(0, lambda: self._apply_stats(s, S.last_scan_time))

    def _bg_stats(self):
        s = fetch()
        self.after(0, lambda: self._apply_stats(s, None))

    def _apply_stats(self, s, scan_time=None):
        if not self.winfo_exists(): return
        self._cards["TOTAL FILES"].update(s["files"])
        self._cards["STORAGE USED"].update(f"{s['size']} GB")
        self._cards["DUPLICATES"].update(s["dupes"])
        self._cards["PENDING"].update(s["pending"])
        if scan_time:
            self._scan_lbl.configure(text=scan_time)
            self._pill_lbl.configure(text="● Up to date", text_color=TEAL)
            msg = f" Done — {s['files']} files, {s['dupes']} dupes, {s['pending']} pending.\n"
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
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")