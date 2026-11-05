"""ui/multi_download_tab.py — paste-many-links batch download UI."""

import customtkinter as ctk

from ui import theme
from ui.widgets import PlaceholderTextbox, SegmentedProgressBar


class MultiDownloadTab(ctk.CTkFrame):
    def __init__(self, master, on_download_all, on_cancel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self,
            text=(
                "Hi! This is where you can input more links, and the fancy gods "
                "will sort them, and will automatically group them in a tidy "
                "folder wherever you set the destination to! "
                "(settings - destination folder)"
            ),
            font=("Segoe UI", 13, "italic"),
            text_color=theme.FG_MUTED,
            wraplength=640,
            justify="center",
        ).pack(pady=(22, 14), padx=20)

        self.textbox = PlaceholderTextbox(
            self,
            placeholder=(
                "Paste multiple YouTube links here — one per line, or all "
                "jumbled together. I'll sort them out."
            ),
            width=640,
            height=200,
            font=("Consolas", 12),
            fg_color=theme.BG_INPUT,
            text_color=theme.FG_TEXT,
            border_color=theme.BG_INPUT,
            border_width=1,
            corner_radius=8,
            wrap="word",
            placeholder_color=theme.FG_DIM,
        )
        self.textbox.pack(pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 12))

        self.download_btn = ctk.CTkButton(
            btn_row,
            text="Download All",
            width=180,
            height=42,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE,
            corner_radius=8,
            command=on_download_all,
        )
        self.download_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT,
            hover_color="#5a1f1f",
            text_color=theme.FG_MUTED,
            corner_radius=6,
            command=on_cancel,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", pady=(10, 0))

        self.progress_row = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_row.pack(pady=(8, 0), fill="x")

        self.progress_bar = SegmentedProgressBar(
            self.progress_row, segments=26, width=640, height=18,
        )
        self.progress_bar.pack(pady=(0, 6))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.progress_row,
            text="",
            font=("Segoe UI", 11),
            text_color=theme.FG_DIM,
        )
        self.status_label.pack()

        self.progress_row.pack_forget()

    def show_progress(self):
        self.progress_row.pack(pady=(8, 0), fill="x")

    def hide_progress(self):
        self.progress_row.pack_forget()