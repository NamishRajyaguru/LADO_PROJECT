import customtkinter as ctk, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG_BASE="#050508";BG_SURFACE="#0c0c12";BG_RAISED="#121219";BG_HOVER="#1a1a24"
BORDER="#1e1e2e";TEXT_PRI="#f0f0f8";TEXT_SEC="#6b6b8a";TEXT_MUT="#2e2e48"
BLUE="#4d9de0";GREEN="#3ddc84";AMBER="#f5a623"

COLS  = ["Name","Ext","Size (MB)","Modified","Path"]
WIDTHS= [210,60,90,130,300]

def load(ext=None, min_mb=None, search=None):
    try:
        conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
        q="SELECT name,extension,size_mb,modified_time,path FROM files"
        conds=[]; params=[]
        if ext and ext!="All":
            conds.append("LOWER(extension)=LOWER(?)"); params.append(ext.lstrip("."))
        if min_mb:
            try: conds.append("size_mb>?"); params.append(float(min_mb))
            except: pass
        if search:
            conds.append("LOWER(name) LIKE LOWER(?)"); params.append(f"%{search}%")
        if conds: q+=" WHERE "+" AND ".join(conds)
        q+=" ORDER BY size_mb DESC LIMIT 500"
        cur.execute(q, params); rows=cur.fetchall(); conn.close(); return rows
    except: return []

def get_exts():
    try:
        c=sqlite3.connect(DB_PATH).cursor()
        c.execute("SELECT DISTINCT LOWER(extension) FROM files WHERE extension IS NOT NULL ORDER BY extension")
        return ["All"]+[r[0] for r in c.fetchall() if r[0]]
    except: return ["All"]


class FileBrowserPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        # Header
        hdr=ctk.CTkFrame(self,fg_color="transparent")
        hdr.pack(fill="x",padx=32,pady=(28,0))
        ctk.CTkLabel(hdr,text="Files",
            font=ctk.CTkFont(family="Segoe UI",size=20,weight="bold"),
            text_color=TEXT_PRI).pack(side="left")
        self._cnt=ctk.CTkLabel(hdr,text="",
            font=ctk.CTkFont(family="Segoe UI",size=10),text_color=TEXT_SEC)
        self._cnt.pack(side="right")

        ctk.CTkFrame(self,fg_color=BORDER,height=1).pack(fill="x",padx=32,pady=20)

        # Filter bar
        fb=ctk.CTkFrame(self,fg_color=BG_RAISED,corner_radius=8,
                        border_color=BORDER,border_width=1)
        fb.pack(fill="x",padx=32,pady=(0,16))

        self._sv=ctk.StringVar()
        ctk.CTkEntry(fb,textvariable=self._sv,placeholder_text="Search files…",
            width=200,height=32,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=BG_BASE,border_color=BORDER,border_width=1,
            text_color=TEXT_PRI).pack(side="left",padx=12,pady=10)

        self._ev=ctk.StringVar(value="All")
        ctk.CTkOptionMenu(fb,variable=self._ev,values=get_exts(),
            width=110,height=32,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=BG_BASE,button_color=BG_HOVER,
            dropdown_fg_color=BG_RAISED,text_color=TEXT_SEC).pack(side="left",padx=(0,8))

        self._mv=ctk.StringVar()
        ctk.CTkEntry(fb,textvariable=self._mv,placeholder_text="Min MB",
            width=80,height=32,font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=BG_BASE,border_color=BORDER,border_width=1,
            text_color=TEXT_PRI).pack(side="left",padx=(0,10))

        ctk.CTkButton(fb,text="Apply",width=72,height=32,
            font=ctk.CTkFont(family="Segoe UI",size=10),
            fg_color=BLUE,text_color="#050508",hover_color="#6bb3e8",
            corner_radius=6,command=self._apply).pack(side="left")

        # Column headers
        ch=ctk.CTkFrame(self,fg_color=BG_SURFACE,corner_radius=0,height=30)
        ch.pack(fill="x",padx=32); ch.pack_propagate(False)
        for i,(col,w) in enumerate(zip(COLS,WIDTHS)):
            ctk.CTkLabel(ch,text=col,
                font=ctk.CTkFont(family="Segoe UI",size=9,weight="bold"),
                text_color=TEXT_SEC,width=w,anchor="w").pack(
                side="left",padx=(16 if i==0 else 6,0))

        # Rows
        self._scroll=ctk.CTkScrollableFrame(self,fg_color="transparent",corner_radius=0)
        self._scroll.pack(fill="both",expand=True,padx=32,pady=(0,24))
        self._load()

    def _load(self,ext=None,min_mb=None,search=None):
        for w in self._scroll.winfo_children(): w.destroy()
        rows=load(ext,min_mb,search)
        self._cnt.configure(text=f"{len(rows)} files")
        for i,r in enumerate(rows):
            bg=BG_RAISED if i%2==0 else BG_SURFACE
            row=ctk.CTkFrame(self._scroll,fg_color=bg,corner_radius=0,height=26)
            row.pack(fill="x"); row.pack_propagate(False)
            vals=[str(r[0])[:35], f".{r[1]}" if r[1] else "",
                  f"{float(r[2] or 0):.1f}", str(r[3] or "")[:16], str(r[4])]
            colors=[TEXT_PRI,BLUE,AMBER,TEXT_SEC,TEXT_MUT+"aa"]
            for j,(v,c,w) in enumerate(zip(vals,colors,WIDTHS)):
                ctk.CTkLabel(row,text=v,
                    font=ctk.CTkFont(family="Segoe UI",size=10),
                    text_color=c,width=w,anchor="w").pack(
                    side="left",padx=(16 if j==0 else 6,0))

    def _apply(self):
        e=self._ev.get() if self._ev.get()!="All" else None
        self._load(ext=e,min_mb=self._mv.get().strip() or None,
                   search=self._sv.get().strip() or None)
