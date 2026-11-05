"""
ui/settings.py — in-window settings panel.

A CTkFrame placed absolutely over the body of the main window, just below
the title bar. Animated by interpolating its placed height from 0 → full
over 20 frames at 16ms each (~320ms). Reverse on close.

CTkFrame.place() rejects height/width arguments — they must be set at
construction. To animate the height, we use raw Tcl `place` calls that
bypass CTk's wrapper entirely.

No Toplevel. No OS window. Nothing escapes the main window.

Public API (used by main_window.py):
    panel = SettingsPanel(parent=body, on_theme_change=..., on_close=...)
    panel.open()       # slides down
    panel.close()      # slides up, then place_forget()
    panel.toggle()     # open if hidden, close if shown
    panel.is_open()    # True when fully open (not during transition)
    panel.contains(x_root, y_root)  # hit-test for click-outside
"""

import os
import customtkinter as ctk

from ui import theme


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _ease_in_cubic(t):
    t = max(0.0, min(1.0, t))
    return t * t * t


class SettingsPanel(ctk.CTkFrame):
    """In-window settings drawer, anchored directly under the title bar."""

    ANIM_FRAMES = 20
    FRAME_MS = 16
    PANEL_H = 520

    def __init__(self, master, on_theme_change, on_close):
        # height is provided at construction — CTk requires this
        super().__init__(
            master,
            fg_color=theme.BG_PANEL,
            corner_radius=0,
            border_width=0,
            width=800,
            height=self.PANEL_H,
        )
        self._on_theme_change = on_theme_change
        self._on_close_cb = on_close

        self._alive = True
        self._visible = False
        self._animating = False
        self._anim_id = None
        self._current_height = 0
        self._credits_window = None

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

    # ------------------------------------------------------------------ raw place
    def _raw_place(self, height=None, relwidth=None):
        """Bypass CTk's place() guard. Use for any call that passes height."""
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
        """Build every widget exactly once."""

        # ---- version line ----
        ctk.CTkLabel(
            self,
            text=f"Iridium v{theme.VERSION}b",
            font=("Segoe UI", 10),
            text_color=theme.FG_DIM,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(12, 0))

        # ---- header ----
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(2, 4))
        ctk.CTkLabel(
            header,
            text="Settings",
            font=("Segoe UI", 14, "bold"),
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

        ctk.CTkFrame(self, height=1, fg_color=theme.BG_INPUT, corner_radius=0).pack(
            fill="x", padx=18, pady=(4, 12)
        )

        # ---- exit confirmation toggle ----
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(
            row,
            text="Show exit confirmation",
            font=theme.FONT_INPUT,
            text_color=theme.FG_TEXT,
            anchor="w",
        ).pack(side="left")
        self._exit_var = ctk.BooleanVar(
            value=bool(theme.get_setting("exit_confirm", True))
        )
        ctk.CTkSwitch(
            row,
            text="",
            variable=self._exit_var,
            width=44,
            progress_color=theme.ACCENT,
            button_color=theme.FG_TEXT,
            button_hover_color=theme.FG_TEXT,
            fg_color=theme.BG_INPUT,
            command=self._toggle_exit_confirm,
        ).pack(side="right")

        # ---- download folder picker ----
        ctk.CTkLabel(
            self,
            text="Download folder",
            font=("Segoe UI", 12, "bold"),
            text_color=theme.FG_MUTED,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 4))

        folder_row = ctk.CTkFrame(self, fg_color="transparent")
        folder_row.pack(fill="x", padx=18, pady=(0, 16))

        current_dir = theme.get_setting(
            "download_dir",
            os.path.join(os.path.expanduser("~"), "Downloads"),
        )
        self._dir_label = ctk.CTkLabel(
            folder_row,
            text=self._abbrev(current_dir),
            font=("Segoe UI", 10),
            text_color=theme.FG_DIM,
            anchor="w",
            justify="left",
            wraplength=200,
        )
        self._dir_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            folder_row,
            text="Browse…",
            width=70,
            height=26,
            font=("Segoe UI", 10, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE,
            corner_radius=6,
            command=self._pick_folder,
        ).pack(side="right")

        # ---- theme picker ----
        ctk.CTkLabel(
            self,
            text="Theme",
            font=("Segoe UI", 12, "bold"),
            text_color=theme.FG_MUTED,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 6))

        for name in theme.all_themes():
            unlocked = theme.is_theme_unlocked(name)
            active = (name == theme.active_theme_name())

            btn = ctk.CTkButton(
                self,
                text=("●  " if active else "○  ") + name + ("" if unlocked else "   🔒"),
                anchor="w",
                height=34,
                font=theme.FONT_INPUT,
                fg_color=theme.ACCENT if active else theme.BG_INPUT,
                hover_color=theme.ACCENT_HOVER if unlocked else theme.BG_INPUT,
                text_color=theme.BG_BASE if active else (
                    theme.FG_TEXT if unlocked else theme.FG_DIM
                ),
                corner_radius=6,
                command=(lambda n=name: self._pick_theme(n)) if unlocked else None,
                state="normal" if unlocked else "disabled",
            )
            btn.pack(fill="x", padx=18, pady=2)

            if not unlocked:
                hint = "unlocks on Halloween" if name == "Halloween" else "unlocks on Christmas"
                btn.bind(
                    "<Enter>",
                    lambda e, t=hint, w=btn: self._show_tooltip(w, t),
                    add="+",
                )
                btn.bind("<Leave>", lambda e: self._hide_tooltip(), add="+")

        # ---- divider + credits button ----
        ctk.CTkFrame(self, height=1, fg_color=theme.BG_INPUT, corner_radius=0).pack(
            fill="x", padx=18, pady=(14, 10)
        )
        ctk.CTkButton(
            self,
            text="Credits",
            height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT,
            hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            corner_radius=6,
            command=self._open_credits,
        ).pack(fill="x", padx=18, pady=(0, 14))

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

        self._raw_place(height=max(1, self._current_height), relwidth=1)
        try:
            self.tk.call("raise", self._w)
        except Exception:
            pass

        self._step(0, opening=True)

    def close(self):
        if not self._alive:
            return
        if not self._visible:
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

    # ------------------------------------------------------------------ animation
    def _step(self, step, opening):
        if not self._alive:
            return
        if step > self.ANIM_FRAMES:
            self._finish(opening)
            return

        t = step / self.ANIM_FRAMES
        e = _ease_out_cubic(t) if opening else _ease_in_cubic(t)
        if opening:
            height = int(self.PANEL_H * e)
        else:
            height = int(self.PANEL_H * (1 - e))

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

    # ---- helpers ----
    @staticmethod
    def _abbrev(path: str) -> str:
        if len(path) <= 28:
            return path
        parts = path.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return "…/" + parts[-1]
        return "…" + path[-24:]

    # ---- handlers ----
    def _toggle_exit_confirm(self):
        theme.set_setting("exit_confirm", bool(self._exit_var.get()))

    def _pick_folder(self):
        from tkinter import filedialog
        chosen = filedialog.askdirectory(parent=self, title="Choose download folder")
        if not chosen:
            return
        theme.set_setting("download_dir", chosen)
        self._dir_label.configure(text=self._abbrev(chosen))

    def _pick_theme(self, name):
        if not theme.is_theme_unlocked(name):
            return
        self._alive = False
        try:
            self.destroy()
        except Exception:
            pass
        try:
            self._on_close_cb()
        except Exception:
            pass
        self._on_theme_change(name)

    def _open_credits(self):
        # if one is already open, just focus it
        if self._credits_window is not None:
            try:
                if self._credits_window.winfo_exists():
                    self._credits_window.focus()
                    return
            except Exception:
                pass
            self._credits_window = None
        try:
            from ui.credits import CreditsWindow
            self._credits_window = CreditsWindow(self.winfo_toplevel())
        except Exception as e:
            print(f"[Iridium] could not open credits: {e}")

    # ---- tooltips ----
    def _show_tooltip(self, widget, text):
        self._hide_tooltip()
        x = widget.winfo_rootx() - self.winfo_rootx() + widget.winfo_width() + 6
        y = widget.winfo_rooty() - self.winfo_rooty() + 6
        tip = ctk.CTkLabel(
            self,
            text=text,
            font=("Segoe UI", 10),
            fg_color=theme.BG_INPUT,
            text_color=theme.FG_TEXT,
            corner_radius=4,
        )
        tip.place(x=x, y=y)
        self._tooltip = tip

    def _hide_tooltip(self):
        if getattr(self, "_tooltip", None) is not None:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None