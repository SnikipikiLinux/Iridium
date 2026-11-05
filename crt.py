"""
ui/crt.py — CRT TV power-off animation.

Phases (all eased):
  A. compress vertically toward center (18 frames, ease-in)
  B. compress horizontally to a line     (14 frames, ease-in)
  C. bright dot hold                     (10 frames)
  D. dot shrink + afterglow fade         (14 frames)
Total ≥ 56 frames @ 16ms ≈ 0.9s.
"""

import math
import tkinter as tk
import customtkinter as ctk

from ui import theme


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class CRTShutdown:
    FRAME_MS = 16

    def __init__(self, window, on_done):
        self.window = window
        self.on_done = on_done
        self._aborted = False

        self.canvas = ctk.CTkCanvas(
            window,
            highlightthickness=0,
            bg="#000000",
            bd=0,
        )
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.tk.call("raise", self.canvas._w)

        self.window.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, _event=None):
        self._aborted = True

    def _schedule(self, ms, fn):
        if self._aborted:
            return
        try:
            self.window.after(ms, fn)
        except tk.TclError:
            self._aborted = True

    # ------------------------------------------------------------------ entry
    def play(self):
        self.window.update_idletasks()
        self.w = self.window.winfo_width()
        self.h = self.window.winfo_height()
        self.cx = self.w // 2
        self.cy = self.h // 2
        self._phase_a(0)

    # ------------------------------------------------------------------ A
    def _phase_a(self, step):
        """Vertical compress toward center line."""
        if self._aborted:
            return
        total = 18
        if step > total:
            self._phase_b(0)
            return

        t = step / total
        e = _smoothstep(t)
        half = max(1, int((self.h / 2) * (1 - e)))

        # phosphor color warms slightly as it collapses
        warmth = int(200 + 55 * e)
        color = f"#{warmth:02x}{min(255, warmth):02x}{int(warmth * 0.9):02x}"

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.w, self.cy - half, fill="#000000", outline="")
        self.canvas.create_rectangle(0, self.cy + half, self.w, self.h, fill="#000000", outline="")
        self.canvas.create_rectangle(
            0, self.cy - half, self.w, self.cy + half, fill=color, outline=""
        )
        self._schedule(self.FRAME_MS, lambda: self._phase_a(step + 1))

    # ------------------------------------------------------------------ B
    def _phase_b(self, step):
        """Horizontal compress to a line."""
        if self._aborted:
            return
        total = 14
        if step > total:
            self._phase_c(0)
            return

        t = step / total
        e = _smoothstep(t)
        half = max(2, int((self.w / 2) * (1 - e)))

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.w, self.h, fill="#000000", outline="")
        self.canvas.create_rectangle(
            self.cx - half, self.cy - 3,
            self.cx + half, self.cy + 3,
            fill="#ffffff", outline="",
        )
        self._schedule(self.FRAME_MS, lambda: self._phase_b(step + 1))

    # ------------------------------------------------------------------ C
    def _phase_c(self, step):
        """Bright dot holds, gently pulsing."""
        if self._aborted:
            return
        total = 10
        if step > total:
            self._phase_d(0)
            return

        t = step / total
        pulse = 1.0 + 0.15 * math.sin(t * math.pi * 2)
        r = max(2, int(3 * pulse))

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.w, self.h, fill="#000000", outline="")
        self.canvas.create_oval(
            self.cx - r, self.cy - r, self.cx + r, self.cy + r,
            fill="#ffffff", outline="",
        )
        self._schedule(self.FRAME_MS, lambda: self._phase_c(step + 1))

    # ------------------------------------------------------------------ D
    def _phase_d(self, step):
        """Dot shrinks and phosphor afterglow fades."""
        if self._aborted:
            return
        total = 14
        if step > total:
            self._finish()
            return

        t = step / total
        e = _smoothstep(t)
        r = max(1, int(3 * (1 - e)))
        v = int(255 * (1 - e))
        color = f"#{v:02x}{v:02x}{v:02x}"

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.w, self.h, fill="#000000", outline="")
        # afterglow ring
        glow_r = max(2, int(8 * (1 - e)))
        glow_v = int(90 * (1 - e))
        glow = f"#{glow_v:02x}{glow_v:02x}{glow_v:02x}"
        self.canvas.create_oval(
            self.cx - glow_r, self.cy - glow_r,
            self.cx + glow_r, self.cy + glow_r,
            fill=glow, outline="",
        )
        self.canvas.create_oval(
            self.cx - r, self.cy - r, self.cx + r, self.cy + r,
            fill=color, outline="",
        )
        self._schedule(self.FRAME_MS, lambda: self._phase_d(step + 1))

    # ------------------------------------------------------------------ finish
    def _finish(self):
        if self._aborted:
            return
        self._aborted = True
        try:
            self.window.update_idletasks()
        except tk.TclError:
            pass
        self.on_done()