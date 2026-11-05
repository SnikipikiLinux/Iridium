"""ui/compress_tab.py — compression tab.

Features:
  • smart size detection: slider range adapts to the loaded file
  • presets: Keep Quality / A Taste of Both / Max Space / Manual
  • animated compressor machine: idle when not running, fast mechanical
    press when compressing, bits flow only during compression and shrink
    as they pass through the press
"""

import math
import os
import random
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from ui import theme
from ui.widgets import SegmentedProgressBar


def _blend(fg, bg, t):
    t = max(0.0, min(1.0, t))
    fr, fg_, fb = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
    br, bg_, bb = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(fr * (1 - t) + br * t),
        int(fg_ * (1 - t) + bg_ * t),
        int(fb * (1 - t) + bb * t),
    )


def _open_folder(path):
    try:
        if not path:
            return
        folder = os.path.dirname(path) if os.path.isfile(path) else path
        if not folder:
            return
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
    except Exception as e:
        print(f"[Iridium] could not open folder: {e}")


_ACCEPTED_EXTS = (
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus",
)

_PRESETS = ("Keep Quality", "A Taste of Both", "Max Space", "Manual")


# ============================================================================
# Animated compressor machine
# ============================================================================
class CompressorMachine(tk.Canvas):
    FRAME_MS = 30
    BIT_POOL = 16

    PRESS_START = 100
    PRESS_END = 240

    def __init__(self, master, cw=330, ch=170):
        super().__init__(
            master, width=cw, height=ch,
            highlightthickness=0, bd=0, bg=theme.BG_PANEL,
        )
        self._alive = True
        self._running = False
        self._ratio = 0.5
        self._frame_id = None
        self._cw = cw
        self._ch = ch
        self._press_phase = 0.0
        self._bit_ids = []
        self._bit_data = []
        self._bit_y = ch // 2

        # pre-computed font tuples for the size-shrink effect
        self._font_sizes = [6, 7, 8, 9, 10, 11]
        self._bit_fonts = [("Consolas", s, "bold") for s in self._font_sizes]
        self._bit_green = "#33ff77"

        self.bind("<Destroy>", self._on_destroy, add="+")

        self._draw_static()
        self._tick()

    def _on_destroy(self, _event=None):
        self._alive = False
        if self._frame_id is not None:
            try:
                self.after_cancel(self._frame_id)
            except Exception:
                pass

    # ---- static drawing ----
    def _draw_static(self):
        tube_color = _blend(theme.FG_DIM, theme.BG_PANEL, 0.5)
        mid_y = self._ch // 2

        self.create_rectangle(
            10, mid_y - 14, self.PRESS_START, mid_y + 14,
            outline=tube_color, width=1,
        )
        self.create_rectangle(
            self.PRESS_END, mid_y - 14, self._cw - 10, mid_y + 14,
            outline=tube_color, width=1,
        )
        self.create_rectangle(
            self.PRESS_START, mid_y - 60, self.PRESS_END, mid_y + 60,
            outline=tube_color, width=1,
        )

        self._top_plate = self.create_rectangle(
            110, mid_y - 70, 230, mid_y - 45,
            fill=theme.ACCENT, outline="",
        )
        self._bot_plate = self.create_rectangle(
            110, mid_y + 45, 230, mid_y + 70,
            fill=theme.ACCENT, outline="",
        )

        self.create_text(
            self._cw // 2, mid_y + 82,
            text="COMPRESSING",
            fill=_blend(theme.FG_MUTED, theme.BG_PANEL, 0.4),
            font=("Segoe UI", 9, "bold"),
        )

    # ---- bits ----
    def _create_bits(self):
        self._bit_ids = []
        self._bit_data = []
        for _ in range(self.BIT_POOL):
            x = random.uniform(-40, self._cw)
            text = random.choice(["0", "1"])
            item = self.create_text(
                x, self._bit_y, text=text,
                fill=self._bit_green, font=self._bit_fonts[-1],
            )
            self._bit_ids.append(item)
            self._bit_data.append({
                "x": x,
                "base_speed": random.uniform(1.6, 3.0),
                "text": text,
                "size_idx": len(self._font_sizes) - 1,
            })

    def _destroy_bits(self):
        for item in self._bit_ids:
            try:
                self.delete(item)
            except Exception:
                pass
        self._bit_ids = []
        self._bit_data = []

    def _size_idx_at(self, x):
        if x < self.PRESS_START:
            return len(self._font_sizes) - 1
        if x > self.PRESS_END:
            return 0
        t = (x - self.PRESS_START) / (self.PRESS_END - self.PRESS_START)
        idx = (len(self._font_sizes) - 1) - int(t * (len(self._font_sizes) - 1))
        return max(0, min(len(self._font_sizes) - 1, idx))

    def _speed_mult_at(self, x):
        if x < 70:
            return 1.0
        if x < self.PRESS_START:
            t = (x - 70) / (self.PRESS_START - 70)
            return 1.0 + t * 0.4
        if x < self.PRESS_END:
            return 1.4
        if x < self.PRESS_END + 40:
            t = (x - self.PRESS_END) / 40
            return 1.4 - t * 0.7
        return 0.7

    def _press_speed_mult(self):
        # harder compression → faster press
        return 1.0 + (1.0 - self._ratio) * 2.5

    # ---- public API ----
    def start_compressing(self, ratio=0.5):
        self._running = True
        self._ratio = max(0.05, min(1.0, ratio))
        self._press_phase = 0.0
        self._destroy_bits()
        self._create_bits()

    def stop_compressing(self):
        self._running = False
        self._press_phase = 0.0
        self._destroy_bits()
        self._reset_press()

    def _reset_press(self):
        mid_y = self._ch // 2
        try:
            self.coords(self._top_plate, 110, mid_y - 70, 230, mid_y - 45)
            self.coords(self._bot_plate, 110, mid_y + 45, 230, mid_y + 70)
        except Exception:
            pass

    # ---- tick loop ----
    def _tick(self):
        if not self._alive:
            return

        if self._running:
            mid_y = self._ch // 2

            # bits
            for i, item in enumerate(self._bit_ids):
                d = self._bit_data[i]
                d["x"] += d["base_speed"] * self._speed_mult_at(d["x"])
                if d["x"] > self._cw + 10:
                    d["x"] = -10
                    d["text"] = random.choice(["0", "1"])
                    try:
                        self.itemconfigure(item, text=d["text"])
                    except Exception:
                        pass
                new_idx = self._size_idx_at(d["x"])
                if new_idx != d["size_idx"]:
                    d["size_idx"] = new_idx
                    try:
                        self.itemconfigure(item, font=self._bit_fonts[new_idx])
                    except Exception:
                        pass
                try:
                    self.coords(item, d["x"], self._bit_y)
                except Exception:
                    pass

            # press
            self._press_phase += 0.5 * self._press_speed_mult()
            offset = (math.sin(self._press_phase) + 1) / 2
            squeeze = int(offset * 40)
            try:
                self.coords(
                    self._top_plate,
                    110, mid_y - 70 + squeeze, 230, mid_y - 45 + squeeze,
                )
                self.coords(
                    self._bot_plate,
                    110, mid_y + 45 - squeeze, 230, mid_y + 70 - squeeze,
                )
            except Exception:
                pass

        try:
            self._frame_id = self.after(self.FRAME_MS, self._tick)
        except Exception:
            self._alive = False


