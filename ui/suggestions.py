import customtkinter as ctk, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG_BASE="#050508";BG_SURFACE="#0c0c12";BG_RAISED="#121219";BG_HOVER="#1a1a24"
BORDER="#1e1e2e";TEXT_PRI="#f0f0f8";TEXT_SEC="#6b6b8a";TEXT_MUT="#2e2e48"
BLUE="#4d9de0";GREEN="#3ddc84";AMBER="#f5a623";RED="#e05c5c"

RISK_CLR={"low":GREEN,"medium":AMBER,"high":RED,"critical":"#ff2d2d"}
TABS=["Pending","Approved","Rejected","All"]

def get(status="pending"):
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        q="SELECT id,file_path,action,reason,confidence,risk,status FROM suggestions"
        if status!="all": q+=" WHERE status=?"; c.execute(q+" ORDER BY confidence DESC",(status,))
        else: c.execute(q+" ORDER BY confidence DESC")
        return c.fetchall()
    except: return []

def update(sid,st):
    try:
        c=sqlite3.connect(DB_PATH)
        c.cursor().execute("UPDATE suggestions SET status=? WHERE id=?",(st,sid))
        c.commit()
    except: pass


class SRow(ctk.CTkFrame):
    def __init__(self,parent,data,reload_cb,**kw):
        super().__init__(parent,fg_color=BG_RAISED,corner_radius=8,
                         border_color=BORDER,border_width=1,**kw)
        sid,fp,action,reason,conf,risk,status=data
        conf=float(conf or 0)
        rc=RISK_CLR.get((risk or "low").lower(),AMBER)
        fname=os.path.basename(fp) if fp else "unknown"

        # Row 1: filename + badges
        r1=ctk.CTkFrame(self,fg_color="transparent")
        r1.pack(fill="x",padx=16,pady=(14,2))

        ctk.CTkLabel(r1,text=fname,
            font=ctk.CTkFont(family="Segoe UI",size=11,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        # status badge
        sc={"pending":AMBER,"approved":GREEN,"rejected":RED}.get(status,TEXT_SEC)
        ctk.CTkLabel(r1,text=f" {status.upper()} ",
            font=ctk.CTkFont(family="Segoe UI",size=8,weight="bold"),
            text_color=BG_BASE,fg_color=sc,corner_radius=3).pack(side="right",padx=(4,0))

        # risk badge
        ctk.CTkLabel(r1,text=f" {(risk or 'LOW').upper()} ",
            font=ctk.CTkFont(family="Segoe UI",size=8,weight="bold"),
            text_color=BG_BASE,fg_color=rc,corner_radius=3).pack(side="right",padx=(0,4))

        # Row 2: action tag
        r2=ctk.CTkFrame(self,fg_color="transparent")
        r2.pack(fill="x",padx=16,pady=(0,2))
        ctk.CTkLabel(r2,text=f"→  {action}",
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=BLUE).pack(side="left")

        # Row 3: reason
        if reason:
            ctk.CTkLabel(self,text=reason,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                text_color=TEXT_SEC,anchor="w",wraplength=680).pack(
                fill="x",padx=16,pady=(0,8))

        # Row 4: confidence bar + buttons
        r4=ctk.CTkFrame(self,fg_color="transparent")
        r4.pack(fill="x",padx=16,pady=(0,14))

        ctk.CTkLabel(r4,text=f"{int(conf*100)}%",
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=TEXT_SEC,width=32).pack(side="left")

        # bar
        bar_bg=ctk.CTkFrame(r4,fg_color=BG_HOVER,width=140,height=4,corner_radius=2)
        bar_bg.pack(side="left",padx=(4,16))
        bar_bg.pack_propagate(False)
        fill=max(2,int(140*conf))
        ctk.CTkFrame(bar_bg,fg_color=BLUE,width=fill,height=4,corner_radius=2).place(x=0,y=0)

        if status=="pending":
            ctk.CTkButton(r4,text="Approve",width=80,height=26,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                fg_color="transparent",border_color=GREEN,border_width=1,
                text_color=GREEN,hover_color="#0a2a14",corner_radius=5,
                command=lambda: (update(sid,"approved"),reload_cb())).pack(side="right",padx=(4,0))
            ctk.CTkButton(r4,text="Reject",width=72,height=26,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                fg_color="transparent",border_color=RED,border_width=1,
                text_color=RED,hover_color="#2a0a0a",corner_radius=5,
                command=lambda: (update(sid,"rejected"),reload_cb())).pack(side="right")


class SuggestionsPanel(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        self._filter="pending"; self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=32,pady=(28,0))
        ctk.CTkLabel(hdr,text="Suggestions",
            font=ctk.CTkFont(family="Segoe UI",size=20,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=32,pady=20)

        # Tab strip
        tabs=ctk.CTkFrame(self,fg_color=BG_RAISED,corner_radius=8,
                          border_color=BORDER,border_width=1)
        tabs.pack(fill="x",padx=32,pady=(0,16))
        self._tbns={}
        for t in TABS:
            b=ctk.CTkButton(tabs,text=t,width=90,height=30,
                font=ctk.CTkFont(family="Segoe UI",size=10),
                fg_color=BLUE if t=="Pending" else "transparent",
                text_color=BG_BASE if t=="Pending" else TEXT_SEC,
                hover_color=BG_HOVER,corner_radius=6,
                command=lambda x=t: self._tab(x))
            b.pack(side="left",padx=4,pady=4)
            self._tbns[t]=b

        self._cnt=ctk.CTkLabel(self,text="",
            font=ctk.CTkFont(family="Segoe UI",size=10),text_color=TEXT_SEC)
        self._cnt.pack(anchor="w",padx=32,pady=(0,8))

        self._scroll=ctk.CTkScrollableFrame(self,fg_color="transparent")
        self._scroll.pack(fill="both",expand=True,padx=32,pady=(0,24))
        self._load()

    def _tab(self,t):
        self._filter=t.lower()
        for k,b in self._tbns.items():
            b.configure(fg_color=BLUE if k==t else "transparent",
                        text_color=BG_BASE if k==t else TEXT_SEC)
        self._load()

    def _load(self):
        for w in self._scroll.winfo_children(): w.destroy()
        rows=get(self._filter)
        self._cnt.configure(text=f"{len(rows)} result{'s' if len(rows)!=1 else ''}")
        if not rows:
            ctk.CTkLabel(self._scroll,text="Nothing here.",
                font=ctk.CTkFont(family="Segoe UI",size=12),
                text_color=TEXT_MUT).pack(pady=48)
            return
        for r in rows:
            SRow(self._scroll,r,self._load).pack(fill="x",pady=4)
