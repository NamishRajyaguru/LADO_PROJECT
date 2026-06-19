import customtkinter as ctk, threading, sqlite3, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ui._state as S

try: from core.llm import ask_llm, reset_conversation; LLM=True
except: LLM=False
try: from config import LOG_DIR, DB_PATH
except: LOG_DIR=None; DB_PATH=None

try:
    from core.action_engine import execute_approved_suggestions
    from core.logger import setup_logger
    ACTIONS_AVAILABLE = True
except:
    ACTIONS_AVAILABLE = False

try:
    from core.agent import run_full_cycle
    SCAN_AVAILABLE = True
except:
    SCAN_AVAILABLE = False

BG="#FFFFFF";SURFACE="#F7F7F8";CARD="#F7F7F8";CARD2="#F1F1F3"
BORDER="#E6E6E9";BORDER_HI="#D1D1D6"
TEXT="#000000";MUTED="#8A8F98";DIM="#C4C5C8"
ACCENT="#000000";ACCENTG="#16A34A"

ACTION_KEYWORDS = {
    "scan": [
        "run a scan", "scan my files", "start scan",
        "rescan", "run scan", "do a scan"
    ],
    "approve_all": [
        "approve all", "approve all duplicates", "approve all suggestions",
        "execute suggestions", "clean duplicates", "archive duplicates"
    ],
    "archive_largest": [
        "archive the largest file", "archive largest",
        "move the largest file", "archive biggest file"
    ],
    "quarantine_duplicates": [
        "quarantine duplicates", "quarantine all duplicates",
        "move duplicates to quarantine", "quarantine it",
        "quarantine them", "quarantine the duplicates",
        "quarantine the file", "quarantine files",
    ],
    "show_largest": [
        "what is the largest file", "which is the largest file",
        "show largest files", "biggest files", "largest files"
    ],
    "show_duplicates": [
        "show duplicates", "list duplicates", "how many duplicates",
        "what are the duplicates"
    ],
}

def detect_action(msg):
    msg_lower = msg.lower().strip()
    for action, phrases in ACTION_KEYWORDS.items():
        for phrase in phrases:
            if phrase in msg_lower:
                return action
    return None

def execute_action(action):

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
            import sqlite3
            c = sqlite3.connect(DB_PATH).cursor()
            c.execute("""
                SELECT path, name, size_mb FROM files
                WHERE extension NOT IN ('.exe','.dll','.sys','.iso','.msi')
                ORDER BY size_mb DESC LIMIT 1
            """)
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
                conn.commit()
                conn.close()
                log_action(path, "suggest_archive", approved_by="user_chat")
                return f"ACTION_RESULT: Archived '{name}' ({size_mb} MB). File moved to LADO/archive/."
            else:
                return f"ACTION_RESULT: Failed to archive '{name}'. File may not exist."
        except Exception as e:
            return f"ACTION_RESULT: Error: {e}"

    elif action == "quarantine_duplicates":
        if not ACTIONS_AVAILABLE:
            return "ACTION_RESULT: Action engine not available."
        try:
            import sqlite3
            from core.action_engine import quarantine_file, log_action
            from core.database import get_connection
            c = sqlite3.connect(DB_PATH).cursor()
            # Get all duplicate files over 10MB — keep one copy per hash
            c.execute("""
                SELECT path, name, size_mb, hash FROM files
                WHERE hash IS NOT NULL AND hash != ''
                AND size_mb > 10
                ORDER BY hash, modified_time DESC
            """)
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
                    conn.commit()
                    conn.close()
                    log_action(path, "suggest_cleanup", approved_by="user_chat")
                    moved += 1
            total_mb = round(sum(s for _, _, s in to_quarantine[:moved]), 2)
            return f"ACTION_RESULT: Quarantined {moved} duplicate files. Freed approximately {total_mb} MB."
        except Exception as e:
            return f"ACTION_RESULT: Error: {e}"

    elif action == "show_largest":
        # This is informational — no file action, just query DB
        return None   # let LLM answer from db summary

    elif action == "show_duplicates":
        return None   # let LLM answer from db summary

    return "ACTION_RESULT: Unknown action."

