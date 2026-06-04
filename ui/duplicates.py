import customtkinter as ctk, sqlite3, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

BG="#07080f";SURFACE="#0e0f1a";CARD="#13141f";CARD2="#181926"
BORDER="#1f2035";BORDER_HI="#2a2d4a"
TEXT="#eeeef5";MUTED="#5a5b7a";DIM="#272840"
ACCENT="#5b8dee";ACCENTG="#3ecf8e";ACCENTR="#e05c72";ACCENTY="#f0a84a"
SK1="#13141f";SK2="#1c1d2e"

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


class SkeletonCluster(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=12,
                         border_color=BORDER, border_width=1, **kw)
        self._phase=0; self._bars=[]
        row=ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=18)
        for w,side in [(130,"left"),(80,"left"),(100,"left"),(150,"right")]:
            b=ctk.CTkFrame(row, fg_color=SK2, corner_radius=3, width=w, height=10)
            b.pack(side=side, padx=(0 if side=="right" else 14,0))
            b.pack_propagate(False)
            self._bars.append(b)
        self._tick()

    def _tick(self):
        if not self.winfo_exists(): return
        self._phase=(self._phase+1)%24
        c=SK2 if self._phase<12 else SK1
        for b in self._bars:
            if b.winfo_exists(): b.configure(fg_color=c)
        self.after(90,self._tick)


class Cluster(ctk.CTkFrame):
    def __init__(self, parent, data, idx, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=12,
                         border_color=BORDER, border_width=1, **kw)
        self._hash,self._cnt,sz=data
        self._sz=float(sz or 0)
        self._expanded=False; self._detail=None
        wasted=self._sz*(self._cnt-1)/self._cnt if self._cnt>1 else 0

        # top accent
        ctk.CTkFrame(self, fg_color=ACCENTR, height=2, corner_radius=0).pack(fill="x", side="top")

        hdr=ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        hdr.pack(fill="x", padx=20, pady=14)
        hdr.bind("<Button-1>", self._toggle)

        self._arrow=ctk.CTkLabel(hdr, text="›",
            font=ctk.CTkFont(family="Segoe UI", size=16), text_color=MUTED, width=16)
        self._arrow.pack(side="left")
        self._arrow.bind("<Button-1>", self._toggle)

        ctk.CTkLabel(hdr, text=f"  Cluster {idx+1}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  ·  {self._cnt} copies",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=MUTED).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  ·  {self._sz:.1f} MB total",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=ACCENTY).pack(side="left")

        # recoverable badge
        badge=ctk.CTkFrame(hdr, fg_color=CARD2, corner_radius=6)
        badge.pack(side="right")
        ctk.CTkLabel(badge, text=f"  ↓ {wasted:.1f} MB free  ",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=ACCENTG).pack(padx=2, pady=4)

        ctk.CTkLabel(hdr, text=f"{self._hash[:10]}…",
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=DIM).pack(side="right", padx=(0,10))

    def _toggle(self, e=None):
        self._expanded=not self._expanded
        self._arrow.configure(text="∨" if self._expanded else "›")
        if self._expanded:
            self._detail=ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
            self._detail.pack(fill="x", padx=14, pady=(0,14))
            for i,(path,name,mb,mod) in enumerate(files_in(self._hash)):
                row=ctk.CTkFrame(self._detail, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=4)
                dot_c=ACCENTG if i==0 else MUTED
                ctk.CTkLabel(row, text="●",
                    font=ctk.CTkFont(size=7), text_color=dot_c, width=12).pack(side="left")
                ctk.CTkLabel(row, text=f"  {name}",
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    text_color=TEXT).pack(side="left")
                ctk.CTkLabel(row, text=f"  {float(mb or 0):.1f} MB",
                    font=ctk.CTkFont(family="Segoe UI", size=9),
                    text_color=ACCENTY).pack(side="left")
                ctk.CTkLabel(row, text=f"  {path}",
                    font=ctk.CTkFont(family="Segoe UI", size=9),
                    text_color=DIM).pack(side="left")
        else:
            if self._detail: self._detail.destroy(); self._detail=None


class DuplicatesPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=36, pady=(32,0))
        left=ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Duplicates",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Groups of identical files — expand to see paths",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED).pack(anchor="w", pady=(2,0))
        self._stats=ctk.CTkLabel(hdr, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENTG)
        self._stats.pack(side="right")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=36, pady=24)

        self._cnt=ctk.CTkLabel(self, text="",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=MUTED)
        self._cnt.pack(anchor="w", padx=36, pady=(0,12))

        self._scroll=ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=36, pady=(0,28))

        # skeletons immediately
        for _ in range(6):
            SkeletonCluster(self._scroll).pack(fill="x", pady=6)

        threading.Thread(target=self._bg, daemon=True).start()

    def _bg(self):
        cl=clusters()
        self.after(0, lambda:self._render(cl))

    def _render(self, cl):
        if not self.winfo_exists(): return
        wasted=sum(float(sz or 0)*(cnt-1)/cnt for _,cnt,sz in cl if cnt>1)
        for w in self._scroll.winfo_children(): w.destroy()
        self._stats.configure(text=f"↓ {wasted:.1f} MB recoverable")
        self._cnt.configure(text=f"{len(cl)} cluster{'s' if len(cl)!=1 else ''} found")
        if not cl:
            ctk.CTkLabel(self._scroll, text="No duplicates found.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=DIM).pack(pady=56)
            return
        self._batch(cl, 0)

    def _batch(self, cl, start):
        if not self.winfo_exists(): return
        end=min(start+20, len(cl))
        for i in range(start, end):
            Cluster(self._scroll, cl[i], i).pack(fill="x", pady=6)
        if end<len(cl):
            self._scroll.after(10, lambda:self._batch(cl, end))
