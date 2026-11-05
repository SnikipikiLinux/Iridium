"""
ui/slide.py — 200ms horizontal tab slide, hard-cancellable.

12 frames @ 16ms ≈ 192ms. Ease-out-cubic. Both tabs move per frame
(incoming slides in, outgoing drifts 15% in the same direction).

Rapid tab switching: play() checks the module-level _ACTIVE animation and,
if one exists, cancels it (sets its _done flag and fires its on_done
immediately) before creating a new one. Every scheduled frame checks its
own _done flag before doing anything. No queue can ever build up.
"""

import tkinter as tk


# module-level tracker for the currently running animation, if any
_ACTIVE = {"current": None}


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _raw_place(widget, x=None, y=None, width=None, height=None):
    args = ["place", widget._w]
    if x is not None:
        args += ["-x", int(x)]
    if y is not None:
        args += ["-y", int(y)]
    if width is not None:
        args += ["-width", int(width)]
    if height is not None:
        args += ["-height", int(height)]
    widget.tk.call(*args)


def _raw_place_configure(widget, x=None, y=None):
    args = ["place", "configure", widget._w]
    if x is not None:
        args += ["-x", int(x)]
    if y is not None:
        args += ["-y", int(y)]
    widget.tk.call(*args)


class SlideTransition:
    FRAMES = 12
    FRAME_MS = 16

    def __init__(self, container, outgoing, incoming, direction, on_done=None):
        self.container = container
        self.outgoing = outgoing
        self.incoming = incoming
        self.direction = direction
        self.on_done = on_done or (lambda: None)
        self._done = False
        self._step = 0

    # ------------------------------------------------------------------ entry
    def play(self):
        # HARD CANCEL: if another animation is active, kill it right now
        prev = _ACTIVE.get("current")
        if prev is not None and prev is not self:
            prev.cancel()
        _ACTIVE["current"] = self

        try:
            self.container.update_idletasks()
            self.W = self.container.winfo_width()
            self.H = self.container.winfo_height()
        except Exception:
            self._finish()
            return

        self.outgoing.pack_forget()
        self.incoming.pack_forget()

        _raw_place(self.outgoing, x=0, y=0, width=self.W, height=self.H)

        if self.direction == "left":
            self._start_x = self.W
        else:
            self._start_x = -self.W

        _raw_place(self.incoming, x=self._start_x, y=0, width=self.W, height=self.H)
        self.incoming.tk.call("raise", self.incoming._w)

        self._frame()

    # ------------------------------------------------------------------ cancel
    def cancel(self):
        """Called by a newer animation. Stop immediately, fire on_done."""
        if self._done:
            return
        self._done = True
        cb = self.on_done
        self.on_done = lambda: None
        try:
            cb()
        except Exception:
            pass

    # ------------------------------------------------------------------ frames
    def _frame(self):
        if self._done:
            return
        if self._step > self.FRAMES:
            self._finish()
            return

        try:
            t = self._step / self.FRAMES
            e = _ease_out_cubic(t)

            in_x = int(self._start_x * (1 - e))
            if self.direction == "left":
                out_x = int(-self.W * 0.15 * e)
            else:
                out_x = int(self.W * 0.15 * e)

            _raw_place_configure(self.incoming, x=in_x)
            _raw_place_configure(self.outgoing, x=out_x)
        except Exception:
            self._done = True
            self._finish()
            return

        self._step += 1
        try:
            self.container.after(self.FRAME_MS, self._frame)
        except Exception:
            self._done = True

    # ------------------------------------------------------------------ finish
    def _finish(self):
        if self._done:
            return
        self._done = True
        if _ACTIVE.get("current") is self:
            _ACTIVE["current"] = None

        try:
            self.outgoing.place_forget()
            self.incoming.place_forget()
            self.incoming.pack(fill="both", expand=True)
        except Exception:
            pass

        cb = self.on_done
        self.on_done = lambda: None
        try:
            cb()
        except Exception:
            pass