def get_logs():
    if not LOG_DIR: return "No log directory configured."
    try:
        f=os.path.join(LOG_DIR,datetime.now().strftime("%Y-%m-%d")+".log")
        return "".join(open(f).readlines()[-30:])
    except: return "No log file for today."

def get_db_summary():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT COUNT(*) FROM files"); total=c.fetchone()[0]
        c.execute("SELECT SUM(size_mb) FROM files"); size=round((c.fetchone()[0] or 0)/1024,2)
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'"); pending=c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT hash) FROM files WHERE hash!='' AND hash IS NOT NULL"); uh=c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM files WHERE hash!='' AND hash IS NOT NULL"); hf=c.fetchone()[0]
        c.execute("SELECT extension,COUNT(*) cnt FROM files GROUP BY extension ORDER BY cnt DESC LIMIT 8")
        try:
            from core.reinforcement import get_feedback_summary
            feedback = get_feedback_summary()
            if feedback:
                feedback_lines = "\n".join([
                    f"  {r[0]}: {r[1]} approvals, {r[2]} rejections, multiplier={r[3]:.2f}"
                    for r in feedback
                ])
                # append to the return string
        except:
            feedback_lines = ""
        ext=", ".join([f"{r[0]}({r[1]})" for r in c.fetchall()])
        c.execute("SELECT name,size_mb,path FROM files ORDER BY size_mb DESC LIMIT 5")
        big="\n".join([f"  - {r[0]} ({float(r[1] or 0):.1f} MB) at {r[2]}" for r in c.fetchall()])
        return f"Total: {total} files | {size} GB | {hf-uh} dupes | {pending} pending\nTypes: {ext}\nLargest:\n{big}"
    except Exception as e: return f"DB unavailable: {e}"

def query(msg, action_result=None):
    if not LLM: return "LLM not connected — add your Groq API key to config.py."
    try:
        action_ctx=f"\n\nACTION JUST TAKEN:\n{action_result}" if action_result else ""
        prompt=f"""You are LADO, a smart personal AI assistant built into a file management app.
You are friendly, helpful, and conversational.
You have full knowledge of the user's file system below.

FILE SYSTEM:
{get_db_summary()}

RECENT LOG:
{get_logs()}{action_ctx}

Respond naturally. For casual messages be friendly. For file questions use the data above.
If an ACTION JUST TAKEN is provided, confirm what was done in plain English.
Never say you cannot access files — you have the data.

User: {msg}"""
        return ask_llm(prompt)
    except Exception as e: return f"Error: {e}"


