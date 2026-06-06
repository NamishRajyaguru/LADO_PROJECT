import customtkinter as ctk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.dashboard    import DashboardPanel
from ui.suggestions  import SuggestionsPanel
from ui.duplicates   import DuplicatesPanel
from ui.file_browser import FileBrowserPanel
from ui.chat         import ChatPanel
from ui.logs         import LogsPanel

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Minimal Monochrome Palette ─────────────────────────────
SB_BG     = "#0F0F10"
SB_TEXT   = "#FFFFFF"
SB_MUTED  = "#8A8F98"
SB_ACTIVE = "#2C2D31"

BG        = "#FFFFFF"
SURFACE   = "#F7F7F8"
CARD      = "#F7F7F8"
CARD2     = "#F1F1F3"
BORDER    = "#E6E6E9"
BORDER_HI = "#D1D1D6"
TEXT      = "#000000"
MUTED     = "#8A8F98"
DIM       = "#C4C5C8"
ACCENT    = "#000000"
ACCENTG   = "#000000"
ACCENTR   = "#000000"
ACCENTY   = "#000000"
ACCENTP   = "#000000"

NAV = [
    ("Dashboard",   "○", DashboardPanel),
    ("Files",       "◫", FileBrowserPanel),
    ("Suggestions", "◎", SuggestionsPanel),
    ("Duplicates",  "⊞", DuplicatesPanel),
    ("Chat",        "◉", ChatPanel),
    ("Logs",        "≡", LogsPanel),
]

class NavBtn(ctk.CTkButton):
    def __init__(self, parent, text, icon, command):
        super().__init__(parent, text=f"  {icon}   {text}",
            width=200, height=44, corner_radius=22,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="transparent", text_color=SB_MUTED, hover_color=SB_ACTIVE,
            anchor="w", command=command)

    def activate(self):
        self.configure(
            fg_color=SB_ACTIVE,
            text_color=SB_TEXT,
            border_width=0,
        )

    def deactivate(self):
        self.configure(
            fg_color="transparent",
            text_color=SB_MUTED,
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
        sb = ctk.CTkFrame(self, fg_color=SB_BG, width=240, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        inner = ctk.CTkFrame(sb, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=32)

        # Logo / Brand
        logo_row = ctk.CTkFrame(inner, fg_color="transparent")
        logo_row.pack(fill="x", padx=16, pady=(0, 32))
        
        ctk.CTkLabel(logo_row, text="●",
            font=ctk.CTkFont(size=20),
            text_color=SB_TEXT).pack(side="left")
        
        ctk.CTkLabel(logo_row, text="  LADO",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=SB_TEXT).pack(side="left")

        ctk.CTkLabel(inner, text="Local AI Data Organizer",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="normal"),
            text_color=SB_MUTED).pack(anchor="w", padx=20, pady=(4, 0))

        # divider removed for smoothness

        ctk.CTkLabel(inner, text="NAVIGATE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=SB_MUTED).pack(anchor="w", padx=22, pady=(32, 12))

        self._btns = {}
        for label, icon, cls in NAV:
            b = NavBtn(inner, icon, label,
                       lambda l=label, c=cls: self._switch(l, c))
            b.pack(fill="x", padx=12, pady=2)
            self._btns[label] = b

        # bottom version tag
        ctk.CTkLabel(inner, text="v0.1  ·  Phase 1–3",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=DIM).pack(side="bottom", pady=(0, 16))

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