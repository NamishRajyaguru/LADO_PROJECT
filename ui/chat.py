import customtkinter as ctk, threading, sqlite3, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ui._state as S
from ui.theme import *

try: from core.llm import ask_llm, reset_conversation; LLM = True
except: LLM = False
try: from config import LOG_DIR, DB_PATH
except: LOG_DIR = None; DB_PATH = None

try:
    from core.action_engine import execute_approved_suggestions
    from core.logger import setup_logger
    ACTIONS_AVAILABLE = True
except: ACTIONS_AVAILABLE = False

try:
    from core.agent import run_full_cycle
    SCAN_AVAILABLE = True
except: SCAN_AVAILABLE = False

ACTION_KEYWORDS = {
    "scan": ["run a scan","scan my files","start scan","rescan","run scan","do a scan"],
    "approve_all": ["approve all","approve all duplicates","approve all suggestions",
                    "execute suggestions","clean duplicates","archive duplicates"],
    "archive_largest": ["archive the largest file","archive largest",
                        "move the largest file","archive biggest file"],
    "quarantine_duplicates": ["quarantine duplicates","quarantine all duplicates",
                              "move duplicates to quarantine","quarantine it",
                              "quarantine them","quarantine the duplicates",
                              "quarantine the file","quarantine files"],
    "show_largest": ["what is the largest file","which is the largest file",
                     "show largest files","biggest files","largest files"],
    "show_duplicates": ["show duplicates","list duplicates","how many duplicates",
                        "what are the duplicates"],
}

def detect_action(msg):
    msg_lower = msg.lower().strip()
    for action, phrases in ACTION_KEYWORDS.items():
        for phrase in phrases:
            if phrase in msg_lower:
                return action
    return None

def execute_action(action, msg=""):
    if action == "scan":
        if not SCAN_AVAILABLE:
            return "ACTION_RESULT: Scan backend not available."
        try:
            run_full_cycle()
            return "ACTION_RESULT: Full scan completed. Files re-indexed and suggestions regenerated."
        except Exception as e:
            return f"ACTION_RESULT: Scan failed: {e}"

    elif action == "approve_all":
        if not ACTIONS_AVAILABLE:
            return "ACTION_RESULT: Action engine not available."
        try:
            execute_approved_suggestions(setup_logger())
            return "ACTION_RESULT: All approved suggestions executed. Files moved to archive or quarantine."
        except Exception as e:
            return f"ACTION_RESULT: Failed: {e}"

    elif action == "archive_largest":
        if not ACTIONS_AVAILABLE:
            return "ACTION_RESULT: Action engine not available."
        try:
            c = sqlite3.connect(DB_PATH).cursor()
            c.execute("""SELECT path, name, size_mb FROM files
                WHERE extension NOT IN ('.exe','.dll','.sys','.iso','.msi')
                ORDER BY size_mb DESC LIMIT 1""")
            row = c.fetchone()
            if not row:
                return "ACTION_RESULT: No suitable file found to archive."
            path, name, size_mb = row
            logger = setup_logger()
            from core.action_engine import archive_file, log_action
            from core.database import get_connection
            success = archive_file(path, logger)
            if success:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM files WHERE path = ?", (path,))
                conn.commit(); conn.close()
                log_action(path, "suggest_archive", approved_by="user_chat")
                return f"ACTION_RESULT: Archived '{name}' ({size_mb:.1f} MB). Moved to archive folder."
            else:
                return f"ACTION_RESULT: Failed to archive '{name}'. File may not exist."
        except Exception as e:
            return f"ACTION_RESULT: Error: {e}"

    elif action == "quarantine_duplicates":
        if not ACTIONS_AVAILABLE:
            return "ACTION_RESULT: Action engine not available."
        # Pronoun check — target specific file if context exists
        if S.last_mentioned_file and any(w in msg.lower() for w in ["it","that","the file"]):
            try:
                from core.action_engine import quarantine_file, log_action
                from core.database import get_connection
                c = sqlite3.connect(DB_PATH).cursor()
                c.execute("SELECT name, size_mb FROM files WHERE path=?", (S.last_mentioned_file,))
                row = c.fetchone()
                if row:
                    logger = setup_logger()
                    success = quarantine_file(S.last_mentioned_file, logger)
                    if success:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM files WHERE path=?", (S.last_mentioned_file,))
                        conn.commit(); conn.close()
                        log_action(S.last_mentioned_file, "suggest_cleanup", approved_by="user_chat")
                        S.last_mentioned_file = None
                        return f"ACTION_RESULT: Quarantined '{row[0]}' ({row[1]:.1f} MB). Moved to quarantine."
            except Exception as e:
                return f"ACTION_RESULT: Error targeting file: {e}"
        # Fall through — quarantine all duplicates
        try:
            from core.action_engine import quarantine_file, log_action
            from core.database import get_connection
            c = sqlite3.connect(DB_PATH).cursor()
            c.execute("""SELECT path, name, size_mb, hash FROM files
                WHERE hash IS NOT NULL AND hash != '' AND size_mb > 10
                ORDER BY hash, modified_time DESC""")
            rows = c.fetchall()
            seen_hashes = set()
            to_quarantine = []
            for path, name, size_mb, hash_ in rows:
                if hash_ in seen_hashes:
                    to_quarantine.append((path, name, size_mb))
                else:
                    seen_hashes.add(hash_)
            if not to_quarantine:
                return "ACTION_RESULT: No duplicate files over 10MB found."
            logger = setup_logger()
            moved = 0
            for path, name, size_mb in to_quarantine:
                if quarantine_file(path, logger):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM files WHERE path = ?", (path,))
                    conn.commit(); conn.close()
                    log_action(path, "suggest_cleanup", approved_by="user_chat")
                    moved += 1
            total_mb = round(sum(s for _, _, s in to_quarantine[:moved]), 2)
            return f"ACTION_RESULT: Quarantined {moved} duplicate files. Freed approximately {total_mb} MB."
        except Exception as e:
            return f"ACTION_RESULT: Error: {e}"

    elif action in ("show_largest", "show_duplicates"):
        return None  # let LLM answer from db summary

    return "ACTION_RESULT: Unknown action."


