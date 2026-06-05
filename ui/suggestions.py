import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTG="#3ecf8e";ACCENTR="#e05c72";ACCENTY="#f0a84a"
SK1="#13141f";SK2="#1c1d2e"

RISK_CLR={"low":ACCENTG,"medium":ACCENTY,"high":ACCENTR,"critical":"#ff3355"}
TABS=["Pending","Approved","Rejected","All"]
PAGE=20  # rows per page

_cache={"pending":None,"approved":None,"rejected":None,"all":None}

def get(status="pending"):
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        if status!="all":
            c.execute("""SELECT id,file_path,action,reason,confidence,risk,status
                        FROM suggestions WHERE status=?
                        ORDER BY confidence DESC""",(status,))
        else:
            c.execute("""SELECT id,file_path,action,reason,confidence,risk,status
                        FROM suggestions ORDER BY confidence DESC""")
        return c.fetchall()
    except: return []

def get_total(status):
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        if status!="all":
            c.execute("SELECT COUNT(*) FROM suggestions WHERE status=?",(status,))
        else:
            c.execute("SELECT COUNT(*) FROM suggestions")
        return c.fetchone()[0]
    except: return 0

def update(sid,st):
    try:
        c=sqlite3.connect(DB_PATH)
        c.cursor().execute("UPDATE suggestions SET status=? WHERE id=?",(st,sid))
        c.commit()
    except: pass


class SkeletonCard(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color=CARD,corner_radius=12,
                         border_color=BORDER,border_width=1,**kw)
        self._phase=0;self._bars=[]
        p=ctk.CTkFrame(self,fg_color="transparent")
        p.pack(fill="x",padx=20,pady=(18,0))
        for w,anch in [(200,"w"),(120,"w"),(320,"w")]:
            b=ctk.CTkFrame(p,fg_color=SK2,corner_radius=4,width=w,height=10)
            b.pack(anchor=anch,pady=5);b.pack_propagate(False);self._bars.append(b)
        bot=ctk.CTkFrame(self,fg_color="transparent")
        bot.pack(fill="x",padx=20,pady=(8,16))
        for w in [150,80,72]:
            b=ctk.CTkFrame(bot,fg_color=SK2,corner_radius=6,width=w,height=26)
            b.pack(side="left" if w==150 else "right",padx=(0,6))
            b.pack_propagate(False);self._bars.append(b)
        self._tick()

    def _tick(self):
        if not self.winfo_exists():return
        self._phase=(self._phase+1)%24
        c=SK2 if self._phase<12 else SK1
        for b in self._bars:
            if b.winfo_exists():b.configure(fg_color=c)
        self.after(90,self._tick)


class SRow(ctk.CTkFrame):
    def __init__(self,parent,data,reload_cb,**kw):
        super().__init__(parent,fg_color=CARD,corner_radius=12,
                         border_color=BORDER,border_width=1,**kw)
        sid,fp,action,reason,conf,risk,status=data
        conf=float(conf or 0)
        rc=RISK_CLR.get((risk or "low").lower(),ACCENTY)
        fname=os.path.basename(fp) if fp else "unknown"
        ctk.CTkFrame(self,fg_color=rc,height=2,corner_radius=0).pack(fill="x",side="top")
        body=ctk.CTkFrame(self,fg_color="transparent")
        body.pack(fill="x",padx=20,pady=(14,0))
        r1=ctk.CTkFrame(body,fg_color="transparent")
        r1.pack(fill="x")
        ctk.CTkLabel(r1,text=fname,
            font=ctk.CTkFont(family="Segoe UI",size=11,weight="bold"),
            text_color=TEXT).pack(side="left")
        sc={"pending":ACCENTY,"approved":ACCENTG,"rejected":ACCENTR}.get(status,MUTED)
        ctk.CTkLabel(r1,text=f"  {status.upper()}  ",
            font=ctk.CTkFont(family="Segoe UI",size=8,weight="bold"),
            text_color=BG,fg_color=sc,corner_radius=4).pack(side="right",padx=(4,0))
        ctk.CTkLabel(r1,text=f"  {(risk or 'LOW').upper()}  ",
            font=ctk.CTkFont(family="Segoe UI",size=8,weight="bold"),
            text_color=BG,fg_color=rc,corner_radius=4).pack(side="right")
        r2=ctk.CTkFrame(body,fg_color="transparent")
        r2.pack(fill="x",pady=(6,0))
        ctk.CTkLabel(r2,text=f"→  {action}",
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=ACCENT).pack(side="left")
        if reason:
            ctk.CTkLabel(body,text=reason,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                text_color=MUTED,anchor="w",wraplength=700).pack(fill="x",pady=(4,0))
        bot=ctk.CTkFrame(self,fg_color="transparent")
        bot.pack(fill="x",padx=20,pady=(12,16))
        ctk.CTkLabel(bot,text=f"{int(conf*100)}%",
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=MUTED,width=34).pack(side="left")
        track=ctk.CTkFrame(bot,fg_color=CARD2,width=160,height=4,corner_radius=2)
        track.pack(side="left",padx=(4,20));track.pack_propagate(False)
        ctk.CTkFrame(track,fg_color=ACCENT,width=max(2,int(160*conf)),
                     height=4,corner_radius=2).place(x=0,y=0)
        if status=="pending":
            ctk.CTkButton(bot,text="Approve",width=84,height=28,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                fg_color="transparent",border_color=ACCENTG,border_width=1,
                text_color=ACCENTG,hover_color="#0a2218",corner_radius=7,
                command=lambda:(update(sid,"approved"),self._bust(),reload_cb())).pack(side="right",padx=(6,0))
            ctk.CTkButton(bot,text="Reject",width=76,height=28,
                font=ctk.CTkFont(family="Segoe UI",size=9),
                fg_color="transparent",border_color=ACCENTR,border_width=1,
                text_color=ACCENTR,hover_color="#22080e",corner_radius=7,
                command=lambda:(update(sid,"rejected"),self._bust(),reload_cb())).pack(side="right")

    def _bust(self):
        global _cache
        _cache={"pending":None,"approved":None,"rejected":None,"all":None}


