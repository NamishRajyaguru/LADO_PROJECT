import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG="#FFFFFF";SURFACE="#F7F7F8";CARD="#F7F7F8";CARD2="#F1F1F3"
BORDER="#E6E6E9";BORDER_HI="#D1D1D6"
TEXT="#000000";MUTED="#8A8F98";DIM="#C4C5C8"
ACCENT="#000000";ACCENTG="#000000";ACCENTR="#000000";ACCENTY="#000000"
SK1="#121212";SK2="#1C1C1E"
PAGE=20

_cache=None

def clusters():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("""SELECT hash,COUNT(*) cnt,SUM(size_mb) sz FROM files
                     WHERE hash IS NOT NULL AND hash!=''
                     GROUP BY hash HAVING cnt>1 ORDER BY sz DESC""")
        return c.fetchall()
    except:return []

def files_in(h):
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT path,name,size_mb,modified_time FROM files WHERE hash=?",(h,))
        return c.fetchall()
    except:return []


class SkeletonCluster(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color=CARD,corner_radius=12,
                         border_color=BORDER,border_width=1,**kw)
        self._phase=0;self._bars=[]
        row=ctk.CTkFrame(self,fg_color="transparent")
        row.pack(fill="x",padx=20,pady=18)
        for w,side in [(130,"left"),(80,"left"),(100,"left"),(150,"right")]:
            b=ctk.CTkFrame(row,fg_color=SK2,corner_radius=3,width=w,height=10)
            b.pack(side=side,padx=(0 if side=="right" else 14,0))
            b.pack_propagate(False);self._bars.append(b)
        self._tick()

    def _tick(self):
        if not self.winfo_exists():return
        self._phase=(self._phase+1)%24
        c=SK2 if self._phase<12 else SK1
        for b in self._bars:
            if b.winfo_exists():b.configure(fg_color=c)
        self.after(90,self._tick)


class Cluster(ctk.CTkFrame):
    def __init__(self,parent,data,idx,**kw):
        super().__init__(parent,fg_color=CARD,corner_radius=20,
                         border_width=0,**kw)
        self._hash,self._cnt,sz=data
        self._sz=float(sz or 0)
        self._expanded=False;self._detail=None
        wasted=self._sz*(self._cnt-1)/self._cnt if self._cnt>1 else 0
        hdr=ctk.CTkFrame(self,fg_color="transparent",cursor="hand2")
        hdr.pack(fill="x",padx=24,pady=18)
        hdr.bind("<Button-1>",self._toggle)
        self._arrow=ctk.CTkLabel(hdr,text="›",
            font=ctk.CTkFont(family="Segoe UI",size=18,weight="bold"),text_color=MUTED,width=20)
        self._arrow.pack(side="left")
        self._arrow.bind("<Button-1>",self._toggle)
        ctk.CTkLabel(hdr,text=f"  Cluster {idx+1}",
            font=ctk.CTkFont(family="Segoe UI",size=12,weight="bold"),
            text_color=TEXT).pack(side="left")
        ctk.CTkLabel(hdr,text=f"  ·  {self._cnt} copies",
            font=ctk.CTkFont(family="Segoe UI",size=11),text_color=MUTED).pack(side="left")
        ctk.CTkLabel(hdr,text=f"  ·  {self._sz:.1f} MB total",
            font=ctk.CTkFont(family="Segoe UI",size=11),text_color=ACCENTY).pack(side="left")
        badge=ctk.CTkFrame(hdr,fg_color=CARD2,corner_radius=8)
        badge.pack(side="right")
        ctk.CTkLabel(badge,text=f"  ↓ {wasted:.1f} MB free  ",
            font=ctk.CTkFont(family="Segoe UI",size=10,weight="bold"),
            text_color=ACCENTG).pack(padx=6,pady=6)
        ctk.CTkLabel(hdr,text=f"{self._hash[:10]}…",
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=DIM).pack(side="right",padx=(0,14))

    def _toggle(self,e=None):
        self._expanded=not self._expanded
        self._arrow.configure(text="∨" if self._expanded else "›")
        if self._expanded:
            self._detail=ctk.CTkFrame(self,fg_color=SURFACE,corner_radius=10)
            self._detail.pack(fill="x",padx=20,pady=(0,20))
            for i,(path,name,mb,mod) in enumerate(files_in(self._hash)):
                row=ctk.CTkFrame(self._detail,fg_color="transparent")
                row.pack(fill="x",padx=16,pady=6)
                ctk.CTkLabel(row,text="●",font=ctk.CTkFont(size=9),
                    text_color=ACCENTG if i==0 else MUTED,width=14).pack(side="left")
                ctk.CTkLabel(row,text=f"  {name}",
                    font=ctk.CTkFont(family="Segoe UI",size=11,weight="bold"),
                    text_color=TEXT).pack(side="left")
                ctk.CTkLabel(row,text=f"  {float(mb or 0):.1f} MB",
                    font=ctk.CTkFont(family="Segoe UI",size=10),text_color=ACCENTY).pack(side="left")
                ctk.CTkLabel(row,text=f"  {path}",
                    font=ctk.CTkFont(family="Segoe UI",size=10),text_color=DIM).pack(side="left")
        else:
            if self._detail:self._detail.destroy();self._detail=None


