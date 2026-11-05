import customtkinter as ctk

from ui import theme


class ExitConfirmDialog(ctk.CTkToplevel):
    W, H = 360, 160

    def __init__(self, parent, on_confirm, on_cancel):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        self.overrideredirect(True)
        self.configure(fg_color=theme.BG_PANEL)
        self.resizable(False, False)

        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - self.W) // 2
        y = py + (ph - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        ctk.CTkFrame(self, height=2, fg_color=theme.ACCENT, corner_radius=0).pack(
            side="top", fill="x"
        )

        ctk.CTkLabel(
            self,
            text="Are you sure you wanna leave the program?",
            font=("Segoe UI", 13),
            text_color=theme.FG_TEXT,
            wraplength=self.W - 48,
            justify="center",
        ).pack(pady=(26, 22), padx=24)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 22))

        ctk.CTkButton(
            btn_row,
            text="No",
            width=110, height=36,
            font=theme.FONT_BUTTON,
            fg_color=theme.BG_INPUT,
            hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            corner_radius=8,
            command=self._cancel,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Yes",
            width=110, height=36,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE,
            corner_radius=8,
            command=self._confirm,
        ).pack(side="left")

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._confirm())
        self.after(50, self.focus_force)

    def _confirm(self):
        self.destroy()
        self._on_confirm()

    def _cancel(self):
        self.destroy()
        self._on_cancel()