class SuggestionsPanel(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        self._filter="pending"
        self._all_rows=[]
        self._shown=0
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=36,pady=(32,0))
        left=ctk.CTkFrame(hdr,fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left,text="Suggestions",
            font=ctk.CTkFont(family="Segoe UI",size=22,weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left,text="Review LADO's recommendations and take action",
            font=ctk.CTkFont(family="Segoe UI",size=11),
            text_color=MUTED).pack(anchor="w",pady=(2,0))

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=36,pady=24)

        tabs=ctk.CTkFrame(self,fg_color=CARD,corner_radius=10,
                          border_color=BORDER,border_width=1)
        tabs.pack(fill="x",padx=36,pady=(0,16))
        self._tbns={}
        for t in TABS:
            active=t=="Pending"
            b=ctk.CTkButton(tabs,text=t,width=94,height=32,
                font=ctk.CTkFont(family="Segoe UI",size=10),
                fg_color=ACCENT if active else "transparent",
                text_color=BG if active else MUTED,
                hover_color=CARD2,corner_radius=8,
                command=lambda x=t:self._tab(x))
            b.pack(side="left",padx=5,pady=5)
            self._tbns[t]=b

        self._cnt=ctk.CTkLabel(self,text="",
            font=ctk.CTkFont(family="Segoe UI",size=10),text_color=MUTED)
        self._cnt.pack(anchor="w",padx=36,pady=(0,10))

        self._scroll=ctk.CTkScrollableFrame(self,fg_color="transparent")
        self._scroll.pack(fill="both",expand=True,padx=36,pady=(0,8))

        # Load More button sits below scroll
        self._load_more_btn=ctk.CTkButton(self,text="Load 20 more ↓",
            width=160,height=32,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color="transparent",border_color=BORDER_HI,border_width=1,
            text_color=MUTED,hover_color=CARD2,corner_radius=8,
            command=self._load_more)
        # don't pack yet — shown only when there's more to load

        self._load()

    def _tab(self,t):
        self._filter=t.lower()
        for k,b in self._tbns.items():
            b.configure(fg_color=ACCENT if k==t else "transparent",
                        text_color=BG if k==t else MUTED)
        self._load()

    def _load(self):
        global _cache
        f=self._filter
        self._load_more_btn.pack_forget()
        if _cache[f] is not None:
            self._all_rows=_cache[f]
            self._shown=0
            self._render_from_cache()
            return
        self._show_skeletons()
        threading.Thread(target=lambda:self._bg(f),daemon=True).start()

    def _show_skeletons(self):
        for w in self._scroll.winfo_children():w.destroy()
        for _ in range(4):
            SkeletonCard(self._scroll).pack(fill="x",pady=6)

    def _bg(self,f):
        rows=get(f)
        total=get_total(f)
        self.after(0,lambda:self._render_fresh(rows,total))

    def _render_fresh(self,rows,total):
        global _cache
        if not self.winfo_exists():return
        _cache[self._filter]=rows
        self._all_rows=rows
        self._shown=0
        for w in self._scroll.winfo_children():w.destroy()
        self._cnt.configure(text=f"{len(rows)} total  ·  highest confidence first")
        if not rows:
            ctk.CTkLabel(self._scroll,text="Nothing here.",
                font=ctk.CTkFont(family="Segoe UI",size=13),
                text_color=DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_from_cache(self):
        for w in self._scroll.winfo_children():w.destroy()
        self._cnt.configure(text=f"{len(self._all_rows)} total  ·  highest confidence first")
        if not self._all_rows:
            ctk.CTkLabel(self._scroll,text="Nothing here.",
                font=ctk.CTkFont(family="Segoe UI",size=13),
                text_color=DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_next_page(self):
        start=self._shown
        end=min(start+PAGE,len(self._all_rows))
        for i in range(start,end):
            SRow(self._scroll,self._all_rows[i],self._load).pack(fill="x",pady=6)
        self._shown=end
        # show/hide load more button
        if self._shown < len(self._all_rows):
            remaining=len(self._all_rows)-self._shown
            self._load_more_btn.configure(
                text=f"Load 20 more  ·  {remaining} remaining ↓")
            self._load_more_btn.pack(pady=(4,20))
        else:
            self._load_more_btn.pack_forget()

    def _load_more(self):
        self._render_next_page()