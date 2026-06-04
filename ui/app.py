import customtkinter as ctk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.dashboard    import DashboardPanel
from ui.suggestions  import SuggestionsPanel
from ui.duplicates   import DuplicatesPanel
from ui.file_browser import FileBrowserPanel
from ui.chat         import ChatPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette ────────────────────────────────────────────────────
BG        = "#07080f"
SURFACE   = "#0e0f1a"
CARD      = "#13141f"
CARD2     = "#181926"
BORDER    = "#1f2035"
BORDER_HI = "#2a2d4a"
TEXT      = "#eeeef5"
MUTED     = "#5a5b7a"
DIM       = "#272840"
ACCENT    = "#5b8dee"   # soft blue
ACCENTG   = "#3ecf8e"   # green
ACCENTR   = "#e05c72"   # rose
ACCENTY   = "#f0a84a"   # amber

NAV = [
    ("Dashboard",   "○", DashboardPanel),
    ("Files",       "◫", FileBrowserPanel),
    ("Suggestions", "◎", SuggestionsPanel),
    ("Duplicates",  "⊞", DuplicatesPanel),
    ("Chat",        "◉", ChatPanel),
]

class NavBtn(ctk.CTkButton):
    def __init__(self, parent, icon, label, cmd):
        super().__init__(
            parent,
            text=f"  {icon}   {label}",
            anchor="w", height=40,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            text_color=MUTED,
            hover_color=CARD2,
            corner_radius=8,
            border_width=0,
            command=cmd,
        )

    def activate(self):
        self.configure(
            fg_color=CARD2,
            text_color=TEXT,
            border_color=BORDER_HI,
            border_width=1,
        )

    def deactivate(self):
        self.configure(
            fg_color="transparent",
            text_color=MUTED,
            border_width=0,
        )


class LADOApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LADO")
        self.geometry("1360x820")
        self.minsize(1000, 640)
        self.configure(fg_color=BG)
        self._active_btn = None
        self._build()

    def _build(self):
        # ── Sidebar ───────────────────────────────────────────
        sb = ctk.CTkFrame(self, fg_color=SURFACE, width=230, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # hairline border
        ctk.CTkFrame(sb, fg_color=BORDER, width=1).pack(side="right", fill="y")

        inner = ctk.CTkFrame(sb, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        # Logo block
        logo = ctk.CTkFrame(inner, fg_color="transparent")
        logo.pack(fill="x", padx=22, pady=(32, 0))

        # accent dot
        dot_row = ctk.CTkFrame(logo, fg_color="transparent")
        dot_row.pack(anchor="w")
        ctk.CTkFrame(dot_row, fg_color=ACCENT, width=8, height=8,
                     corner_radius=4).pack(side="left", pady=2)
        ctk.CTkLabel(dot_row, text="  LADO",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=TEXT).pack(side="left")

        ctk.CTkLabel(inner, text="autonomous file agent",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=DIM).pack(anchor="w", padx=22, pady=(4, 0))

        # divider
        ctk.CTkFrame(inner, fg_color=BORDER, height=1).pack(
            fill="x", padx=22, pady=28)

        ctk.CTkLabel(inner, text="NAVIGATE",
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color=DIM).pack(anchor="w", padx=24, pady=(0, 10))

        self._btns = {}
        for label, icon, cls in NAV:
            b = NavBtn(inner, icon, label,
                       lambda l=label, c=cls: self._switch(l, c))
            b.pack(fill="x", padx=12, pady=2)
            self._btns[label] = b

        # bottom version tag
        ctk.CTkFrame(inner, fg_color=BORDER, height=1).pack(
            fill="x", padx=22, side="bottom", pady=(0, 14))
        ctk.CTkLabel(inner, text="v0.1  ·  Phase 1–3",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=DIM).pack(side="bottom", pady=(0, 6))

        # ── Content ───────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        self._switch("Dashboard", DashboardPanel)

    def _switch(self, label, cls):
        if self._active_btn:
            self._active_btn.deactivate()
        self._btns[label].activate()
        self._active_btn = self._btns[label]
        for w in self.content.winfo_children():
            w.destroy()
        cls(self.content).pack(fill="both", expand=True)


if __name__ == "__main__":
    LADOApp().mainloop()