class DuplicatesPanel(ctk.CTkFrame):
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
        ctk.CTkLabel(left,text="Duplicates",
            font=ctk.CTkFont(family="Segoe UI",size=22,weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left,text="Groups of identical files — expand to see paths",
            font=ctk.CTkFont(family="Segoe UI",size=11),
            text_color=MUTED).pack(anchor="w",pady=(2,0))
        self._stats=ctk.CTkLabel(hdr,text="",
            font=ctk.CTkFont(family="Segoe UI",size=11,weight="bold"),
            text_color=ACCENTG)
        self._stats.pack(side="right")

        # divider removed
        ctk.CTkFrame(self, fg_color="transparent", height=1).pack(fill="x", padx=36, pady=16)

        self._cnt=ctk.CTkLabel(self,text="",
            font=ctk.CTkFont(family="Segoe UI",size=10),text_color=MUTED)
        self._cnt.pack(anchor="w",padx=36,pady=(0,12))

        self._scroll=ctk.CTkScrollableFrame(self,fg_color="transparent")
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
            wasted=sum(float(sz or 0)*(cnt-1)/cnt for _,cnt,sz in _cache if cnt>1)
            self._stats.configure(text=f"↓ {wasted:.1f} MB recoverable")
            self._cnt.configure(text=f"{len(_cache)} clusters found")
            self._render_next_page()
        else:
            for _ in range(5):
                SkeletonCluster(self._scroll).pack(fill="x",pady=6)
            threading.Thread(target=self._bg,daemon=True).start()

    def _bg(self):
        cl=clusters()
        self.after(0,lambda:self._render(cl))

    def _render(self,cl):
        global _cache
        if not self.winfo_exists():return
        _cache=cl
        self._all_rows=cl
        self._shown=0
        wasted=sum(float(sz or 0)*(cnt-1)/cnt for _,cnt,sz in cl if cnt>1)
        for w in self._scroll.winfo_children():w.destroy()
        self._stats.configure(text=f"↓ {wasted:.1f} MB recoverable")
        self._cnt.configure(text=f"{len(cl)} clusters found")
        if not cl:
            ctk.CTkLabel(self._scroll,text="No duplicates found.",
                font=ctk.CTkFont(family="Segoe UI",size=13),
                text_color=DIM).pack(pady=56)
            return
        self._render_next_page()

    def _render_next_page(self):
        start=self._shown
        end=min(start+PAGE,len(self._all_rows))
        for i in range(start,end):
            Cluster(self._scroll,self._all_rows[i],i).pack(fill="x",pady=6)
        self._shown=end
        if self._shown<len(self._all_rows):
            remaining=len(self._all_rows)-self._shown
            self._load_more_btn.configure(text=f"Load 20 more  ·  {remaining} remaining ↓")
            self._load_more_btn.pack(pady=(4,20))
        else:
            self._load_more_btn.pack_forget()

    def _load_more(self):
        self._render_next_page()