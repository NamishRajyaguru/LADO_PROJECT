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

BG_BASE    = "#050508"
BG_SURFACE = "#0c0c12"
BG_RAISED  = "#121219"
BORDER     = "#1e1e2e"
TEXT_PRI   = "#f0f0f8"
TEXT_SEC   = "#6b6b8a"
ACCENT     = "#4d9de0"

NAV = [
    ("Dashboard",   "◈", DashboardPanel),
    ("Files",       "◫", FileBrowserPanel),
    ("Suggestions", "◎", SuggestionsPanel),
    ("Duplicates",  "⊞", DuplicatesPanel),
    ("Chat",        "◉", ChatPanel),
]

class NavBtn(ctk.CTkButton):
    def __init__(self, parent, icon, label, cmd):
        super().__init__(
            parent,
            text=f" {icon}   {label}",
            anchor="w", height=38,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            text_color=TEXT_SEC,
            hover_color=BG_RAISED,
            corner_radius=6,
            border_width=0,
            command=cmd,
        )
    def activate(self):
        self.configure(
            fg_color=BG_RAISED,
            text_color=ACCENT,
            border_color="#1e2a38",
            border_width=1,
        )
    def deactivate(self):
        self.configure(fg_color="transparent", text_color=TEXT_SEC, border_width=0)


class LADOApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LADO")
        self.geometry("1300x780")
        self.minsize(960, 600)
        self.configure(fg_color=BG_BASE)
        self._active_btn = None
        self._build()

    def _build(self):
        # ── Sidebar ──────────────────────────────────────
        self.sb = ctk.CTkFrame(self, fg_color=BG_SURFACE, width=220, corner_radius=0)
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        # thin right border on sidebar
        ctk.CTkFrame(self.sb, fg_color=BORDER, width=1).pack(side="right", fill="y")

        inner = ctk.CTkFrame(self.sb, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=0)

        # Wordmark
        wm = ctk.CTkFrame(inner, fg_color="transparent")
        wm.pack(fill="x", padx=20, pady=(28, 0))
        ctk.CTkLabel(wm, text="LADO",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRI).pack(anchor="w")
        ctk.CTkLabel(wm, text="autonomous file agent",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=TEXT_SEC).pack(anchor="w", pady=(1,0))

        # Divider
        ctk.CTkFrame(inner, fg_color=BORDER, height=1).pack(fill="x", padx=20, pady=22)

        # Nav label
        ctk.CTkLabel(inner, text="MENU",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=TEXT_SEC).pack(anchor="w", padx=22, pady=(0,8))

        # Nav buttons
        self._btns = {}
        for label, icon, cls in NAV:
            b = NavBtn(inner, icon, label, lambda l=label, c=cls: self._switch(l, c))
            b.pack(fill="x", padx=10, pady=1)
            self._btns[label] = b

        # Bottom tag
        ctk.CTkLabel(inner, text="Phase 1–3  ·  v0.1",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=TEXT_SEC).pack(side="bottom", pady=18)

        # ── Content ───────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
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
