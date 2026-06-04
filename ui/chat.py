import customtkinter as ctk, threading, sys, os, sqlite3
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try: from core.llm import ask_llm, reset_conversation; LLM=True
except: LLM=False
try: from config import LOG_DIR, DB_PATH
except: LOG_DIR=None; DB_PATH=None

BG_BASE="#050508";BG_SURFACE="#0c0c12";BG_RAISED="#121219";BG_HOVER="#1a1a24"
BORDER="#1e1e2e";TEXT_PRI="#f0f0f8";TEXT_SEC="#6b6b8a";TEXT_MUT="#2e2e48"
BLUE="#4d9de0";GREEN="#3ddc84"

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
        return f"""Total files: {total} | Storage: {size} GB | Duplicates: {hf-uh} | Pending suggestions: {pending}
Top file types: {ext_breakdown}
Largest files:
{big}"""
    except Exception as e:
        return f"DB unavailable: {e}"

def query(msg):
    if not LLM: return "LLM not connected — add your Groq API key to config.py."
    try:
        prompt=f"""You are LADO, a smart personal AI assistant built into a file management app.
You are friendly, helpful, and conversational — you can talk about anything from casual greetings to deep questions.
You also have full knowledge of the user's file system from the database below.

FILE SYSTEM SNAPSHOT:
{get_db_summary()}

RECENT ACTIVITY LOG:
{get_logs()}

Respond naturally to the user. For casual messages like greetings, just be friendly and natural.
For file-related questions, use the snapshot above to give specific accurate answers.
Never say you "cannot access" files — you have the data above.

User message: {msg}"""
        return ask_llm(prompt)
    except Exception as e: return f"Error: {e}"


class Bubble(ctk.CTkFrame):
    def __init__(self,parent,text,role,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        is_user=role=="user"
        bg=BG_HOVER if is_user else BG_RAISED
        tc=BLUE if is_user else TEXT_PRI
        name="you" if is_user else "lado"
        side="e" if is_user else "w"

        wrap=ctk.CTkFrame(self,fg_color="transparent")
        wrap.pack(anchor=side,padx=8,fill="x")

        ctk.CTkLabel(wrap,text=name,
            font=ctk.CTkFont(family="Segoe UI",size=8),
            text_color=TEXT_MUT).pack(anchor=side,padx=16,pady=(8,0))

        bub=ctk.CTkFrame(wrap,fg_color=bg,corner_radius=8,
                         border_color=BORDER,border_width=1)
        bub.pack(anchor=side,padx=8,pady=(2,8))
        ctk.CTkLabel(bub,text=text,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=tc,wraplength=540,justify="left",anchor="w").pack(
            padx=14,pady=10)


class ChatPanel(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=32,pady=(28,0))
        ctk.CTkLabel(hdr,text="Chat",
            font=ctk.CTkFont(family="Segoe UI",size=20,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        st,sc=(("● online",GREEN) if LLM else ("● offline",TEXT_SEC))
        ctk.CTkLabel(hdr,text=st,
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=sc).pack(side="right",padx=(0,12))

        ctk.CTkButton(hdr,text="Clear",width=60,height=26,
            font=ctk.CTkFont(family="Segoe UI",size=9),
            fg_color="transparent",border_color=BORDER,border_width=1,
            text_color=TEXT_SEC,hover_color=BG_HOVER,
            corner_radius=5,command=self._clear).pack(side="right",padx=(0,8))

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=32,pady=20)

        self._scroll=ctk.CTkScrollableFrame(self,fg_color=BG_SURFACE,corner_radius=10)
        self._scroll.pack(fill="both",expand=True,padx=32,pady=(0,12))

        Bubble(self._scroll,"Hey! I'm LADO. Ask me anything — your files, duplicates, storage, or just say hi.","assistant").pack(fill="x")

        inp=ctk.CTkFrame(self,fg_color=BG_RAISED,corner_radius=8,
                         border_color=BORDER,border_width=1)
        inp.pack(fill="x",padx=32,pady=(0,24))

        self._inp=ctk.CTkEntry(inp,placeholder_text="Ask LADO anything…",
            font=ctk.CTkFont(family="Segoe UI",size=10),height=38,
            fg_color="transparent",border_width=0,text_color=TEXT_PRI)
        self._inp.pack(side="left",fill="x",expand=True,padx=12,pady=8)
        self._inp.bind("<Return>",lambda e:self._send())

        self._sbtn=ctk.CTkButton(inp,text="Send",width=68,height=30,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=BLUE,text_color=BG_BASE,hover_color="#6bb3e8",
            corner_radius=6,command=self._send)
        self._sbtn.pack(side="right",padx=8)

    def _send(self):
        msg=self._inp.get().strip()
        if not msg: return
        self._inp.delete(0,"end")
        self._sbtn.configure(state="disabled",text="…")
        Bubble(self._scroll,msg,"user").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        thinking=ctk.CTkLabel(self._scroll,text="thinking…",
            font=ctk.CTkFont(family="Segoe UI",size=9),text_color=TEXT_MUT)
        thinking.pack(anchor="w",padx=24,pady=4)
        self._scroll._parent_canvas.yview_moveto(1.0)
        def _work():
            r=query(msg)
            self.after(0,lambda:self._reply(r,thinking))
        threading.Thread(target=_work,daemon=True).start()

    def _reply(self,text,thinking):
        thinking.destroy()
        Bubble(self._scroll,text,"assistant").pack(fill="x")
        self._scroll._parent_canvas.yview_moveto(1.0)
        self._sbtn.configure(state="normal",text="Send")

    def _clear(self):
        if LLM:
            try: reset_conversation()
            except: pass
        for w in self._scroll.winfo_children(): w.destroy()
        Bubble(self._scroll,"Conversation reset. What do you need?","assistant").pack(fill="x")