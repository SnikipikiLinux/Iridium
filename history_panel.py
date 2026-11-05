"""ui/history_panel.py — in-window history drawer.

Same visual pattern as SettingsPanel: a CTkFrame that slides down from just
below the title bar via raw Tcl `place` calls. Content is a scrollable list
of past downloads, newest first.
"""

import customtkinter as ctk

from ui import theme
from core import history as history_mod


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _ease_in_cubic(t):
    t = max(0.0, min(1.0, t))
    return t * t * t


class HistoryPanel(ctk.CTkFrame):
    """In-window history drawer, anchored under the title bar."""

    ANIM_FRAMES = 20
    FRAME_MS = 16
    PANEL_H = 460

    def __init__(self, master, on_close):
        super().__init__(
            master,
            fg_color=theme.BG_PANEL,
            corner_radius=0,
            border_width=0,
            width=800,
            height=self.PANEL_H,
        )
        self._on_close_cb = on_close

        self._alive = True
        self._visible = False
        self._animating = False
        self._anim_id = None
        self._current_height = 0

        self._build_content()
        self.bind("<Destroy>", self._on_destroy, add="+")

    # ------------------------------------------------------------------ lifecycle
    def _on_destroy(self, _event=None):
        self._alive = False
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    def _schedule(self, ms, fn):
        if not self._alive:
            return
        try:
            self._anim_id = self.after(ms, fn)
        except Exception:
            self._anim_id = None

    def _raw_place(self, height=None, relwidth=None):
        args = ["place", self._w, "-x", "0", "-y", "0"]
        if relwidth is not None:
            args += ["-relwidth", str(relwidth)]
        if height is not None:
            args += ["-height", str(int(height))]
        self.tk.call(*args)

    def _raw_place_forget(self):
        try:
            self.tk.call("place", "forget", self._w)
        except Exception:
            pass

    # ------------------------------------------------------------------ content
    def _build_content(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(
            header, text="History",
            font=("Segoe UI", 14, "bold"),
            text_color=theme.FG_TEXT,
        ).pack(side="left")
        ctk.CTkButton(
            header, text="✕", width=26, height=26, corner_radius=6,
            fg_color="transparent", hover_color=theme.MIN_HOVER,
            text_color=theme.FG_MUTED, font=theme.FONT_ICON,
            command=self.close,
        ).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=theme.BG_INPUT, corner_radius=0).pack(
            fill="x", padx=18, pady=(4, 10)
        )

        self.entries_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.entries_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        ctk.CTkButton(
            self, text="Clear History", height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT, hover_color="#5a1f1f",
            text_color=theme.FG_TEXT, corner_radius=6,
            command=self._clear_history,
        ).pack(fill="x", padx=18, pady=(0, 14))

        self._refresh_entries()

    def _refresh_entries(self):
        # wipe existing
        for child in list(self.entries_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        try:
            entries = history_mod.load_history()
        except Exception:
            entries = []

        if not entries:
            ctk.CTkLabel(
                self.entries_frame,
                text="No downloads yet.",
                font=("Segoe UI", 12),
                text_color=theme.FG_DIM,
            ).pack(pady=40)
            return

        for entry in entries:
            self._render_entry(entry)

    def _render_entry(self, entry):
        row = ctk.CTkFrame(
            self.entries_frame,
            fg_color=theme.BG_INPUT,
            corner_radius=6,
        )
        row.pack(fill="x", pady=3, padx=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            inner,
            text=entry.get("title", "Unknown"),
            font=("Segoe UI", 12, "bold"),
            text_color=theme.FG_TEXT,
            anchor="w",
            wraplength=700,
            justify="left",
        ).pack(fill="x")

        kind = entry.get("kind", "video").capitalize()
        date = entry.get("date", "")
        meta = " · ".join(p for p in (kind, date) if p)
        ctk.CTkLabel(
            inner,
            text=meta,
            font=("Segoe UI", 10),
            text_color=theme.FG_DIM,
            anchor="w",
        ).pack(fill="x")

    def _clear_history(self):
        try:
            history_mod.clear_history()
        except Exception:
            pass
        self._refresh_entries()

    # ------------------------------------------------------------------ open / close
    def is_open(self) -> bool:
        return self._visible and not self._animating

    def toggle(self):
        if self._visible:
            self.close()
        else:
            self.open()

    def open(self):
        if not self._alive:
            return
        if self._visible and not self._animating:
            return
        self._visible = True
        self._animating = True

        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

        # load fresh data each time it opens (in case downloads finished while closed)
        self._refresh_entries()

        self._raw_place(height=max(1, self._current_height), relwidth=1)
        try:
            self.tk.call("raise", self._w)
        except Exception:
            pass

        self._step(0, opening=True)

    def close(self):
        if not self._alive or not self._visible:
            return
        self._visible = False
        self._animating = True
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None
        self._step(0, opening=False)

    def _step(self, step, opening):
        if not self._alive:
            return
        if step > self.ANIM_FRAMES:
            self._finish(opening)
            return
        t = step / self.ANIM_FRAMES
        e = _ease_out_cubic(t) if opening else _ease_in_cubic(t)
        height = int(self.PANEL_H * e) if opening else int(self.PANEL_H * (1 - e))
        self._current_height = max(1, height)
        try:
            self._raw_place(height=self._current_height, relwidth=1)
        except Exception:
            return
        self._schedule(self.FRAME_MS, lambda: self._step(step + 1, opening))

    def _finish(self, opening):
        self._animating = False
        if not self._alive:
            return
        if opening:
            self._current_height = self.PANEL_H
            try:
                self._raw_place(height=self.PANEL_H, relwidth=1)
            except Exception:
                pass
        else:
            self._current_height = 0
            self._raw_place_forget()
            try:
                self._on_close_cb()
            except Exception:
                pass

    # ------------------------------------------------------------------ hit test
    def contains(self, x_root, y_root) -> bool:
        if not self._visible:
            return False
        try:
            x0 = self.winfo_rootx()
            y0 = self.winfo_rooty()
            x1 = x0 + self.winfo_width()
            y1 = y0 + self._current_height
            return x0 <= x_root <= x1 and y0 <= y_root <= y1
        except Exception:
            return False