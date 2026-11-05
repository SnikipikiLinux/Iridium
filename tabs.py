"""
ui/tabs.py — Iridium segmented tab control.

Deliberately simple. No multi-frame animations anywhere on the buttons.

Click behaviour:
  • click → switch tab instantly (no delay, no animation)
  • single fg_color flash: brighten on click, one after(150) to restore
  • if a new click arrives before the 150ms reset fires, cancel the pending
    timer and start fresh — NEVER more than one pending after() per tab
  • <Destroy> cancels all pending timers

There is nothing here that can queue up. Rapid clicks always work.
"""

import customtkinter as ctk

from ui import theme


def _blend(fg_hex, bg_hex, t):
    t = max(0.0, min(1.0, t))
    fr, fg, fb = int(fg_hex[1:3], 16), int(fg_hex[3:5], 16), int(fg_hex[5:7], 16)
    br, bg, bb = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
    r = int(fr * (1 - t) + br * t)
    g = int(fg * (1 - t) + bg * t)
    b = int(fb * (1 - t) + bb * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class TabBar(ctk.CTkFrame):
    """Compact segmented tab control, centered in the bar."""

    BUTTON_WIDTH = 140
    BUTTON_HEIGHT = 40
    FLASH_MS = 150

    def __init__(self, master, tabs, on_change, **kwargs):
        super().__init__(master, fg_color="transparent", height=56, **kwargs)
        self.pack_propagate(False)

        self._on_change = on_change
        self._active = None
        self._buttons = {}
        self._pending_reset = {}    # name -> single after id or None

        self._alive = True
        self.bind("<Destroy>", self._on_destroy, add="+")

        self._group = ctk.CTkFrame(
            self,
            fg_color=theme.BG_PANEL,
            border_color=theme.ACCENT,
            border_width=1,
            corner_radius=8,
        )
        self._group.pack(anchor="center", pady=(8, 8))
        self._group.pack_propagate(True)

        for name in tabs:
            btn = ctk.CTkButton(
                self._group,
                text=name,
                width=self.BUTTON_WIDTH,
                height=self.BUTTON_HEIGHT,
                corner_radius=0,
                border_width=0,
                font=("Segoe UI", 13, "bold"),
                fg_color=theme.BG_PANEL,
                hover_color=theme.BG_PANEL,
                text_color=theme.FG_MUTED,
                command=lambda n=name: self._on_click(n),
            )
            btn.pack(side="left", padx=0, pady=0)

            btn.bind("<Enter>", lambda e, n=name: self._on_enter(n), add="+")
            btn.bind("<Leave>", lambda e, n=name: self._on_leave(n), add="+")

            self._buttons[name] = btn
            self._pending_reset[name] = None

        if tabs:
            self.set_active(tabs[0])

    # ------------------------------------------------------------------ lifecycle
    def _on_destroy(self, _event=None):
        self._alive = False
        for name in list(self._pending_reset.keys()):
            self._cancel_pending(name)

    def _cancel_pending(self, name):
        tid = self._pending_reset.get(name)
        if tid is not None:
            try:
                self.after_cancel(tid)
            except Exception:
                pass
            self._pending_reset[name] = None

    # ------------------------------------------------------------------ colours
    def _active_color(self):
        return theme.ACCENT

    def _active_text_color(self):
        return theme.BG_BASE

    def _hover_color(self):
        return _blend(theme.BG_PANEL, theme.ACCENT, 0.15)

    def _flash_color(self, name):
        if name == self._active:
            return _blend(theme.ACCENT, "#ffffff", 0.30)
        return _blend(theme.BG_PANEL, theme.ACCENT, 0.55)

    # ------------------------------------------------------------------ painting
    def _paint_resting(self, name):
        b = self._buttons[name]
        if name == self._active:
            b.configure(
                fg_color=self._active_color(),
                text_color=self._active_text_color(),
                font=("Segoe UI", 13, "bold"),
            )
        else:
            b.configure(
                fg_color=theme.BG_PANEL,
                text_color=theme.FG_MUTED,
                font=("Segoe UI", 13, "normal"),
            )

    def _paint_hover(self, name):
        if name == self._active:
            return
        self._buttons[name].configure(
            fg_color=self._hover_color(),
            text_color=theme.FG_TEXT,
            font=("Segoe UI", 13, "normal"),
        )

    # ------------------------------------------------------------------ mouse
    def _on_enter(self, name):
        if not self._alive:
            return
        # don't override an active flash-in-progress
        if self._pending_reset.get(name) is not None:
            return
        self._paint_hover(name)

    def _on_leave(self, name):
        if not self._alive:
            return
        # let the flash timer finish, then it will restore resting color
        if self._pending_reset.get(name) is not None:
            return
        self._paint_resting(name)

    # ------------------------------------------------------------------ click
    def _on_click(self, name):
        if not self._alive:
            return

        # 1) switch immediately (no animation, no delay)
        if name != self._active:
            self.set_active(name)
            self._on_change(name)

        # 2) single-shot flash: brighten, one after to restore
        b = self._buttons[name]
        try:
            b.configure(
                fg_color=self._flash_color(name),
                text_color=(
                    self._active_text_color() if name == self._active
                    else theme.FG_TEXT
                ),
                font=("Segoe UI", 13, "bold"),
            )
        except Exception:
            return

        # cancel any prior pending reset for this tab (rapid clicks)
        self._cancel_pending(name)

        def reset():
            self._pending_reset[name] = None
            if not self._alive:
                return
            try:
                self._paint_resting(name)
            except Exception:
                pass

        try:
            tid = self.after(self.FLASH_MS, reset)
            self._pending_reset[name] = tid
        except Exception:
            self._pending_reset[name] = None

    # ------------------------------------------------------------------ public
    def set_active(self, name):
        if not self._alive or name == self._active:
            return
        self._active = name
        for n in self._buttons:
            # skip tabs with a pending flash reset — they'll restore themselves
            if self._pending_reset.get(n) is None:
                self._paint_resting(n)