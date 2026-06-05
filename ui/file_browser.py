import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTY="#f0a84a"
SK1="#13141f";SK2="#1c1d2e"
PAGE=20

COLS=["Name","Type","Size","Modified","Path"]
WIDTHS=[220,65,85,140,310]

_cache=None

def load(ext=None,min_mb=None,search=None):
    try:
        conn=sqlite3.connect(DB_PATH);cur=conn.cursor()
        q="SELECT name,extension,size_mb,modified_time,path FROM files"
        conds=[];params=[]
        if ext and ext!="All":
            conds.append("LOWER(extension)=LOWER(?)");params.append(ext.lstrip("."))
        if min_mb:
            try:conds.append("size_mb>?");params.append(float(min_mb))
            except:pass
        if search:
            conds.append("LOWER(name) LIKE LOWER(?)");params.append(f"%{search}%")
        if conds:q+=" WHERE "+" AND ".join(conds)
        q+=" ORDER BY size_mb DESC"
        cur.execute(q,params);rows=cur.fetchall();conn.close();return rows
    except:return []

def get_exts():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT DISTINCT LOWER(extension) FROM files WHERE extension IS NOT NULL ORDER BY extension")
        return ["All"]+[r[0] for r in c.fetchall() if r[0]]
    except:return ["All"]


class SkeletonRow(ctk.CTkFrame):
    def __init__(self,parent,shade,**kw):
        super().__init__(parent,fg_color=shade,corner_radius=0,height=28,**kw)
        self.pack_propagate(False)
        self._phase=0;self._bars=[]
        for i,w in enumerate([190,55,70,120,260]):
            b=ctk.CTkFrame(self,fg_color=SK2,corner_radius=3,width=w,height=9)
            b.pack(side="left",padx=(18 if i==0 else 10,0),pady=10)
            b.pack_propagate(False);self._bars.append(b)
        self._tick()

    def _tick(self):
        if not self.winfo_exists():return
        self._phase=(self._phase+1)%24
        c=SK2 if self._phase<12 else SK1
        for b in self._bars:
            if b.winfo_exists():b.configure(fg_color=c)
        self.after(90,self._tick)


