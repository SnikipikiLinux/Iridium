import customtkinter as ctk

from ui import theme


class PlaceholderEntry(ctk.CTkEntry):
    def __init__(self, master, placeholder="", placeholder_color=None, **kwargs):
        super().__init__(master, **kwargs)
        self._placeholder = placeholder
        self._placeholder_color = placeholder_color or theme.FG_DIM
        self._text_color = kwargs.get("text_color", theme.FG_TEXT)
        self._showing_placeholder = False
        self._apply_placeholder()
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")

    def _apply_placeholder(self):
        if not self.get():
            self._showing_placeholder = True
            self.configure(text_color=self._placeholder_color)
            self.insert(0, self._placeholder)

    def _on_focus_in(self, _event=None):
        if self._showing_placeholder:
            self.delete(0, "end")
            self.configure(text_color=self._text_color)
            self._showing_placeholder = False

    def _on_focus_out(self, _event=None):
        if not self.get():
            self._apply_placeholder()

    def get_value(self) -> str:
        try:
            raw = self.get()
        except Exception:
            return ""
        if raw == self._placeholder:
            return ""
        return raw.strip()

    def clear(self):
        self.delete(0, "end")
        self._on_focus_out()


class PlaceholderTextbox(ctk.CTkTextbox):
    def __init__(self, master, placeholder="", placeholder_color=None, **kwargs):
        super().__init__(master, **kwargs)
        self._placeholder = placeholder
        self._placeholder_color = placeholder_color or theme.FG_DIM
        self._text_color = kwargs.get("text_color", theme.FG_TEXT)
        self._showing_placeholder = False
        self._apply_placeholder()
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")

    def _apply_placeholder(self):
        if not self.get("1.0", "end").strip():
            self._showing_placeholder = True
            self.configure(text_color=self._placeholder_color)
            self.insert("1.0", self._placeholder)

    def _on_focus_in(self, _event=None):
        if self._showing_placeholder:
            self.delete("1.0", "end")
            self.configure(text_color=self._text_color)
            self._showing_placeholder = False

    def _on_focus_out(self, _event=None):
        if not self.get("1.0", "end").strip():
            self._apply_placeholder()

    def get_value(self) -> str:
        try:
            raw = self.get("1.0", "end").strip()
        except Exception:
            return ""
        if raw == self._placeholder:
            return ""
        return raw

    def set_value(self, text: str):
        self.delete("1.0", "end")
        if text:
            self.configure(text_color=self._text_color)
            self._showing_placeholder = False
            self.insert("1.0", text)
        else:
            self._apply_placeholder()

    def clear(self):
        self.set_value("")


class GlowButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        fg = kwargs.get("fg_color", theme.ACCENT)
        idle_border = fg[1] if isinstance(fg, tuple) else fg
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", idle_border)
        super().__init__(master, **kwargs)
        self._idle_border = idle_border
        self._glow_border = theme.ACCENT_HOVER
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        try:
            self.configure(border_color=self._glow_border)
        except Exception:
            pass

    def _on_leave(self, _event=None):
        try:
            self.configure(border_color=self._idle_border)
        except Exception:
            pass


class SegmentedProgressBar(ctk.CTkFrame):
    """
    A segmented, theme-tinted progress bar with a fixed number of slots.
    Filled slots use ACCENT, empty slots use BG_PANEL (visible against
    BG_INPUT container). Border uses ACCENT_GLOW for a soft outline.

    API is compatible with `CTkProgressBar.set(...)` — you can drop this in
    anywhere you'd use CTkProgressBar.
    """

    DEFAULT_SEGMENTS = 26
    DEFAULT_HEIGHT = 18
    DEFAULT_WIDTH = 460

    def __init__(
        self,
        master,
        segments: int = DEFAULT_SEGMENTS,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=theme.BG_INPUT,
            corner_radius=4,
            border_width=1,
            border_color=theme.ACCENT_GLOW,
            width=width,
            height=height,
            **kwargs,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._segments = max(1, int(segments))
        self._value = 0.0
        self._seg_frames = []

        # inner strip of small segments, packed side-by-side with 1px gaps
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=3, pady=3)

        for i in range(self._segments):
            seg = ctk.CTkFrame(
                inner,
                fg_color=theme.BG_PANEL,
                corner_radius=2,
                height=max(2, height - 8),
            )
            # 1px gap between segments via left pad (skip on first)
            seg.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0 if i == 0 else 1, 0),
            )
            self._seg_frames.append(seg)

    def set(self, value: float):
        value = max(0.0, min(1.0, value))
        self._value = value
        filled = int(round(value * self._segments))
        # first N segments get ACCENT, rest stay BG_PANEL
        for i, seg in enumerate(self._seg_frames):
            target = theme.ACCENT if i < filled else theme.BG_PANEL
            try:
                current = seg.cget("fg_color")
            except Exception:
                current = None
            if current != target:
                try:
                    seg.configure(fg_color=target)
                except Exception:
                    pass

    def get(self):
        return self._value