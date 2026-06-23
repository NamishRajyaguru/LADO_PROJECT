import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
from ui.theme import *

try:
    from core.reinforcement import record_feedback
    REINFORCEMENT = True
except: REINFORCEMENT = False

try:
    from core.action_engine import execute_approved_suggestions
    from core.logger import setup_logger
    ACTION_ENGINE = True
except: ACTION_ENGINE = False

try:
    from ui.watcher import _notify_all
    NOTIFY_AVAILABLE = True
except: NOTIFY_AVAILABLE = False

RISK_CLR = {"low": TEAL, "medium": AMBER, "high": PINK, "critical": RED}
RISK_DIM = {"low": TEAL_DIM, "medium": AMBER_DIM, "high": PINK_DIM, "critical": RED_DIM}
TABS = ["Pending", "Approved", "Rejected", "All"]
PAGE = 20

_cache = {"pending": None, "approved": None, "rejected": None, "all": None}


def get(status="pending"):
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        if status != "all":
            c.execute("""SELECT id,file_path,action,reason,confidence,risk,status
                        FROM suggestions WHERE status=?
                        ORDER BY confidence DESC""", (status,))
        else:
            c.execute("""SELECT id,file_path,action,reason,confidence,risk,status
                        FROM suggestions ORDER BY confidence DESC""")
        return c.fetchall()
    except: return []

def get_total(status):
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        if status != "all":
            c.execute("SELECT COUNT(*) FROM suggestions WHERE status=?", (status,))
        else:
            c.execute("SELECT COUNT(*) FROM suggestions")
        return c.fetchone()[0]
    except: return 0

def update(sid, st):
    try:
        c = sqlite3.connect(DB_PATH)
        c.cursor().execute("UPDATE suggestions SET status=? WHERE id=?", (st, sid))
        c.commit()
    except: pass


class SkeletonCard(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=GLASS_BG,
                         border_color=GLASS_BORDER, border_width=1,
                         corner_radius=14, **kw)
        self._phase = 0; self._bars = []
        p = ctk.CTkFrame(self, fg_color="transparent")
        p.pack(fill="x", padx=20, pady=(18, 0))
        for w, anch in [(200, "w"), (120, "w"), (320, "w")]:
            b = ctk.CTkFrame(p, fg_color=SK2, corner_radius=4, width=w, height=9)
            b.pack(anchor=anch, pady=5)
            b.pack_propagate(False)
            self._bars.append(b)
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=20, pady=(8, 16))
        for w in [150, 80, 72]:
            b = ctk.CTkFrame(bot, fg_color=SK2, corner_radius=6, width=w, height=24)
            b.pack(side="left" if w == 150 else "right", padx=(0, 6))
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


