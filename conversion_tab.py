"""ui/conversion_tab.py — conversion tab: select downloads, convert to mp3."""

import os
import customtkinter as ctk

from ui import theme
from ui.widgets import SegmentedProgressBar
from core import history as history_mod


_VIDEO_EXTS = (".mp4", ".webm", ".mkv", ".mov", ".avi", ".flv")


class ConversionTab(ctk.CTkFrame):
    def __init__(self, master, on_convert, on_cancel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_convert = on_convert
        self._checkboxes = {}

        ctk.CTkLabel(
            self,
            text=(
                "Here is the Conversion part, if you are happy with your MP4, "
                "Congrats! if not, there is this tool over here, just select "
                "from the list the video you are trying to convert, and we are "
                "gonna convert it for you!"
            ),
            font=("Segoe UI", 13, "italic"),
            text_color=theme.FG_MUTED,
            wraplength=640,
            justify="center",
        ).pack(pady=(22, 14), padx=20)

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=32, pady=(0, 6))

        ctk.CTkLabel(
            header_row,
            text="Your downloaded videos:",
            font=("Segoe UI", 12, "bold"),
            text_color=theme.FG_TEXT,
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            header_row, text="↻ Refresh", width=80, height=24,
            font=("Segoe UI", 11, "bold"),
            fg_color=theme.BG_INPUT, hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT, corner_radius=6,
            command=self.refresh,
        ).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.BG_INPUT,
            corner_radius=8,
            width=640,
            height=150,
        )
        self.list_frame.pack(pady=(0, 8))

        # ---- delete-mp4 option ----
        self._delete_var = ctk.BooleanVar(value=False)
        self.delete_cb = ctk.CTkCheckBox(
            self,
            text="Delete MP4 after conversion?",
            variable=self._delete_var,
            font=("Segoe UI", 12),
            text_color=theme.FG_TEXT,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            border_color=theme.FG_DIM,
            checkmark_color=theme.BG_BASE,
        )
        self.delete_cb.pack(pady=(0, 8))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 10))

        self.convert_btn = ctk.CTkButton(
            btn_row, text="Convert to MP3", width=200, height=42,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE, corner_radius=8,
            command=self._on_click_convert,
        )
        self.convert_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_row, text="Cancel", width=100, height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT, hover_color="#5a1f1f",
            text_color=theme.FG_MUTED, corner_radius=6,
            command=on_cancel, state="disabled",
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
            self.progress_row, text="",
            font=("Segoe UI", 11), text_color=theme.FG_DIM,
        )
        self.status_label.pack()

        self.progress_row.pack_forget()

        self.after(80, self.refresh)

    # ------------------------------------------------------------------ refresh
    def refresh(self):
        for child in list(self.list_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self._checkboxes.clear()

        entries = history_mod.load_history()
        videos = []
        for e in entries:
            try:
                path = e.get("path", "")
                kind = e.get("kind", "")
                if kind != "video":
                    continue
                if not path or not os.path.isfile(path):
                    continue
                if not any(path.lower().endswith(ext) for ext in _VIDEO_EXTS):
                    continue
                videos.append(e)
            except Exception:
                continue

        if not videos:
            ctk.CTkLabel(
                self.list_frame,
                text="No videos downloaded yet. Download a video first!",
                font=("Segoe UI", 11),
                text_color=theme.FG_DIM,
            ).pack(pady=30)
            return

        for e in videos:
            self._render_checkbox(e)

    def _render_checkbox(self, entry):
        path = entry.get("path", "")
        title = entry.get("title", "Unknown")
        date = entry.get("date", "")

        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=3)

        var = ctk.BooleanVar(value=False)
        self._checkboxes[path] = var

        cb = ctk.CTkCheckBox(
            row,
            text=title,
            variable=var,
            font=("Segoe UI", 12),
            text_color=theme.FG_TEXT,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            border_color=theme.FG_DIM,
            checkmark_color=theme.BG_BASE,
        )
        cb.pack(anchor="w", fill="x")

        if date:
            ctk.CTkLabel(
                row, text=date,
                font=("Segoe UI", 9),
                text_color=theme.FG_DIM,
                anchor="w",
            ).pack(anchor="w", padx=(26, 0))

    def _on_click_convert(self):
        paths = [p for p, var in self._checkboxes.items() if var.get()]
        if not paths:
            self.show_progress()
            self.status_label.configure(
                text="Select at least one video.", text_color="#ff5a5a",
            )
            return
        delete = bool(self._delete_var.get())
        self._on_convert(paths, delete)

    # ------------------------------------------------------------------ external API
    def show_progress(self):
        self.progress_row.pack(pady=(8, 0), fill="x")

    def hide_progress(self):
        self.progress_row.pack_forget()

    def set_progress(self, frac):
        try:
            self.progress_bar.set(frac)
        except Exception:
            pass

    def set_status(self, text, error=False):
        try:
            self.status_label.configure(
                text=text,
                text_color="#ff5a5a" if error else theme.FG_DIM,
            )
        except Exception:
            pass

    def set_converting(self, converting):
        try:
            self.convert_btn.configure(
                state="disabled" if converting else "normal",
                text="Converting..." if converting else "Convert to MP3",
            )
            self.cancel_btn.configure(state="normal" if converting else "disabled")
            # prevent mid-run flips
            self.delete_cb.configure(
                state="disabled" if converting else "normal"
            )
        except Exception:
            pass