class Bubble(ctk.CTkFrame):
    def __init__(self, parent, text, role, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        is_user=role=="user"
        bg=ACCENT if is_user else CARD2
        tc="#FFFFFF" if is_user else TEXT
        name="you" if is_user else "lado"
        side="e" if is_user else "w"
        wrap=ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(anchor=side, fill="x", padx=12)
        ctk.CTkLabel(wrap, text=name,
            font=ctk.CTkFont(family="Segoe UI",size=10,weight="bold"),
            text_color=DIM).pack(anchor=side, padx=20, pady=(12,0))
        bub=ctk.CTkFrame(wrap, fg_color=bg, corner_radius=20, border_width=0)
        bub.pack(anchor=side, padx=12, pady=(4,12))
        ctk.CTkLabel(bub, text=text,
            font=ctk.CTkFont(family="Segoe UI",size=12),
            text_color=tc, wraplength=560,
            justify="left", anchor="w").pack(padx=20, pady=14)


class ActionBubble(ctk.CTkFrame):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        pill=ctk.CTkFrame(self, fg_color="#F0FDF4", corner_radius=12)
        pill.pack(anchor="w", padx=32, pady=(4,4))
        ctk.CTkLabel(pill, text=f"⚡ {text}",
            font=ctk.CTkFont(family="Segoe UI",size=10,weight="bold"),
            text_color=ACCENTG).pack(padx=16, pady=8)


class ChatPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=36, pady=(32,0))
        left=ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Chat",
            font=ctk.CTkFont(family="Segoe UI",size=22,weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Ask LADO anything — or give it a command",
            font=ctk.CTkFont(family="Segoe UI",size=11),
            text_color=MUTED).pack(anchor="w", pady=(2,0))

        right=ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right")
        st,sc=(("● online",ACCENTG) if LLM else ("● offline",MUTED))
        ctk.CTkLabel(right, text=st,
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=sc).pack(side="right", padx=(8,0))
        ctk.CTkButton(right, text="Clear", width=62, height=28,
            font=ctk.CTkFont(family="Segoe UI",size=9),
            fg_color="transparent", border_color=BORDER_HI, border_width=1,
            text_color=MUTED, hover_color=CARD2, corner_radius=7,
            command=self._clear).pack(side="right")

        ctk.CTkFrame(self, fg_color="transparent", height=1).pack(fill="x", padx=36, pady=16)

        self._scroll=ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=20, border_width=0)
        self._scroll.pack(fill="both", expand=True, padx=36, pady=(0,16))

        if S.chat_messages:
            for role, text in S.chat_messages:
                Bubble(self._scroll, text, role).pack(fill="x")
        else:
            welcome="Hey! I'm LADO. Ask me anything, or try commands like 'run a scan' or 'archive the largest file'."
            S.chat_messages.append(("assistant", welcome))
            Bubble(self._scroll, welcome, "assistant").pack(fill="x")

        # ── Updated hint strip with all current commands ──────
        hint=ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=0)
        hint.pack(fill="x", padx=36, pady=(0,8))
        ctk.CTkLabel(hint,
            text="Commands:  'run a scan'  ·  'archive the largest file'  ·  'quarantine duplicates'  ·  'quarantine it'",
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=DIM).pack(padx=16, pady=8)

        inp=ctk.CTkFrame(self, fg_color=CARD, corner_radius=24, border_width=0)
        inp.pack(fill="x", padx=36, pady=(0,32))

        self._inp=ctk.CTkEntry(inp, placeholder_text="Ask LADO anything or give a command…",
            font=ctk.CTkFont(family="Segoe UI",size=12), height=48,
            fg_color="transparent", border_width=0, text_color=TEXT)
        self._inp.pack(side="left", fill="x", expand=True, padx=20, pady=6)
        self._inp.bind("<Return>", lambda e: self._send())

        self._sbtn=ctk.CTkButton(inp, text="Send", width=80, height=36,
            font=ctk.CTkFont(family="Segoe UI",size=12,weight="bold"),
            fg_color=ACCENT, text_color=BG, hover_color="#2563EB",
            corner_radius=14, command=self._send)
        self._sbtn.pack(side="right", padx=10)

    def _send(self):
        msg=self._inp.get().strip()
        if not msg: return
        self._inp.delete(0,"end")
        self._sbtn.configure(state="disabled", text="…")

        S.chat_messages.append(("user", msg))
        Bubble(self._scroll, msg, "user").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)

        action=detect_action(msg)
        thinking=ctk.CTkLabel(self._scroll,
            text="executing…" if action else "thinking…",
            font=ctk.CTkFont(family="Segoe UI",size=9), text_color=DIM)
        thinking.pack(anchor="w", padx=24, pady=4)
        self._scroll._parent_canvas.yview_moveto(1.0)

        threading.Thread(
            target=lambda: self._work(msg, action, thinking),
            daemon=True
        ).start()

    def _work(self, msg, action, thinking):
        action_result = None
        if action:
            action_result = execute_action(action)
            # Only show the action bubble if something actually happened
            if action_result and "ACTION_RESULT" in action_result:
                friendly = {
                    "scan":                  "Running a full scan…",
                    "approve_all":           "Executing approved suggestions…",
                    "archive_largest":       "Archiving largest file…",
                    "quarantine_duplicates": "Moving duplicate files to quarantine…",
                }.get(action, "Running action…")
                self.after(0, lambda: ActionBubble(
                    self._scroll, friendly).pack(fill="x"))

        r = query(msg, action_result)
        self.after(0, lambda: self._reply(r, thinking))

    def _reply(self, text, thinking):
        thinking.destroy()
        S.chat_messages.append(("assistant", text))
        Bubble(self._scroll, text, "assistant").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        self._sbtn.configure(state="normal", text="Send")

    def _clear(self):
        if LLM:
            try: reset_conversation()
            except: pass
        S.chat_messages=[]
        for w in self._scroll.winfo_children(): w.destroy()
        welcome="Cleared. What do you need?"
        S.chat_messages.append(("assistant", welcome))
        Bubble(self._scroll, welcome, "assistant").pack(fill="x")