def get_logs():
    if not LOG_DIR: return "No log directory configured."
    try:
        f = os.path.join(LOG_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")
        return "".join(open(f).readlines()[-30:])
    except: return "No log file for today."


def get_db_summary():
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); total = c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); size = round((c.fetchone()[0] or 0) / 1024, 2)
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pending = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf = c.fetchone()[0]
        c.execute("SELECT extension,COUNT(*) cnt FROM files GROUP BY extension ORDER BY cnt DESC LIMIT 8")
        ext = ", ".join([f"{r[0]}({r[1]})" for r in c.fetchall()])
        c.execute("SELECT name,size_mb,path FROM files ORDER BY size_mb DESC LIMIT 5")
        big = "\n".join([f"  - {r[0]} ({float(r[1] or 0):.1f} MB) at {r[2]}" for r in c.fetchall()])
        try:
            from core.reinforcement import get_feedback_summary
            feedback = get_feedback_summary()
            feedback_lines = ""
            if feedback:
                feedback_lines = "\n".join([
                    f"  {r[0]}: {r[1]} approvals, {r[2]} rejections, multiplier={r[3]:.2f}"
                    for r in feedback
                ])
        except: feedback_lines = ""
        return (f"Total: {total} files | {size} GB | {hf - uh} dupes | {pending} pending\n"
                f"Types: {ext}\nLargest:\n{big}\nRule Learning:\n{feedback_lines}")
    except Exception as e: return f"DB unavailable: {e}"


def fetch_stats():
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); tf = c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); sz = round((c.fetchone()[0] or 0) / 1024, 2)
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pend = c.fetchone()[0]
        return {"files": tf, "size": sz, "dupes": hf - uh, "pending": pend}
    except: return {"files": 0, "size": 0.0, "dupes": 0, "pending": 0}


def fetch_recent_actions(limit=6):
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("""SELECT file_path, action, timestamp FROM actions_log
                     ORDER BY timestamp DESC LIMIT ?""", (limit,))
        return c.fetchall()
    except: return []


