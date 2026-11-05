"""
ui/credits.py — themed credits window.

Frameless Toplevel, centered over the main window. Matches the visual style
of the Discord confirmation dialog. Closes on Escape, X button, or Enter.
"""

import customtkinter as ctk

from ui import theme


class CreditsWindow(ctk.CTkToplevel):
    W, H = 420, 260

    def __init__(self, parent):
        super().__init__(parent)

        self.overrideredirect(True)
        self.configure(fg_color=theme.BG_PANEL)
        self.resizable(False, False)

        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - self.W) // 2
        y = py + (ph - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        # accent strip
        ctk.CTkFrame(self, height=2, fg_color=theme.ACCENT, corner_radius=0).pack(
            side="top", fill="x"
        )

        # header row with title + close button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(
            header,
            text="Credits",
            font=("Segoe UI", 15, "bold"),
            text_color=theme.FG_TEXT,
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="✕",
            width=26,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color=theme.MIN_HOVER,
            text_color=theme.FG_MUTED,
            font=theme.FONT_ICON,
            command=self.close,
        ).pack(side="right")

        # divider
        ctk.CTkFrame(self, height=1, fg_color=theme.BG_INPUT, corner_radius=0).pack(
            fill="x", padx=20, pady=(0, 20)
        )

        # copyright line
        ctk.CTkLabel(
            self,
            text="2026 Copyright @HeySniki",
            font=("Segoe UI", 14, "bold"),
            text_color=theme.FG_TEXT,
        ).pack(pady=(0, 16))

        # credits body
        ctk.CTkLabel(
            self,
            text="Massively helped by AI's DeepSeek and Claude",
            font=("Segoe UI", 13),
            text_color=theme.FG_MUTED,
            wraplength=self.W - 60,
            justify="center",
        ).pack(padx=20)

        self.bind("<Escape>", lambda e: self.close())
        self.bind("<Return>", lambda e: self.close())
        self.after(50, self.focus_force)

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass