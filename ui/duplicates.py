import customtkinter as ctk, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG_BASE="#050508";BG_SURFACE="#0c0c12";BG_RAISED="#121219";BG_HOVER="#1a1a24"
BORDER="#1e1e2e";TEXT_PRI="#f0f0f8";TEXT_SEC="#6b6b8a";TEXT_MUT="#2e2e48"
BLUE="#4d9de0";GREEN="#3ddc84";AMBER="#f5a623";RED="#e05c5c"

def clusters():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("""SELECT hash,COUNT(*) cnt,SUM(size_mb) sz FROM files
                     WHERE hash IS NOT NULL AND hash!=''
                     GROUP BY hash HAVING cnt>1 ORDER BY sz DESC""")
        return c.fetchall()
    except: return []

def files_in(h):
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT path,name,size_mb,modified_time FROM files WHERE hash=?",(h,))
        return c.fetchall()
    except: return []


class Cluster(ctk.CTkFrame):
    def __init__(self,parent,data,idx,**kw):
        super().__init__(parent,fg_color=BG_RAISED,corner_radius=8,
                         border_color=BORDER,border_width=1,**kw)
        self._hash,self._cnt,sz=data
        self._sz=float(sz or 0)
        self._expanded=False; self._detail=None
        wasted=self._sz*(self._cnt-1)/self._cnt if self._cnt>1 else 0

        hdr=ctk.CTkFrame(self,fg_color="transparent",cursor="hand2")
        hdr.pack(fill="x",padx=16,pady=12)
        hdr.bind("<Button-1>",self._toggle)

        self._arrow=ctk.CTkLabel(hdr,text="›",
            font=ctk.CTkFont(family="Segoe UI",size=14),
            text_color=TEXT_SEC,width=14)
        self._arrow.pack(side="left")
        self._arrow.bind("<Button-1>",self._toggle)

        ctk.CTkLabel(hdr,text=f"  Cluster {idx+1}",
            font=ctk.CTkFont(family="Segoe UI",size=11,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        ctk.CTkLabel(hdr,text=f"  ·  {self._cnt} copies",
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=TEXT_SEC).pack(side="left")

        ctk.CTkLabel(hdr,text=f"  ·  {self._sz:.1f} MB total",
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=AMBER).pack(side="left")

        ctk.CTkLabel(hdr,text=f"↓ {wasted:.1f} MB recoverable",
            font=ctk.CTkFont(family="Segoe UI",size=9,weight="bold"),
            text_color=GREEN).pack(side="right")

        ctk.CTkLabel(hdr,text=f"{self._hash[:12]}…",
            font=ctk.CTkFont(family="Segoe UI",size=9),
            text_color=TEXT_MUT).pack(side="right",padx=(0,12))

    def _toggle(self,e=None):
        self._expanded=not self._expanded
        self._arrow.configure(text="∨" if self._expanded else "›")
        if self._expanded:
            self._detail=ctk.CTkFrame(self,fg_color=BG_SURFACE,corner_radius=6)
            self._detail.pack(fill="x",padx=16,pady=(0,12))
            for i,(path,name,mb,mod) in enumerate(files_in(self._hash)):
                row=ctk.CTkFrame(self._detail,fg_color="transparent")
                row.pack(fill="x",padx=12,pady=3)
                dot_c=TEXT_SEC if i>0 else GREEN
                ctk.CTkLabel(row,text="·",font=ctk.CTkFont(size=14),
                    text_color=dot_c,width=12).pack(side="left")
                ctk.CTkLabel(row,text=f"  {name}",
                    font=ctk.CTkFont(family="Segoe UI",size=10,weight="bold"),
                    text_color=TEXT_PRI).pack(side="left")
                ctk.CTkLabel(row,text=f"  {float(mb or 0):.1f} MB",
                    font=ctk.CTkFont(family="Segoe UI",size=9),
                    text_color=AMBER).pack(side="left")
                ctk.CTkLabel(row,text=f"  {path}",
                    font=ctk.CTkFont(family="Segoe UI",size=9),
                    text_color=TEXT_MUT).pack(side="left")
        else:
            if self._detail: self._detail.destroy(); self._detail=None


class DuplicatesPanel(ctk.CTkFrame):
    def __init__(self,parent,**kw):
        super().__init__(parent,fg_color="transparent",**kw)
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=32,pady=(28,0))
        ctk.CTkLabel(hdr,text="Duplicates",
            font=ctk.CTkFont(family="Segoe UI",size=20,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")

        cl=clusters()
        wasted=sum(float(sz or 0)*(cnt-1)/cnt for _,cnt,sz in cl if cnt>1)
        ctk.CTkLabel(hdr,text=f"↓ {wasted:.1f} MB total recoverable",
            font=ctk.CTkFont(family="Segoe UI",size=10,weight="bold"),
            text_color=GREEN).pack(side="right")

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=32,pady=20)

        ctk.CTkLabel(self,text=f"{len(cl)} duplicate cluster{'s' if len(cl)!=1 else ''} found",
            font=ctk.CTkFont(family="Segoe UI",size=10),
            text_color=TEXT_SEC).pack(anchor="w",padx=32,pady=(0,12))

        scroll=ctk.CTkScrollableFrame(self,fg_color="transparent")
        scroll.pack(fill="both",expand=True,padx=32,pady=(0,24))

        if not cl:
            ctk.CTkLabel(scroll,text="No duplicates found.",
                font=ctk.CTkFont(family="Segoe UI",size=12),
                text_color=TEXT_MUT).pack(pady=48)
            return
        for i,c in enumerate(cl):
            Cluster(scroll,c,i).pack(fill="x",pady=4)
