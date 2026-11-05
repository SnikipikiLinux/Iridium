"""
ui/formatting_tab.py — paste ANY text containing YouTube links, extract & format.
"""

import re

import customtkinter as ctk

from ui import theme
from ui.widgets import PlaceholderTextbox


_YT_URL_RE = re.compile(
    r"(?:https?://)?"
    r"(?:www\.|m\.)?"
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{6,})"
)


class FormattingTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # instruction label — bigger, still italic, still muted
        ctk.CTkLabel(
            self,
            text=(
                "...This is where you enter ALL your links to format them. "
                "Paste them all in — the program will automatically format "
                "them for you to paste into the downloader!"
            ),
            font=("Segoe UI", 14, "italic"),
            text_color=theme.FG_MUTED,
            wraplength=640,
            justify="center",
        ).pack(pady=(20, 14), padx=20)

        # textbox — one notch bigger for readability
        self.textbox = PlaceholderTextbox(
            self,
            placeholder="Paste ANY text containing YouTube links here...",
            width=640,
            height=220,
            font=("Consolas", 13),
            fg_color=theme.BG_INPUT,
            text_color=theme.FG_TEXT,
            border_color=theme.BG_INPUT,
            border_width=1,
            corner_radius=8,
            wrap="word",
            placeholder_color=theme.FG_DIM,
        )
        self.textbox.pack(pady=(0, 10))

        # status strip
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 12),
            text_color=theme.FG_DIM,
        )
        self.status_label.pack(pady=(0, 10))

        # action button — taller
        self.action_btn = ctk.CTkButton(
            self,
            text="Format!",
            width=170,
            height=46,
            font=("Segoe UI", 13, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE,
            corner_radius=8,
            command=self._on_action,
        )
        self.action_btn.pack(pady=(0, 12))

        self._formatted = None

    # ------------------------------------------------------------------ actions
    def _on_action(self):
        if self._formatted is None:
            raw = self.textbox.get_value()
            if not raw:
                return
            urls = self._extract(raw)
            if not urls:
                self.status_label.configure(
                    text="No YouTube links found.", text_color=theme.FG_DIM
                )
                return
            self._formatted = "\n".join(urls)
            self.textbox.set_value(self._formatted)
            self.action_btn.configure(text="Copy!")
            self.status_label.configure(
                text=f"Found {len(urls)} link{'s' if len(urls) != 1 else ''}.",
                text_color=theme.FG_MUTED,
            )
        else:
            self._copy()
            self.action_btn.configure(text="Copied!", fg_color=theme.ACCENT_PRESS)
            self.after(900, self._reset_button)

    def _reset_button(self):
        self.action_btn.configure(text="Copy!", fg_color=theme.ACCENT)

    # ------------------------------------------------------------------ extract
    @staticmethod
    def _extract(raw):
        seen = set()
        out = []
        for m in _YT_URL_RE.finditer(raw):
            vid = m.group(1)
            url = f"https://www.youtube.com/watch?v={vid}"
            if url not in seen:
                seen.add(url)
                out.append(url)
        return out

    # ------------------------------------------------------------------ clipboard
    def _copy(self):
        if not self._formatted:
            return
        self.clipboard_clear()
        self.clipboard_append(self._formatted)