import customtkinter as ctk
import sys, os
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.chat         import ChatPanel
from ui.dashboard    import DashboardPanel
from ui.suggestions  import SuggestionsPanel
from ui.duplicates   import DuplicatesPanel
from ui.file_browser import FileBrowserPanel
from ui.logs         import LogsPanel
from ui.watcher      import start_watcher, stop_watcher
from ui.theme import *
from core.settings   import load_settings, save_settings

ctk.set_default_color_theme("blue")

# Chat is first — LADO is an agent, not a file manager
NAV = [
    ("Agent Chat",  "◉", ChatPanel),
    ("Overview",    "○", DashboardPanel),
    ("Files",       "◫", FileBrowserPanel),
    ("Suggestions", "◎", SuggestionsPanel),
    ("Duplicates",  "⊞", DuplicatesPanel),
    ("Logs",        "≡", LogsPanel),
]


class NavBtn(ctk.CTkButton):
    def __init__(self, parent, text, icon, command):
        super().__init__(
            parent,
            text=f"  {icon}   {text}",
            width=188, height=40,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_SANS, size=12, weight="bold"),
            fg_color="transparent",
            text_color=TEXT_DIM,
            hover_color=SB_ACTIVE,
            anchor="w",
            border_width=0,
            command=command,
        )

    def activate(self):
        self.configure(
            fg_color=SB_ACTIVE,
            text_color=TEXT,
            border_color=GLASS_BORDER2,
            border_width=1,
        )

    def deactivate(self):
        self.configure(
            fg_color="transparent",
            text_color=TEXT_DIM,
            border_width=0,
        )


class LADOApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))
        
        self.title("LADO")
        self.geometry("1400x860")
        self.minsize(1100, 660)
        self.configure(fg_color=BG_DARK)
        self._active_btn = None
        self._build()
        start_watcher()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Windows taskbar fix
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LADO.App.1.0")
        except:
            pass
        # Set icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "lado.ico")
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(default=icon_path))

    def _on_close(self):
        stop_watcher()
        self.destroy()

    def _build(self):
        # ── Sidebar ──────────────────────────────────────────────
        sb = ctk.CTkFrame(self, fg_color=SB_BG, width=220, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        inner = ctk.CTkFrame(sb, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=28)

        # Logo image
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "lado_logo.png")
        if os.path.exists(logo_path):
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path),
                                    dark_image=Image.open(logo_path),
                                    size=(182, 56))
            ctk.CTkLabel(inner, image=logo_img, text="").pack(anchor="w", padx=4, pady=(0, 4))
        else:
            ctk.CTkLabel(inner, text="L.A.D.O.",
                font=ctk.CTkFont(family=FONT_SANS, size=18, weight="bold"),
                text_color=TEXT).pack(anchor="w", padx=8)

        # Watcher status pill
        from ui.watcher import WATCHDOG_AVAILABLE
        pill_bg = TEAL_DIM if WATCHDOG_AVAILABLE else AMBER_DIM
        pill_color = TEAL if WATCHDOG_AVAILABLE else AMBER
        pill_text = "● Agent active" if WATCHDOG_AVAILABLE else "● Install watchdog"

        pill = ctk.CTkFrame(inner, fg_color=pill_bg, corner_radius=20)
        pill.pack(anchor="w", padx=6, pady=(12, 0))
        ctk.CTkLabel(pill, text=pill_text,
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=pill_color).pack(padx=12, pady=5)

        # Nav label
        ctk.CTkLabel(inner, text="PANELS",
            font=ctk.CTkFont(family=FONT_SANS, size=9, weight="bold"),
            text_color=TEXT_DIM).pack(anchor="w", padx=10, pady=(24, 6))

        # Nav buttons
        self._btns = {}
        for label, icon, cls in NAV:
            b = NavBtn(inner, label, icon,
                       lambda l=label, c=cls: self._switch(l, c))
            b.pack(fill="x", padx=4, pady=2)
            self._btns[label] = b

        # Version
        ctk.CTkLabel(inner, text="v0.1  ·  Phase 1–5",
            font=ctk.CTkFont(family=FONT_SANS, size=9),
            text_color=TEXT_DIM).pack(side="bottom", pady=(0, 8))

        # Theme Toggle
        theme_val = self.settings.get("theme", "dark")
        self.theme_btn = ctk.CTkButton(inner, 
            text="☀️ Light Mode" if theme_val == "dark" else "🌙 Dark Mode",
            width=188, height=32, corner_radius=8,
            font=ctk.CTkFont(family=FONT_SANS, size=11, weight="bold"),
            fg_color="transparent", hover_color=SB_ACTIVE, text_color=TEXT_DIM,
            command=self._toggle_theme)
        self.theme_btn.pack(side="bottom", pady=(0, 16))

        # ── Content area ─────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        # Start on Agent Chat
        self._switch("Agent Chat", ChatPanel)

    def _switch(self, label, cls):
        if self._active_btn:
            self._active_btn.deactivate()
        self._btns[label].activate()
        self._active_btn = self._btns[label]
        for w in self.content.winfo_children():
            w.destroy()
        cls(self.content).pack(fill="both", expand=True)

    def _toggle_theme(self):
        current = self.settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        
        ctk.set_appearance_mode(new_theme)
        self.theme_btn.configure(text="☀️ Light Mode" if new_theme == "dark" else "🌙 Dark Mode")


if __name__ == "__main__":
    LADOApp().mainloop()