def query(msg, action_result=None):
    if not LLM: return "LLM not connected — add your Groq API key to config.py."
    try:
        action_ctx = f"\n\nACTION JUST TAKEN:\n{action_result}" if action_result else ""
        prompt = f"""You are LADO, a Local Autonomous Digital Operator running on the user's Windows PC.
You help users understand what is happening on their computer.
You explain file management decisions in plain, friendly English.
Keep responses concise — 2 to 4 sentences maximum.

CRITICAL RULES — never break these:
- You CANNOT move, archive, delete, or modify any files through conversation.
- Never claim you performed a file action unless an ACTION JUST TAKEN block is present.
- If asked to archive, move, or delete something specific, tell the user to use the Suggestions panel
  or type a valid command like 'quarantine duplicates' or 'archive the largest file'.
- Only report actions as done when ACTION JUST TAKEN confirms it happened.

FILE SYSTEM:
{get_db_summary()}

RECENT LOG:
{get_logs()}{action_ctx}

Respond naturally. For casual messages be friendly. For file questions use the data above.
If an ACTION JUST TAKEN is provided, confirm what was done in plain English.

User: {msg}"""
        return ask_llm(prompt)
    except Exception as e: return f"Error: {e}"


def update_last_mentioned_file(response_text):
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT name, path FROM files ORDER BY size_mb DESC LIMIT 20")
        for name, path in c.fetchall():
            if name in response_text:
                S.last_mentioned_file = path
                return
    except: pass


# ── Widgets ───────────────────────────────────────────────────────

class GlassFrame(ctk.CTkFrame):
    """Reusable glass card."""
    def __init__(self, parent, **kw):
        kw.setdefault("corner_radius", 16)
        super().__init__(parent,
            fg_color=GLASS_BG,
            border_color=GLASS_BORDER,
            border_width=1,
            **kw)


class StatPill(ctk.CTkFrame):
    def __init__(self, parent, text, bg, color, **kw):
        super().__init__(parent, fg_color=bg, corner_radius=20, **kw)
        ctk.CTkLabel(self, text=text,
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=color).pack(padx=12, pady=5)

    def update_text(self, text):
        for child in self.winfo_children():
            child.configure(text=text)