class SRow(ctk.CTkFrame):
    def __init__(self, parent, data, reload_cb, **kw):
        super().__init__(parent, fg_color=GLASS_BG,
                         border_color=GLASS_BORDER, border_width=1,
                         corner_radius=14, **kw)
        sid, fp, action, reason, conf, risk, status = data
        conf = float(conf or 0)
        risk_key = (risk or "low").lower()
        rc = RISK_CLR.get(risk_key, TEAL)
        rd = RISK_DIM.get(risk_key, TEAL_DIM)
        fname = os.path.basename(fp) if fp else "unknown"

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=(16, 0))

        # Row 1 — filename + badges
        r1 = ctk.CTkFrame(body, fg_color="transparent")
        r1.pack(fill="x")
        ctk.CTkLabel(r1, text=fname,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            text_color=TEXT).pack(side="left")

        # Status badge
        st_color = {"pending": AMBER, "approved": TEAL, "rejected": PINK}.get(status, TEXT_DIM)
        st_dim   = {"pending": AMBER_DIM, "approved": TEAL_DIM, "rejected": PINK_DIM}.get(status, GLASS_BG)
        st_badge = ctk.CTkFrame(r1, fg_color=st_dim, corner_radius=6)
        st_badge.pack(side="right", padx=(6, 0))
        ctk.CTkLabel(st_badge, text=f"  {status.upper()}  ",
            font=ctk.CTkFont(family=FONT_SANS, size=8, weight="bold"),
            text_color=st_color).pack(padx=2, pady=3)

        # Risk badge
        risk_badge = ctk.CTkFrame(r1, fg_color=rd, corner_radius=6)
        risk_badge.pack(side="right")
        ctk.CTkLabel(risk_badge, text=f"  {risk_key.upper()}  ",
            font=ctk.CTkFont(family=FONT_SANS, size=8, weight="bold"),
            text_color=rc).pack(padx=2, pady=3)

        # Row 2 — action
        r2 = ctk.CTkFrame(body, fg_color="transparent")
        r2.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(r2, text=f"→  {action}",
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
            text_color=PURPLE).pack(side="left")

        # Reason
        if reason:
            ctk.CTkLabel(body, text=reason,
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color=TEXT_MUTED, anchor="w", wraplength=680).pack(
                fill="x", pady=(4, 0))

        # Bottom row — confidence bar + buttons
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=20, pady=(12, 16))

        ctk.CTkLabel(bot, text=f"{int(conf * 100)}%",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEXT_DIM, width=34).pack(side="left")

        track = ctk.CTkFrame(bot, fg_color=GLASS_BG2,
                             width=160, height=5, corner_radius=3)
        track.pack(side="left", padx=(6, 16))
        track.pack_propagate(False)
        fill_w = max(4, int(160 * conf))
        ctk.CTkFrame(track, fg_color=PURPLE,
                     width=fill_w, height=5,
                     corner_radius=3).place(x=0, y=0)

        if status == "pending":
            ctk.CTkButton(bot, text="Approve", width=90, height=30,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                fg_color=TEAL_DIM, hover_color=TEAL_BORDER,
                text_color=TEAL, border_color=TEAL_BORDER, border_width=1,
                corner_radius=8,
                command=lambda: self._approve(sid, reload_cb)).pack(side="right", padx=(6, 0))
            ctk.CTkButton(bot, text="Reject", width=80, height=30,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                fg_color=PINK_DIM, hover_color=RED_DIM,
                text_color=PINK, border_color=PINK_DIM, border_width=1,
                corner_radius=8,
                command=lambda: self._reject(sid, reload_cb)).pack(side="right")

    def _approve(self, sid, reload_cb):
        update(sid, "approved")
        if REINFORCEMENT:
            try:
                c = sqlite3.connect(DB_PATH).cursor()
                c.execute("SELECT rule_id, file_path FROM suggestions WHERE id=?", (sid,))
                row = c.fetchone()
                if row: record_feedback(row[0], "approved", row[1])
            except Exception as e: print(f"[Reinforcement] {e}")
        if ACTION_ENGINE:
            threading.Thread(
                target=lambda: self._run_engine_then_reload(reload_cb),
                daemon=True).start()
        else:
            self._bust(); reload_cb()

    def _run_engine_then_reload(self, reload_cb):
        try: execute_approved_suggestions(setup_logger())
        except Exception as e: print(f"[Action Engine] {e}")
        self._bust()
        self.after(0, reload_cb)
        if NOTIFY_AVAILABLE:
            try: _notify_all()
            except Exception as e: print(f"[Notify] {e}")

    def _reject(self, sid, reload_cb):
        update(sid, "rejected")
        if REINFORCEMENT:
            try:
                c = sqlite3.connect(DB_PATH).cursor()
                c.execute("SELECT rule_id, file_path FROM suggestions WHERE id=?", (sid,))
                row = c.fetchone()
                if row: record_feedback(row[0], "rejected", row[1])
            except Exception as e: print(f"[Reinforcement] {e}")
        self._bust(); reload_cb()

    def _bust(self):
        global _cache
        _cache = {"pending": None, "approved": None, "rejected": None, "all": None}


class SuggestionsPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_DARK, **kw)
        self._filter = "pending"
        self._all_rows = []
        self._shown = 0
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 0))
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Suggestions",
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Review LADO's recommendations and take action",
            font=ctk.CTkFont(family=FONT_SANS, size=11),
            text_color=TEXT_DIM).pack(anchor="w", pady=(2, 0))

        # Action engine badge
        badge = ctk.CTkFrame(hdr,
            fg_color=TEAL_DIM if ACTION_ENGINE else AMBER_DIM,
            corner_radius=20)
        badge.pack(side="right")
        ctk.CTkLabel(badge,
            text="⚡ Action engine connected" if ACTION_ENGINE else "⚠ Action engine offline",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=TEAL if ACTION_ENGINE else AMBER).pack(padx=12, pady=5)

        # Tabs
        tabs = ctk.CTkFrame(self, fg_color=GLASS_BG,
                            border_color=GLASS_BORDER, border_width=1,
                            corner_radius=14)
        tabs.pack(fill="x", padx=32, pady=(20, 0))
        self._tbns = {}
        for t in TABS:
            active = t == "Pending"
            b = ctk.CTkButton(tabs, text=t, width=100, height=34,
                font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
                fg_color=PURPLE if active else "transparent",
                text_color=TEXT if active else TEXT_DIM,
                hover_color=GLASS_BG2, corner_radius=10,
                command=lambda x=t: self._tab(x))
            b.pack(side="left", padx=6, pady=6)
            self._tbns[t] = b

        self._cnt = ctk.CTkLabel(self, text="",
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            text_color=TEXT_DIM)
        self._cnt.pack(anchor="w", padx=32, pady=(12, 0))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=GLASS_BG2,
            scrollbar_button_hover_color=GLASS_BORDER2)
        self._scroll.pack(fill="both", expand=True, padx=32, pady=(8, 0))

        self._load_more_btn = ctk.CTkButton(self, text="Load 20 more ↓",
            width=160, height=30,
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            fg_color=GLASS_BG2, hover_color=GLASS_BORDER,
            text_color=TEXT_DIM, corner_radius=8,
            command=self._load_more)

        self._load()

    def _tab(self, t):
        self._filter = t.lower()
        for k, b in self._tbns.items():
            b.configure(fg_color=PURPLE if k == t else "transparent",
                        text_color=TEXT if k == t else TEXT_DIM)
        self._load()

    def _load(self):
        global _cache
        f = self._filter
        self._load_more_btn.pack_forget()
        if _cache[f] is not None:
            self._all_rows = _cache[f]
            self._shown = 0
            self._render_from_cache()
            return
        self._show_skeletons()
        threading.Thread(target=lambda: self._bg(f), daemon=True).start()

    def _show_skeletons(self):
        for w in self._scroll.winfo_children(): w.destroy()
        for _ in range(4):
            SkeletonCard(self._scroll).pack(fill="x", pady=5)

    def _bg(self, f):
        rows = get(f); total = get_total(f)
        self.after(0, lambda: self._render_fresh(rows, total))

    def _render_fresh(self, rows, total):
        global _cache
        if not self.winfo_exists(): return
        _cache[self._filter] = rows
        self._all_rows = rows
        self._shown = 0
        for w in self._scroll.winfo_children(): w.destroy()
        self._cnt.configure(text=f"{len(rows)} total  ·  highest confidence first")
        if not rows:
            ctk.CTkLabel(self._scroll, text="Nothing here.",
                font=ctk.CTkFont(family=FONT_SANS, size=13),
                text_color=TEXT_DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_from_cache(self):
        for w in self._scroll.winfo_children(): w.destroy()
        self._cnt.configure(text=f"{len(self._all_rows)} total  ·  highest confidence first")
        if not self._all_rows:
            ctk.CTkLabel(self._scroll, text="Nothing here.",
                font=ctk.CTkFont(family=FONT_SANS, size=13),
                text_color=TEXT_DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_next_page(self):
        start = self._shown
        end = min(start + PAGE, len(self._all_rows))
        for i in range(start, end):
            SRow(self._scroll, self._all_rows[i], self._load).pack(
                fill="x", pady=5)
        self._shown = end
        if self._shown < len(self._all_rows):
            remaining = len(self._all_rows) - self._shown
            self._load_more_btn.configure(
                text=f"Load 20 more  ·  {remaining} remaining ↓")
            self._load_more_btn.pack(pady=(6, 20))
        else:
            self._load_more_btn.pack_forget()

    def _load_more(self):
        self._render_next_page()