# ============================================================================
# The tab
# ============================================================================
class CompressTab(ctk.CTkFrame):
    SLIDER_STEPS = 200

    def __init__(self, master, on_start, on_cancel, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_start = on_start
        self._on_cancel = on_cancel
        self._selected_file = None
        self._output_path = None
        self._original_size_mb = None
        self._current_target_mb = None
        self._slider_min = 1.0
        self._slider_max = 200.0
        self._active_preset = "Manual"
        self._preset_buttons = {}
        self._programmatic_slider = False

        # ---- description ----
        ctk.CTkLabel(
            self,
            text=(
                "Welcome to the Compressor! It works exactly how it sounds — "
                "by compressing. Drag your video or audio file into the input, "
                "set your target size using the slider, and hit Start Compressing. "
                "Simple as that."
            ),
            font=("Segoe UI", 12, "italic"),
            text_color=theme.FG_MUTED,
            wraplength=720, justify="center",
        ).pack(pady=(14, 8), padx=20)

        # ---- three-column row ----
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(0, 4))

        # LEFT: input
        self.input_frame = ctk.CTkFrame(
            row,
            fg_color=theme.BG_INPUT,
            border_color=_blend(theme.FG_DIM, theme.BG_INPUT, 0.3),
            border_width=2,
            corner_radius=8,
            width=190, height=170,
        )
        self.input_frame.pack(side="left", padx=(0, 10))
        self.input_frame.pack_propagate(False)

        self.input_label = ctk.CTkLabel(
            self.input_frame,
            text="Click to select\nor drop file here",
            font=("Segoe UI", 11),
            text_color=theme.FG_MUTED,
            wraplength=170, justify="center",
        )
        self.input_label.pack(expand=True)
        for w in (self.input_frame, self.input_label):
            w.bind("<Button-1>", lambda e: self._browse())

        # CENTER: machine
        self.machine = CompressorMachine(row, cw=330, ch=170)
        self.machine.pack(side="left", padx=(0, 10))

        # RIGHT: output
        self.output_frame = ctk.CTkFrame(
            row,
            fg_color=theme.BG_INPUT,
            corner_radius=8,
            width=190, height=170,
        )
        self.output_frame.pack(side="left")
        self.output_frame.pack_propagate(False)

        self.output_placeholder = ctk.CTkLabel(
            self.output_frame,
            text="Your compressed\nfile will appear here",
            font=("Segoe UI", 11),
            text_color=theme.FG_DIM,
            justify="center",
        )
        self.output_placeholder.pack(expand=True)

        self.sparkle_canvas = None
        self.open_folder_btn = None

        # ---- presets row ----
        presets_row = ctk.CTkFrame(self, fg_color="transparent")
        presets_row.pack(pady=(4, 2))

        for name in _PRESETS:
            btn = ctk.CTkButton(
                presets_row,
                text=name,
                width=110, height=28,
                font=("Segoe UI", 11, "bold"),
                fg_color=theme.BG_INPUT,
                hover_color=_blend(theme.BG_INPUT, theme.ACCENT, 0.15),
                text_color=theme.FG_TEXT,
                corner_radius=6,
                command=lambda n=name: self._click_preset(n),
            )
            btn.pack(side="left", padx=3)
            self._preset_buttons[name] = btn

        # ---- slider row ----
        slider_row = ctk.CTkFrame(self, fg_color="transparent")
        slider_row.pack(fill="x", padx=20, pady=(2, 2))

        ctk.CTkLabel(
            slider_row, text="Target:",
            font=("Segoe UI", 12, "bold"),
            text_color=theme.FG_TEXT,
        ).pack(side="left", padx=(0, 8))

        self.slider = ctk.CTkSlider(
            slider_row,
            from_=self._slider_min, to=self._slider_max,
            number_of_steps=self.SLIDER_STEPS,
            width=340,
            progress_color=theme.ACCENT,
            button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            fg_color=theme.BG_INPUT,
            command=self._on_slider,
        )
        self.slider.pack(side="left", padx=(0, 10))
        self.slider.set(50)

        self.slider_value = ctk.CTkLabel(
            slider_row, text="—",
            font=("Segoe UI", 12, "bold"),
            text_color=theme.ACCENT,
            width=90, anchor="w",
        )
        self.slider_value.pack(side="left")

        self.original_label = ctk.CTkLabel(
            slider_row, text="",
            font=("Segoe UI", 10),
            text_color=theme.FG_DIM,
        )
        self.original_label.pack(side="left", padx=(10, 0))

        # ---- buttons ----
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(4, 4))

        self.start_btn = ctk.CTkButton(
            btn_row, text="Start Compressing",
            width=200, height=38,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE, corner_radius=8,
            command=self._on_click_start,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_row, text="Cancel",
            width=100, height=30,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT, hover_color="#5a1f1f",
            text_color=theme.FG_MUTED, corner_radius=6,
            command=on_cancel, state="disabled",
        )
        self.cancel_btn.pack(side="left", pady=(8, 0))

        # ---- progress ----
        self.progress_row = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_row.pack(pady=(2, 6), fill="x", padx=20)
        self.progress_bar = SegmentedProgressBar(
            self.progress_row, segments=26, width=640, height=14,
        )
        self.progress_bar.pack(pady=(0, 4))
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(
            self.progress_row, text="",
            font=("Segoe UI", 10), text_color=theme.FG_DIM,
        )
        self.status_label.pack()
        self.progress_row.pack_forget()

        self._update_preset_colors()

    # ---- file browse ----
    def _browse(self):
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Select a file to compress",
            filetypes=[
                ("Video / Audio", " ".join("*" + e for e in _ACCEPTED_EXTS)),
                ("All files", "*.*"),
            ],
        )
        if not chosen:
            return
        ext = os.path.splitext(chosen)[1].lower()
        if ext not in _ACCEPTED_EXTS:
            self._set_status(f"Unsupported format: {ext}", error=True)
            return
        self._load_file(chosen)

    def _load_file(self, path):
        try:
            size_bytes = os.path.getsize(path)
        except Exception:
            self._set_status("Could not read file size.", error=True)
            return
        orig = size_bytes / (1024 * 1024)
        if orig < 0.1:
            self._set_status(
                f"File too small to compress ({size_bytes // 1024} KB)",
                error=True,
            )
            return

        self._selected_file = path
        self._original_size_mb = orig

        # slider bounds:
        #   min = max(1 MB or 10% of orig, whichever is larger) — for tiny
        #         files below 2 MB, allow 10% of orig instead of a hard 1 MB
        #   max = just below the original size
        if orig >= 2.0:
            self._slider_min = max(1.0, orig * 0.10)
        else:
            self._slider_min = max(0.1, orig * 0.10)
        self._slider_max = max(self._slider_min + 0.1, orig * 0.99)
        self._apply_slider_range()

        # display filename
        name = os.path.basename(path)
        short = name if len(name) < 20 else name[:17] + "…"
        self.input_label.configure(
            text=short, text_color=theme.FG_TEXT, font=("Segoe UI", 11, "bold"),
        )
        self.input_frame.configure(border_color=theme.ACCENT)

        self.original_label.configure(text=f"(original: {orig:.1f} MB)")

        if self._active_preset == "Manual":
            default_target = orig * 0.5
            default_target = max(self._slider_min, min(self._slider_max, default_target))
            default_target = round(default_target * 10) / 10
            self._set_slider(default_target)
            self._set_status(f"Loaded: {name}")
        else:
            self._apply_preset(self._active_preset)

    def _apply_slider_range(self):
        try:
            self.slider.configure(
                from_=self._slider_min,
                to=self._slider_max,
                number_of_steps=self.SLIDER_STEPS,
            )
        except Exception:
            pass

    # ---- presets ----
    def _click_preset(self, name):
        if self._selected_file is None:
            self._set_status("Load a file first.", error=True)
            return
        self._active_preset = name
        self._update_preset_colors()
        if name == "Manual":
            self._set_status("Manual mode — drag the slider to pick a size.")
        else:
            self._apply_preset(name)

    def _apply_preset(self, name):
        if self._original_size_mb is None:
            return
        orig = self._original_size_mb
        if name == "Keep Quality":
            target = orig * 0.80
        elif name == "A Taste of Both":
            target = orig * 0.50
        elif name == "Max Space":
            target = 20.0 if orig > 20 else orig * 0.40
        else:
            return
        target = max(self._slider_min, min(self._slider_max, target))
        target = round(target * 10) / 10
        self._set_slider(target)
        self._set_status(f"{name} preset: target ~{target:.1f} MB")

    def _set_slider(self, value):
        self._programmatic_slider = True
        try:
            self.slider.set(value)
        except Exception:
            pass
        self._programmatic_slider = False
        self._current_target_mb = value
        self.slider_value.configure(text=f"{value:.1f} MB")

    def _on_slider(self, value):
        if self._programmatic_slider:
            return
        if self._original_size_mb is None:
            self.slider_value.configure(text="—")
            return
        self._current_target_mb = value
        self.slider_value.configure(text=f"{value:.1f} MB")
        if self._active_preset != "Manual":
            self._active_preset = "Manual"
            self._update_preset_colors()

    def _update_preset_colors(self):
        for name, btn in self._preset_buttons.items():
            if name == self._active_preset:
                btn.configure(fg_color=theme.ACCENT, text_color=theme.BG_BASE)
            else:
                btn.configure(fg_color=theme.BG_INPUT, text_color=theme.FG_TEXT)

    # ---- start ----
    def _on_click_start(self):
        if not self._selected_file:
            self._set_status("Select a file first.", error=True)
            self.progress_row.pack(pady=(2, 6), fill="x", padx=20)
            return
        if not os.path.isfile(self._selected_file):
            self._set_status("File no longer exists.", error=True)
            return
        target_mb = self._current_target_mb
        if target_mb is None:
            target_mb = self.slider.get()
        target_mb = round(target_mb, 1)
        self._current_target_mb = target_mb
        self._clear_output()
        self._on_start(self._selected_file, target_mb)

    # ---- external API ----
    def set_running(self, running):
        try:
            self.start_btn.configure(
                state="disabled" if running else "normal",
                text="Compressing..." if running else "Start Compressing",
            )
            self.cancel_btn.configure(state="normal" if running else "disabled")
            self.slider.configure(state="disabled" if running else "normal")
            for btn in self._preset_buttons.values():
                try:
                    btn.configure(state="disabled" if running else "normal")
                except Exception:
                    pass
            if running:
                orig = self._original_size_mb or 1.0
                target = self._current_target_mb or (orig * 0.5)
                ratio = max(0.05, min(1.0, target / orig))
                self.machine.start_compressing(ratio)
                self.progress_row.pack(pady=(2, 6), fill="x", padx=20)
            else:
                self.machine.stop_compressing()
        except Exception:
            pass

    def set_progress(self, frac):
        try:
            self.progress_bar.set(frac)
        except Exception:
            pass

    def _set_status(self, text, error=False):
        try:
            self.progress_row.pack(pady=(2, 6), fill="x", padx=20)
            self.status_label.configure(
                text=text,
                text_color="#ff5a5a" if error else theme.FG_DIM,
            )
        except Exception:
            pass

    def set_status(self, text, error=False):
        self._set_status(text, error)

    def finish_success(self, message, output_path):
        self._output_path = output_path
        self._set_status(message, error=False)
        self._play_sparkle()
        self.after(400, lambda: self._show_open_folder(output_path))

    def finish_failure(self, message):
        self._set_status(message, error=True)
        self.progress_bar.set(0)

    def hide_progress_later(self):
        self.after(4000, lambda: self.progress_row.pack_forget())

    # ---- output area ----
    def _clear_output(self):
        for child in list(self.output_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self.open_folder_btn = None
        self._output_path = None
        self.output_placeholder = ctk.CTkLabel(
            self.output_frame,
            text="Your compressed\nfile will appear here",
            font=("Segoe UI", 11),
            text_color=theme.FG_DIM,
            justify="center",
        )
        self.output_placeholder.pack(expand=True)

    def _play_sparkle(self):
        try:
            if self.sparkle_canvas is not None:
                self.sparkle_canvas.destroy()
        except Exception:
            pass
        try:
            self.output_placeholder.pack_forget()
        except Exception:
            pass

        c = tk.Canvas(
            self.output_frame,
            highlightthickness=0, bd=0,
            bg=theme.BG_INPUT,
        )
        c.place(x=0, y=0, relwidth=1, relheight=1)
        c.tk.call("raise", c._w)
        self.sparkle_canvas = c

        try:
            self.output_frame.update_idletasks()
            w = self.output_frame.winfo_width()
            h = self.output_frame.winfo_height()
        except Exception:
            w, h = 190, 170
        cx, cy = w // 2, h // 2

        particles = []
        for i in range(14):
            ang = (i / 14) * (2 * math.pi)
            particles.append({
                "ang": ang,
                "r": 4,
                "dist": 0,
                "speed": random.uniform(3.0, 5.5),
                "id": c.create_oval(
                    cx - 3, cy - 3, cx + 3, cy + 3,
                    fill=theme.ACCENT, outline="",
                ),
            })

        step = [0]
        total = 24

        def tick():
            try:
                if not c.winfo_exists():
                    return
            except Exception:
                return
            step[0] += 1
            t = step[0] / total
            col = _blend(theme.ACCENT, theme.BG_INPUT, t)
            for p in particles:
                p["dist"] += p["speed"]
                px = cx + math.cos(p["ang"]) * p["dist"]
                py = cy + math.sin(p["ang"]) * p["dist"]
                r = max(1, int(p["r"] * (1 - t * 0.7)))
                try:
                    c.coords(p["id"], px - r, py - r, px + r, py + r)
                    c.itemconfigure(p["id"], fill=col)
                except Exception:
                    return
            if step[0] < total:
                try:
                    c.after(24, tick)
                except Exception:
                    pass
            else:
                try:
                    c.destroy()
                except Exception:
                    pass
                self.sparkle_canvas = None
                try:
                    self.output_placeholder.pack(expand=True)
                except Exception:
                    pass

        tick()

    def _show_open_folder(self, output_path):
        if not output_path:
            return
        try:
            self.output_placeholder.pack_forget()
        except Exception:
            pass
        if self.open_folder_btn is not None:
            try:
                self.open_folder_btn.destroy()
            except Exception:
                pass
        name = os.path.basename(output_path)
        short = name if len(name) < 20 else name[:17] + "…"
        ctk.CTkLabel(
            self.output_frame, text=short,
            font=("Segoe UI", 10, "bold"),
            text_color=theme.FG_TEXT,
            wraplength=170, justify="center",
        ).pack(pady=(16, 8), padx=6)
        self.open_folder_btn = ctk.CTkButton(
            self.output_frame,
            text="Open Folder", width=140, height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE, corner_radius=6,
            command=lambda: _open_folder(output_path),
        )
        self.open_folder_btn.pack()