class Bubble(ctk.CTkFrame):
    def __init__(self, parent, text, role, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        is_user = role == "user"
        side = "e" if is_user else "w"

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(anchor=side, fill="x", padx=8)

        name_color = TEXT_DIM
        ctk.CTkLabel(wrap, text="you" if is_user else "lado",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=name_color).pack(anchor=side, padx=16, pady=(8, 0))

        if is_user:
            bub = ctk.CTkFrame(wrap, fg_color=PURPLE_DIM,
                               border_color=PURPLE_BORDER, border_width=1,
                               corner_radius=16)
        else:
            bub = ctk.CTkFrame(wrap, fg_color=GLASS_BG,
                               border_color=GLASS_BORDER, border_width=1,
                               corner_radius=16)

        bub.pack(anchor=side, padx=10, pady=(4, 10))
        ctk.CTkLabel(bub, text=text,
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            text_color=TEXT if is_user else TEXT_MUTED,
            wraplength=520, justify="left", anchor="w").pack(padx=16, pady=12)


class ActionBubble(ctk.CTkFrame):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        pill = ctk.CTkFrame(self, fg_color=TEAL_DIM,
                            border_color=TEAL_BORDER, border_width=1,
                            corner_radius=10)
        pill.pack(anchor="w", padx=24, pady=(2, 2))
        ctk.CTkLabel(pill, text=f"⚡  {text}",
            font=ctk.CTkFont(family=FONT_SANS, size=10, weight="bold"),
            text_color=TEAL).pack(padx=14, pady=7)


class ActivityRow(ctk.CTkFrame):
    def __init__(self, parent, fp, action, ts, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        dot_color = TEAL if "cleanup" in action else (PURPLE if "archive" in action else AMBER)
        dot = ctk.CTkFrame(self, fg_color=dot_color,
                           width=6, height=6, corner_radius=3)
        dot.pack(side="left", padx=(0, 8), pady=6)
        dot.pack_propagate(False)
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True)
        fname = os.path.basename(fp)[:28] if fp else "unknown"
        ctk.CTkLabel(right, text=fname,
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            text_color=TEXT_MUTED, anchor="w").pack(anchor="w")
        try:
            dt = datetime.fromisoformat(ts)
            ago = datetime.now() - dt
            mins = int(ago.total_seconds() // 60)
            time_str = f"{mins}m ago" if mins < 60 else f"{mins//60}h ago"
        except: time_str = "recently"
        ctk.CTkLabel(right, text=time_str,
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIM, anchor="w").pack(anchor="w")


# ── Main panel ────────────────────────────────────────────────────

class ChatPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_DARK, **kw)
        self._stats = {}
        self._pill_refs = {}
        self._build()
        threading.Thread(target=self._load_stats, daemon=True).start()

    def _load_stats(self):
        s = fetch_stats()
        self.after(0, lambda: self._update_pills(s))

    def _update_pills(self, s):
        if not self.winfo_exists(): return
        mapping = {
            "files":   f"  {s['files']:,} files indexed  ",
            "pending": f"  {s['pending']} suggestions  ",
            "dupes":   f"  {s['dupes']:,} duplicates  ",
            "size":    f"  {s['size']} GB scanned  ",
        }
        for key, text in mapping.items():
            if key in self._pill_refs:
                self._pill_refs[key].update_text(text)

    def _build(self):
        # ── Three-column layout ───────────────────────────────────
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # Left spacer (breathing room)
        ctk.CTkFrame(outer, fg_color="transparent", width=12).pack(side="left", fill="y")

        # ── Center: main chat ─────────────────────────────────────
        center = ctk.CTkFrame(outer, fg_color="transparent")
        center.pack(side="left", fill="both", expand=True)

        # Agent identity header
        hdr = ctk.CTkFrame(center, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(24, 0))

        ctk.CTkLabel(hdr,
            text="LADO  ·  LOCAL AUTONOMOUS DIGITAL OPERATOR",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=TEXT_DIM).pack(anchor="w")

        ctk.CTkLabel(hdr,
            text="What would you like me to do?",
            font=ctk.CTkFont(family=FONT_SANS, size=20, weight="bold"),
            text_color=TEXT).pack(anchor="w", pady=(4, 0))

        # Status pills row
        pills_frame = ctk.CTkFrame(center, fg_color="transparent")
        pills_frame.pack(fill="x", padx=24, pady=(12, 0))

        pill_defs = [
            ("files",   "  loading...  ",  PURPLE_DIM,  PURPLE),
            ("pending", "  loading...  ",  TEAL_DIM,    TEAL),
            ("dupes",   "  loading...  ",  PINK_DIM,    PINK),
            ("size",    "  loading...  ",  AMBER_DIM,   AMBER),
        ]
        for key, text, bg, color in pill_defs:
            p = StatPill(pills_frame, text, bg, color)
            p.pack(side="left", padx=(0, 8))
            self._pill_refs[key] = p

        # Separator
        ctk.CTkFrame(center, fg_color=GLASS_BORDER, height=1).pack(
            fill="x", padx=24, pady=(16, 0))

        # Chat scroll area
        self._scroll = ctk.CTkScrollableFrame(
            center,
            fg_color="transparent",
            scrollbar_button_color=GLASS_BG2,
            scrollbar_button_hover_color=GLASS_BORDER2,
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        # Restore or show welcome
        if S.chat_messages:
            for role, text in S.chat_messages:
                Bubble(self._scroll, text, role).pack(fill="x")
        else:
            welcome = ("Hey, I'm LADO. I've finished scanning your system and I'm ready. "
                       "Ask me anything, or give me a command — I can archive files, "
                       "quarantine duplicates, run a scan, and more.")
            S.chat_messages.append(("assistant", welcome))
            Bubble(self._scroll, welcome, "assistant").pack(fill="x")

        # Hint strip
        hint = ctk.CTkFrame(center, fg_color=GLASS_BG, corner_radius=10)
        hint.pack(fill="x", padx=24, pady=(8, 0))
        ctk.CTkLabel(hint,
            text="Commands:  'run a scan'  ·  'archive the largest file'  ·  'quarantine duplicates'  ·  'quarantine it'",
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIM).pack(padx=16, pady=7)

        # Input row
        inp_frame = GlassFrame(center, corner_radius=14)
        inp_frame.pack(fill="x", padx=24, pady=(8, 24))

        self._inp = ctk.CTkEntry(
            inp_frame,
            placeholder_text="Ask LADO anything or give a command…",
            font=ctk.CTkFont(family=FONT_SANS, size=12),
            height=46,
            fg_color="transparent",
            border_width=0,
            text_color=TEXT,
            placeholder_text_color=TEXT_DIM,
        )
        self._inp.pack(side="left", fill="x", expand=True, padx=16, pady=6)
        self._inp.bind("<Return>", lambda e: self._send())

        self._sbtn = ctk.CTkButton(
            inp_frame,
            text="Send",
            width=80, height=36,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            fg_color=PURPLE,
            hover_color=PURPLE_HOVER,
            text_color=TEXT,
            corner_radius=10,
            command=self._send,
        )
        self._sbtn.pack(side="right", padx=10)

        # ── Right panel: status + activity ───────────────────────
        right = GlassFrame(outer, width=220)
        right.pack(side="right", fill="y", padx=(8, 16), pady=20)
        right.pack_propagate(False)

        right_inner = ctk.CTkFrame(right, fg_color="transparent")
        right_inner.pack(fill="both", expand=True, padx=14, pady=16)

        # Online status
        online_pill = ctk.CTkFrame(right_inner,
            fg_color=TEAL_DIM if LLM else AMBER_DIM, corner_radius=20)
        online_pill.pack(anchor="w", pady=(0, 16))
        ctk.CTkLabel(online_pill,
            text=f"● {'online' if LLM else 'offline'}",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=TEAL if LLM else AMBER).pack(padx=12, pady=5)

        # Clear button
        ctk.CTkButton(right_inner, text="Clear chat",
            width=120, height=30,
            font=ctk.CTkFont(family=FONT_SANS, size=10),
            fg_color=GLASS_BG2, hover_color=GLASS_BORDER,
            text_color=TEXT_MUTED, corner_radius=8,
            command=self._clear).pack(anchor="w", pady=(0, 20))

        # Separator
        ctk.CTkFrame(right_inner, fg_color=GLASS_BORDER, height=1).pack(
            fill="x", pady=(0, 14))

        # Recent actions label
        ctk.CTkLabel(right_inner, text="RECENT ACTIONS",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=TEXT_DIM).pack(anchor="w", pady=(0, 8))

        self._activity_frame = ctk.CTkFrame(right_inner, fg_color="transparent")
        self._activity_frame.pack(fill="x")
        self._load_activity()

    def _load_activity(self):
        for w in self._activity_frame.winfo_children():
            w.destroy()
        actions = fetch_recent_actions(6)
        if not actions:
            ctk.CTkLabel(self._activity_frame,
                text="No actions yet.",
                font=ctk.CTkFont(family=FONT_SANS, size=10),
                text_color=TEXT_DIM).pack(anchor="w")
        else:
            for fp, action, ts in actions:
                ActivityRow(self._activity_frame, fp, action, ts).pack(
                    fill="x", pady=2)

    def _send(self):
        msg = self._inp.get().strip()
        if not msg: return
        self._inp.delete(0, "end")
        self._sbtn.configure(state="disabled", text="…")

        S.chat_messages.append(("user", msg))
        Bubble(self._scroll, msg, "user").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)

        action = detect_action(msg)
        thinking = ctk.CTkLabel(self._scroll,
            text="executing…" if action else "thinking…",
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIM)
        thinking.pack(anchor="w", padx=24, pady=4)
        self._scroll._parent_canvas.yview_moveto(1.0)

        threading.Thread(
            target=lambda: self._work(msg, action, thinking),
            daemon=True,
        ).start()

    def _work(self, msg, action, thinking):
        action_result = None
        if action:
            action_result = execute_action(action, msg)
            if action_result and "ACTION_RESULT" in action_result:
                friendly = {
                    "scan":                  "Running a full scan…",
                    "approve_all":           "Executing approved suggestions…",
                    "archive_largest":       "Archiving largest file…",
                    "quarantine_duplicates": "Moving duplicate files to quarantine…",
                }.get(action, "Running action…")
                self.after(0, lambda: ActionBubble(self._scroll, friendly).pack(fill="x"))

        r = query(msg, action_result)
        self.after(0, lambda: self._reply(r, thinking))

    def _reply(self, text, thinking):
        thinking.destroy()
        update_last_mentioned_file(text)
        S.chat_messages.append(("assistant", text))
        Bubble(self._scroll, text, "assistant").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        self._sbtn.configure(state="normal", text="Send")
        # Refresh pills and activity after any response
        threading.Thread(target=self._load_stats, daemon=True).start()
        self.after(500, self._load_activity)

    def _clear(self):
        if LLM:
            try: reset_conversation()
            except: pass
        S.chat_messages = []
        for w in self._scroll.winfo_children():
            w.destroy()
        welcome = "Cleared. What do you need?"
        S.chat_messages.append(("assistant", welcome))
        Bubble(self._scroll, welcome, "assistant").pack(fill="x")