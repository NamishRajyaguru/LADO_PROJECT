import customtkinter as ctk, threading, sqlite3, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try: from core.llm import ask_llm, reset_conversation; LLM=True
except: LLM=False
try: from config import LOG_DIR, DB_PATH
except: LOG_DIR=None; DB_PATH=None

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTG="#3ecf8e"

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
        ext_breakdown=", ".join([f"{r[0]}({r[1]})" for r in c.fetchall()])
        c.execute("SELECT name,size_mb,path FROM files ORDER BY size_mb DESC LIMIT 5")
        big="\n".join([f"  - {r[0]} ({float(r[1] or 0):.1f} MB) at {r[2]}" for r in c.fetchall()])
        return f"Total: {total} files | {size} GB | {hf-uh} duplicates | {pending} pending\nTypes: {ext_breakdown}\nLargest:\n{big}"
    except Exception as e: return f"DB unavailable: {e}"

def query(msg):
    if not LLM: return "LLM not connected — add your Groq API key to config.py."
    try:
        prompt=f"""You are LADO, a smart personal AI assistant built into a file management app.
You are friendly, helpful, and conversational — talk about anything from greetings to deep questions.
You have full knowledge of the user's file system below.

FILE SYSTEM:
{get_db_summary()}

RECENT LOG:
{get_logs()}

Respond naturally. For casual messages be friendly. For file questions use the data above.
Never say you cannot access files — you have the data.

User: {msg}"""
        return ask_llm(prompt)
    except Exception as e: return f"Error: {e}"


class Bubble(ctk.CTkFrame):
    def __init__(self, parent, text, role, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        is_user=role=="user"
        bg=CARD2 if is_user else CARD
        tc=ACCENT if is_user else TEXT
        name="you" if is_user else "lado"
        side="e" if is_user else "w"

        wrap=ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(anchor=side, fill="x", padx=8)

        ctk.CTkLabel(wrap, text=name,
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=DIM).pack(anchor=side, padx=16, pady=(10,0))

        bub=ctk.CTkFrame(wrap, fg_color=bg, corner_radius=10,
                         border_color=BORDER, border_width=1)
        bub.pack(anchor=side, padx=8, pady=(3,10))

        ctk.CTkLabel(bub, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=tc, wraplength=560,
            justify="left", anchor="w").pack(padx=16, pady=12)


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
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Ask LADO anything about your files or anything else",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED).pack(anchor="w", pady=(2,0))

        right=ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right")
        st,sc=(("● online",ACCENTG) if LLM else ("● offline",MUTED))
        ctk.CTkLabel(right, text=st,
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=sc).pack(side="right", padx=(8,0))
        ctk.CTkButton(right, text="Clear", width=62, height=28,
            font=ctk.CTkFont(family="Segoe UI", size=9),
            fg_color="transparent", border_color=BORDER_HI, border_width=1,
            text_color=MUTED, hover_color=CARD2, corner_radius=7,
            command=self._clear).pack(side="right")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=36, pady=24)

        self._scroll=ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=12)
        self._scroll.pack(fill="both", expand=True, padx=36, pady=(0,14))

        Bubble(self._scroll,
            "Hey! I'm LADO. Ask me anything — your files, duplicates, storage, or just say hi.",
            "assistant").pack(fill="x")

        # Input row
        inp=ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                         border_color=BORDER, border_width=1)
        inp.pack(fill="x", padx=36, pady=(0,28))

        self._inp=ctk.CTkEntry(inp, placeholder_text="Ask LADO anything…",
            font=ctk.CTkFont(family="Segoe UI", size=10), height=40,
            fg_color="transparent", border_width=0, text_color=TEXT)
        self._inp.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self._inp.bind("<Return>", lambda e:self._send())

        self._sbtn=ctk.CTkButton(inp, text="Send", width=72, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=ACCENT, text_color=BG, hover_color="#7aa5f5",
            corner_radius=8, command=self._send)
        self._sbtn.pack(side="right", padx=10)

    def _send(self):
        msg=self._inp.get().strip()
        if not msg: return
        self._inp.delete(0,"end")
        self._sbtn.configure(state="disabled", text="…")
        Bubble(self._scroll, msg, "user").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        thinking=ctk.CTkLabel(self._scroll, text="thinking…",
            font=ctk.CTkFont(family="Segoe UI", size=9), text_color=DIM)
        thinking.pack(anchor="w", padx=24, pady=4)
        self._scroll._parent_canvas.yview_moveto(1.0)
        threading.Thread(target=lambda:self._work(msg, thinking), daemon=True).start()

    def _work(self, msg, thinking):
        r=query(msg)
        self.after(0, lambda:self._reply(r, thinking))

    def _reply(self, text, thinking):
        thinking.destroy()
        Bubble(self._scroll, text, "assistant").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        self._sbtn.configure(state="normal", text="Send")

    def _clear(self):
        if LLM:
            try: reset_conversation()
            except: pass
        for w in self._scroll.winfo_children(): w.destroy()
        Bubble(self._scroll, "Cleared. What do you need?", "assistant").pack(fill="x")