class FileBrowserPanel(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        self._all_rows=[]
        self._shown=0
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=36,pady=(32,0))
        left=ctk.CTkFrame(hdr,fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left,text="Files",
            font=ctk.CTkFont(family="Segoe UI",size=22,weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left,text="Browse and search your indexed file system",
            font=ctk.CTkFont(family="Segoe UI",size=11),
            text_color=MUTED).pack(anchor="w",pady=(2,0))
        self._cnt=ctk.CTkLabel(hdr,text="",
            font=ctk.CTkFont(family="Segoe UI",size=10),text_color=MUTED)
        self._cnt.pack(side="right")

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=36,pady=24)

        fb=ctk.CTkFrame(self,fg_color=CARD,corner_radius=12,
                        border_color=BORDER,border_width=1)
        fb.pack(fill="x",padx=36,pady=(0,16))
        self._sv=ctk.StringVar()
        ctk.CTkEntry(fb,textvariable=self._sv,placeholder_text="Search by filename…",
            width=220,height=34,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=CARD2,border_color=BORDER_HI,border_width=1,
            text_color=TEXT,corner_radius=8).pack(side="left",padx=14,pady=12)
        self._ev=ctk.StringVar(value="All")
        ctk.CTkOptionMenu(fb,variable=self._ev,values=get_exts(),
            width=110,height=34,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=CARD2,button_color=BORDER_HI,button_hover_color=CARD2,
            dropdown_fg_color=CARD,text_color=MUTED,
            corner_radius=8).pack(side="left",padx=(0,10))
        self._mv=ctk.StringVar()
        ctk.CTkEntry(fb,textvariable=self._mv,placeholder_text="Min MB",
            width=88,height=34,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=CARD2,border_color=BORDER_HI,border_width=1,
            text_color=TEXT,corner_radius=8).pack(side="left",padx=(0,12))
        ctk.CTkButton(fb,text="Search",width=80,height=34,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=ACCENT,text_color=BG,hover_color="#7aa5f5",
            corner_radius=8,command=self._apply).pack(side="left")

        ch=ctk.CTkFrame(self,fg_color=SURFACE,corner_radius=0,height=32)
        ch.pack(fill="x",padx=36);ch.pack_propagate(False)
        for i,(col,w) in enumerate(zip(COLS,WIDTHS)):
            ctk.CTkLabel(ch,text=col,
                font=ctk.CTkFont(family="Segoe UI",size=9,weight="bold"),
                text_color=DIM,width=w,anchor="w").pack(
                side="left",padx=(18 if i==0 else 8,0))

        self._scroll=ctk.CTkScrollableFrame(self,fg_color="transparent",corner_radius=0)
        self._scroll.pack(fill="both",expand=True,padx=36,pady=(0,8))

        self._load_more_btn=ctk.CTkButton(self,text="Load 20 more ↓",
            width=160,height=32,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color="transparent",border_color=BORDER_HI,border_width=1,
            text_color=MUTED,hover_color=CARD2,corner_radius=8,
            command=self._load_more)

        global _cache
        if _cache is not None:
            self._all_rows=_cache
            self._shown=0
            self._cnt.configure(text=f"{len(_cache)} files")
            self._render_next_page()
        else:
            self._show_skeletons()
            threading.Thread(target=self._bg_fetch,args=(None,None,None),daemon=True).start()

    def _show_skeletons(self):
        for w in self._scroll.winfo_children():w.destroy()
        self._load_more_btn.pack_forget()
        for i in range(8):
            SkeletonRow(self._scroll,shade=CARD if i%2==0 else SURFACE).pack(fill="x")

    def _bg_fetch(self,ext,min_mb,search):
        rows=load(ext,min_mb,search)
        self.after(0,lambda:self._render(rows))

    def _render(self,rows):
        global _cache
        if not self.winfo_exists():return
        _cache=rows
        self._all_rows=rows
        self._shown=0
        for w in self._scroll.winfo_children():w.destroy()
        self._cnt.configure(text=f"{len(rows)} files")
        self._render_next_page()

    def _render_next_page(self):
        start=self._shown
        end=min(start+PAGE,len(self._all_rows))
        for i in range(start,end):
            r=self._all_rows[i]
            bg=CARD if i%2==0 else SURFACE
            row=ctk.CTkFrame(self._scroll,fg_color=bg,corner_radius=0,height=28)
            row.pack(fill="x");row.pack_propagate(False)
            vals=[str(r[0])[:38],f".{r[1]}" if r[1] else "",
                  f"{float(r[2] or 0):.1f} MB",str(r[3] or "")[:16],str(r[4])]
            colors=[TEXT,ACCENT,ACCENTY,MUTED,DIM]
            for j,(v,c,w) in enumerate(zip(vals,colors,WIDTHS)):
                ctk.CTkLabel(row,text=v,
                    font=ctk.CTkFont(family="Segoe UI",size=10),
                    text_color=c,width=w,anchor="w").pack(
                    side="left",padx=(18 if j==0 else 8,0))
        self._shown=end
        if self._shown<len(self._all_rows):
            remaining=len(self._all_rows)-self._shown
            self._load_more_btn.configure(text=f"Load 20 more  ·  {remaining} remaining ↓")
            self._load_more_btn.pack(pady=(4,20))
        else:
            self._load_more_btn.pack_forget()

    def _load_more(self):
        self._render_next_page()

    def _apply(self):
        global _cache
        _cache=None
        self._load_more_btn.pack_forget()
        e=self._ev.get() if self._ev.get()!="All" else None
        self._show_skeletons()
        threading.Thread(target=self._bg_fetch,
            args=(e,self._mv.get().strip() or None,self._sv.get().strip() or None),
            daemon=True).start()