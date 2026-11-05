"""
ui/intro.py — Iridium ghost intro, rewritten clean.

Sequence:
  1. Ghost creeps in from left while bobbing gently
  2. Settles in center
  3. Winks once (eye shrinks to line then reopens)
  4. Fades out smoothly
  5. UI fades in

Skip: any key or mouse click
"""

import math
import tkinter as tk
import customtkinter as ctk
from ui import theme


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def _sine_ease(t):
    t = max(0.0, min(1.0, t))
    return -(math.cos(math.pi * t) - 1) / 2


class GhostIntro:
    FRAME_MS      = 16
    FLOAT_FRAMES  = 120
    SETTLE_FRAMES = 30
    WINK_FRAMES   = 40
    FADE_FRAMES   = 50
    REVEAL_FRAMES = 40

    GW = 28
    GH = 36

    def __init__(self, window, on_done):
        self.window   = window
        self.on_done  = on_done
        self._aborted = False
        self._skipped = False

        self.canvas = ctk.CTkCanvas(
            window, highlightthickness=0, bg=theme.BG_BASE, bd=0
        )
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.tk.call("raise", self.canvas._w)

        window.bind("<Destroy>",     self._on_destroy, add="+")
        window.bind("<KeyPress>",    self._on_skip,    add="+")
        window.bind("<ButtonPress>", self._on_skip,    add="+")
        self.canvas.bind("<ButtonPress>", self._on_skip, add="+")
        self.canvas.focus_set()

    def _on_destroy(self, _=None): self._aborted = True

    def _on_skip(self, _=None):
        if self._aborted or self._skipped:
            return
        self._skipped = True
        self.canvas.delete("all")
        self._reveal_step(0)

    def _schedule(self, ms, fn):
        if not self._aborted:
            self.window.after(ms, fn)

    def play(self):
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        self.w = w if w > 100 else theme.WINDOW_W
        self.h = h if h > 100 else theme.WINDOW_H
        self.cx = self.w // 2
        self.cy = self.h // 2
        self._float_step(0)

    def _float_step(self, step):
        if self._aborted or self._skipped:
            return
        if step > self.FLOAT_FRAMES:
            self._settle_step(0)
            return

        t = _sine_ease(step / self.FLOAT_FRAMES)

        # start fully on screen from left edge with generous margin
        start_x = self.GW + 80
        cx = start_x + (self.cx - start_x) * t
        cy = self.cy + math.sin(step / self.FLOAT_FRAMES * math.pi * 2) * 5
        alpha = min(1.0, step / 20)

        self.canvas.delete("all")
        self._draw_ghost(cx, cy, wink=0.0, alpha=alpha)
        self._draw_hint()
        self._schedule(self.FRAME_MS, lambda: self._float_step(step + 1))

    def _settle_step(self, step):
        if self._aborted or self._skipped:
            return
        if step > self.SETTLE_FRAMES:
            self._wink_step(0)
            return

        t = step / self.SETTLE_FRAMES
        cy = self.cy + math.sin(t * math.pi) * 3

        self.canvas.delete("all")
        self._draw_ghost(self.cx, cy, wink=0.0, alpha=1.0)
        self._draw_hint()
        self._schedule(self.FRAME_MS, lambda: self._settle_step(step + 1))

    def _wink_step(self, step):
        if self._aborted or self._skipped:
            return
        if step > self.WINK_FRAMES:
            self._fade_step(0)
            return

        t = step / self.WINK_FRAMES
        if t < 0.35:
            wink = _ease(t / 0.35)
        elif t < 0.65:
            wink = 1.0
        else:
            wink = 1.0 - _ease((t - 0.65) / 0.35)

        self.canvas.delete("all")
        self._draw_ghost(self.cx, self.cy, wink=wink, alpha=1.0)
        self._draw_hint()
        self._schedule(self.FRAME_MS, lambda: self._wink_step(step + 1))

    def _fade_step(self, step):
        if self._aborted:
            return
        if step > self.FADE_FRAMES:
            self._reveal_step(0)
            return

        alpha = 1.0 - _sine_ease(step / self.FADE_FRAMES)

        self.canvas.delete("all")
        if alpha > 0.01:
            self._draw_ghost(self.cx, self.cy, wink=0.0, alpha=alpha)
        self._schedule(self.FRAME_MS, lambda: self._fade_step(step + 1))

    def _reveal_step(self, step):
        if self._aborted:
            return
        if step > self.REVEAL_FRAMES:
            self._finish()
            return

        t = _sine_ease(step / self.REVEAL_FRAMES)
        v = int(255 * (1.0 - t))
        color = f"#{v:02x}{v:02x}{v:02x}"

        self.canvas.delete("all")
        self.canvas.create_rectangle(
            0, 0, self.w, self.h, fill=color, outline=""
        )
        self._schedule(self.FRAME_MS, lambda: self._reveal_step(step + 1))

    def _draw_hint(self):
        r, g, b = self._blend_rgb(theme.FG_DIM, theme.BG_BASE, 0.45)
        self.canvas.create_text(
            self.w // 2, self.h - 24,
            text="Press any key or click to skip...",
            fill=f"#{r:02x}{g:02x}{b:02x}",
            font=("Segoe UI", 10),
        )

    def _draw_ghost(self, cx, cy, wink, alpha):
        gw = self.GW
        gh = self.GH

        body  = self._blend(theme.ACCENT, theme.BG_BASE, 1.0 - alpha * 0.85)
        edge  = self._blend(theme.ACCENT, theme.BG_BASE, 1.0 - alpha * 0.6)
        eye_c = self._blend(theme.BG_BASE, theme.BG_BASE, 0.0)

        # make sure ghost never goes off screen
        cx = max(gw + 10, min(self.w - gw - 10, cx))
        cy = max(gh + 10, min(self.h - gh - 10, cy))

        # body: top semicircle
        top = []
        for i in range(33):
            a = math.pi + math.pi * i / 32
            top.append((
                cx + math.cos(a) * gw,
                cy + math.sin(a) * gh * 0.7
            ))

        # body rectangle middle section
        rect_top_y = cy - gh * 0.1
        rect_bot_y = cy + gh * 0.55

        # wavy hem at bottom
        hem = []
        steps = 24
        for i in range(steps + 1):
            u = i / steps
            lx = cx - gw + 2 * gw * u
            ly = rect_bot_y + math.sin(u * math.pi * 3) * (gh * 0.18)
            hem.append((lx, ly))

        # build full ghost polygon
        ghost_pts = []
        ghost_pts += top
        ghost_pts += [(cx + gw, rect_bot_y)]
        ghost_pts += hem[::-1]
        ghost_pts += [(cx - gw, rect_bot_y)]

        flat = [c for p in ghost_pts for c in p]
        self.canvas.create_polygon(flat, fill=body, outline=edge, width=1.5)

        # eyes
        ex = gw * 0.38
        ey = gh * 0.08
        erx = gw * 0.18
        ery = gh * 0.22

        # left eye (always open)
        self.canvas.create_oval(
            cx - ex - erx, cy - ey - ery,
            cx - ex + erx, cy - ey + ery,
            fill=eye_c, outline=""
        )

        # right eye (winks)
        ery_now = max(1.5, ery * (1.0 - wink))
        self.canvas.create_oval(
            cx + ex - erx, cy - ey - ery_now,
            cx + ex + erx, cy - ey + ery_now,
            fill=eye_c, outline=""
        )

        # draw eyelid line when winking
        if wink > 0.6:
            lid_alpha = (wink - 0.6) / 0.4
            lid = self._blend(eye_c, body, 1.0 - lid_alpha)
            self.canvas.create_line(
                cx + ex - erx, cy - ey,
                cx + ex + erx, cy - ey,
                fill=lid, width=2
            )

    @staticmethod
    def _blend(fg, bg, t):
        t = max(0.0, min(1.0, t))
        fr, fg_, fb = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
        br, bg_, bb = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        r = int(fr * (1 - t) + br * t)
        g = int(fg_ * (1 - t) + bg_ * t)
        b = int(fb * (1 - t) + bb * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _blend_rgb(fg, bg, t):
        t = max(0.0, min(1.0, t))
        fr, fg_, fb = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
        br, bg_, bb = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        return (
            int(fr * (1 - t) + br * t),
            int(fg_ * (1 - t) + bg_ * t),
            int(fb * (1 - t) + bb * t),
        )

    def _finish(self):
        if self._aborted:
            return
        self._aborted = True
        try:
            self.window.unbind("<KeyPress>")
            self.window.unbind("<ButtonPress>")
        except Exception:
            pass
        try:
            self.canvas.destroy()
        except tk.TclError:
            pass
        self.on_done()