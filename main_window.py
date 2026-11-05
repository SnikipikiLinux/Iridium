import os
import customtkinter as ctk

from ui import theme
from ui.widgets import PlaceholderEntry, SegmentedProgressBar
from ui.popup import ExitConfirmDialog
from ui.crt import CRTShutdown
from ui.tabs import TabBar
from ui.slide import SlideTransition
from ui.settings import SettingsPanel
from ui.history_panel import HistoryPanel
from ui.multi_download_tab import MultiDownloadTab
from ui.conversion_tab import ConversionTab
from ui.compress_tab import CompressTab
from core.downloader import Downloader
from core.converter import Converter
from core.compressor import Compressor
from core.urls import extract_youtube_urls, format_single


DISCORD_URL = "https://discord.com/invite/eDGFq3neR"
TAB_ORDER = ["Main", "Multi-Download", "Conversion", "Compress"]


def _default_download_dir() -> str:
    p = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(p):
        return p
    return os.path.expanduser("~")


def _folder_name_now() -> str:
    import datetime
    return datetime.datetime.now().strftime("Iridium_%Y-%m-%d_%H-%M-%S")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - theme.WINDOW_W) // 2
        y = (screen_h - theme.WINDOW_H) // 2
        self.geometry(f"{theme.WINDOW_W}x{theme.WINDOW_H}+{x}+{y}")
        self.minsize(theme.WINDOW_W, theme.WINDOW_H)
        self.configure(fg_color=theme.BG_BASE)

        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._closing = False
        self._transitioning = False

        self._downloader = None
        self._downloading = False
        self._download_mode = "single"
        self._active_progress_bar = None

        self._converter = None
        self._converting = False

        self._compressor = None
        self._compressing = False

        self._active_tab = "Main"
        self._discord_dialog = None
        self._settings_panel = None
        self._history_panel = None

        self._build_titlebar()
        self._build_body()

        self.bind("<ButtonPress-1>", self._on_global_click, add="+")
        self.after(100, self._force_focus)

    def _force_focus(self):
        try:
            self.focus_force()
        except Exception:
            pass

    # ---------------- title bar ----------------
    def _build_titlebar(self):
        self.titlebar = ctk.CTkFrame(
            self, height=theme.TITLEBAR_HEIGHT,
            fg_color=theme.BG_TITLEBAR, corner_radius=0,
        )
        self.titlebar.pack(side="top", fill="x")
        self.titlebar.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.titlebar, text="Iridium", font=theme.FONT_TITLE,
            text_color=theme.FG_TEXT, anchor="w",
        )
        self.title_label.pack(side="left", padx=(14, 0))

        # shared visual traits for every title-bar button
        ICON_FONT = ("Segoe UI", 17, "bold")
        BTN_H = 28
        BTN_PADY = 4
        BTN_PADX = (3, 0)
        BORDER = theme.FG_DIM

        self.close_btn = ctk.CTkButton(
            self.titlebar, text="✕",
            width=44, height=BTN_H, corner_radius=5,
            fg_color="transparent", hover_color=theme.CLOSE_HOVER,
            text_color=theme.FG_TEXT,
            border_width=1, border_color=BORDER,
            font=ICON_FONT, command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=(0, 8), pady=BTN_PADY)

        self.min_btn = ctk.CTkButton(
            self.titlebar, text="—",
            width=44, height=BTN_H, corner_radius=5,
            fg_color="transparent", hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            border_width=1, border_color=BORDER,
            font=ICON_FONT, command=self._on_minimize,
        )
        self.min_btn.pack(side="right", padx=BTN_PADX, pady=BTN_PADY)

        self.settings_btn = ctk.CTkButton(
            self.titlebar, text="⚙",
            width=44, height=BTN_H, corner_radius=5,
            fg_color="transparent", hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            border_width=1, border_color=BORDER,
            font=ICON_FONT, command=self._toggle_settings,
        )
        self.settings_btn.pack(side="right", padx=BTN_PADX, pady=BTN_PADY)

        self.history_btn = ctk.CTkButton(
            self.titlebar, text="📜",
            width=50, height=BTN_H, corner_radius=5,
            fg_color="transparent", hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            border_width=1, border_color=BORDER,
            font=("Segoe UI", 18, "bold"),
            command=self._toggle_history,
        )
        self.history_btn.pack(side="right", padx=BTN_PADX, pady=BTN_PADY)

        self.discord_btn = ctk.CTkButton(
            self.titlebar, text="Discord",
            width=92, height=BTN_H, corner_radius=5,
            fg_color="transparent", hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT,
            border_width=1, border_color=BORDER,
            font=("Segoe UI", 13, "bold"),
            command=self._on_discord,
        )
        self.discord_btn.pack(side="right", padx=BTN_PADX, pady=BTN_PADY)

        for widget in (self.titlebar, self.title_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event):
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        self.geometry(f"+{event.x_root - self._drag_offset_x}+{event.y_root - self._drag_offset_y}")

    # ---------------- body ----------------
    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color=theme.BG_BASE, corner_radius=0)
        self.body.pack(side="top", fill="both", expand=True)

        self.tabbar = TabBar(
            self.body, tabs=TAB_ORDER, on_change=self._switch_tab,
        )
        self.tabbar.pack(side="top", fill="x")

        ctk.CTkFrame(self.body, height=1, fg_color=theme.BG_PANEL, corner_radius=0).pack(
            side="top", fill="x"
        )

        self.stack = ctk.CTkFrame(self.body, fg_color="transparent", corner_radius=0)
        self.stack.pack(side="top", fill="both", expand=True)

        self.main_tab = ctk.CTkFrame(self.stack, fg_color="transparent", corner_radius=0)
        self._build_main_tab(self.main_tab)

        self.multi_tab = MultiDownloadTab(
            self.stack,
            on_download_all=self._on_download_all,
            on_cancel=self._on_cancel,
        )

        self.conversion_tab = ConversionTab(
            self.stack,
            on_convert=self._on_convert,
            on_cancel=self._on_convert_cancel,
        )

        self.compress_tab = CompressTab(
            self.stack,
            on_start=self._on_compress_start,
            on_cancel=self._on_compress_cancel,
        )

        self._tabs = {
            "Main": self.main_tab,
            "Multi-Download": self.multi_tab,
            "Conversion": self.conversion_tab,
            "Compress": self.compress_tab,
        }

        if self._active_tab in self._tabs:
            self._tabs[self._active_tab].pack(fill="both", expand=True)
            self.tabbar.set_active(self._active_tab)
        else:
            self._active_tab = "Main"
            self.main_tab.pack(fill="both", expand=True)
            self.tabbar.set_active("Main")

        self._settings_panel = SettingsPanel(
            self.body,
            on_theme_change=self._on_theme_changed,
            on_close=self._on_settings_closed,
        )

        self._history_panel = HistoryPanel(
            self.body,
            on_close=self._on_history_closed,
        )

        # restore active download state if still running (e.g. after theme switch)
        if self._downloading and self._downloader is not None and self._downloader.is_running():
            try:
                if self._download_mode == "single":
                    self.download_btn.configure(state="disabled", text="Downloading...")
                    self.pause_btn.configure(state="normal")
                    self.cancel_btn.configure(state="normal")
                    if self._downloader.is_paused():
                        self.pause_btn.configure(text="Resume")
                    self.progress_row.pack(pady=(14, 0), fill="x")
                    self._active_progress_bar = self.progress_bar
                else:
                    self.multi_tab.download_btn.configure(state="disabled", text="Downloading...")
                    self.multi_tab.cancel_btn.configure(state="normal")
                    self.multi_tab.show_progress()
                    self._active_progress_bar = self.multi_tab.progress_bar
            except Exception:
                pass

    def _build_main_tab(self, parent):
        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            content, text="...This is the part where you download stuff...",
            font=theme.FONT_HERO, text_color=theme.FG_MUTED,
        ).pack(pady=(0, 22))

        self.link_entry = PlaceholderEntry(
            content,
            placeholder="Enter link right here...",
            width=460, height=42,
            font=theme.FONT_INPUT,
            fg_color=theme.BG_INPUT, text_color=theme.FG_TEXT,
            border_color=theme.BG_INPUT, border_width=1,
            corner_radius=8, placeholder_color=theme.FG_DIM,
        )
        self.link_entry.pack(pady=(0, 16))

        for seq in ("<<Paste>>", "<Control-v>", "<Control-V>", "<Shift-Insert>"):
            try:
                self.link_entry.bind(seq, self._on_link_paste, add="+")
            except Exception:
                pass

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack()

        self.pause_btn = ctk.CTkButton(
            btn_row, text="Pause", width=100, height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT, hover_color=theme.MIN_HOVER,
            text_color=theme.FG_MUTED, corner_radius=6,
            command=self._on_pause_resume, state="disabled",
        )
        self.pause_btn.pack(side="left", padx=(0, 10), pady=(10, 0))

        self.download_btn = ctk.CTkButton(
            btn_row, text="Download", width=180, height=42,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE, corner_radius=8,
            command=self._on_download,
        )
        self.download_btn.pack(side="left")

        self.cancel_btn = ctk.CTkButton(
            btn_row, text="Cancel", width=100, height=32,
            font=("Segoe UI", 12, "bold"),
            fg_color=theme.BG_INPUT, hover_color="#5a1f1f",
            text_color=theme.FG_MUTED, corner_radius=6,
            command=self._on_cancel, state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(10, 0), pady=(10, 0))

        self.progress_row = ctk.CTkFrame(content, fg_color="transparent")
        self.progress_row.pack(pady=(14, 0), fill="x")

        self.progress_bar = SegmentedProgressBar(
            self.progress_row, segments=26, width=460, height=18,
        )
        self.progress_bar.pack(pady=(0, 6))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.progress_row, text="",
            font=("Segoe UI", 11), text_color=theme.FG_DIM,
        )
        self.status_label.pack()

        self.progress_row.pack_forget()

        self.link_entry.bind("<FocusIn>", lambda e: self.link_entry.configure(border_color=theme.ACCENT))
        self.link_entry.bind("<FocusOut>", lambda e: self.link_entry.configure(border_color=theme.BG_INPUT))

    def _on_link_paste(self, _event=None):
        self.after(15, self._reformat_link_entry)

    def _reformat_link_entry(self):
        try:
            raw = self.link_entry.get()
        except Exception:
            return
        if not raw:
            return
        formatted = format_single(raw)
        if formatted and formatted != raw:
            try:
                self.link_entry.delete(0, "end")
                self.link_entry.configure(text_color=theme.FG_TEXT)
                self.link_entry.insert(0, formatted)
                self.link_entry._showing_placeholder = False
            except Exception:
                pass

    # ---------------- tab switching ----------------
    def _switch_tab(self, name):
        if name == self._active_tab:
            return
        if name not in self._tabs:
            return
        try:
            forward = TAB_ORDER.index(name) > TAB_ORDER.index(self._active_tab)
        except ValueError:
            forward = True
        direction = "left" if forward else "right"

        outgoing = self._tabs.get(self._active_tab)
        incoming = self._tabs[name]
        if outgoing is None or incoming is None:
            return

        self._active_tab = name
        self.tabbar.set_active(name)

        if name == "Conversion":
            try:
                self.conversion_tab.refresh()
            except Exception:
                pass

        SlideTransition(
            container=self.stack,
            outgoing=outgoing, incoming=incoming,
            direction=direction, on_done=lambda: None,
        ).play()

    # ---------------- panels ----------------
    def _toggle_settings(self):
        if self._history_panel is not None:
            try:
                self._history_panel.close()
            except Exception:
                pass
        if self._settings_panel is None:
            return
        try:
            if not self._settings_panel.winfo_exists():
                return
        except Exception:
            return
        self._settings_panel.toggle()

    def _toggle_history(self):
        if self._settings_panel is not None:
            try:
                self._settings_panel.close()
            except Exception:
                pass
        if self._history_panel is None:
            return
        try:
            if not self._history_panel.winfo_exists():
                return
        except Exception:
            return
        self._history_panel.toggle()

    def _on_settings_closed(self):
        pass

    def _on_history_closed(self):
        pass

    def _on_global_click(self, event):
        for btn in (getattr(self, "settings_btn", None), getattr(self, "history_btn", None)):
            if btn is None:
                continue
            try:
                bx0 = btn.winfo_rootx()
                by0 = btn.winfo_rooty()
                bx1 = bx0 + btn.winfo_width()
                by1 = by0 + btn.winfo_height()
                if bx0 <= event.x_root <= bx1 and by0 <= event.y_root <= by1:
                    return
            except Exception:
                pass
        for panel in (self._settings_panel, self._history_panel):
            if panel is None:
                continue
            try:
                if not panel.winfo_exists():
                    continue
                if not getattr(panel, "_visible", False):
                    continue
                if panel.contains(event.x_root, event.y_root):
                    continue
                panel.close()
            except Exception:
                pass

    # ---------------- single download ----------------
    def _on_download(self):
        if self._converting or self._compressing:
            self._show_status("Another operation is running.", error=True)
            return
        if self._downloading:
            if self._downloader is not None and self._downloader.is_running():
                return
            self._downloading = False
            try:
                self.download_btn.configure(state="normal", text="Download")
            except Exception:
                pass

        try:
            if str(self.download_btn.cget("state")) == "disabled":
                self.download_btn.configure(state="normal", text="Download")
        except Exception:
            pass

        link = self.link_entry.get_value()
        if link:
            formatted = format_single(link)
            if formatted and formatted != link:
                link = formatted
        if not link:
            self._show_status("Paste a link first.", error=True)
            return

        save_dir = theme.get_setting("download_dir", _default_download_dir())
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception:
            self._show_status(f"Cannot use folder: {save_dir}", error=True)
            return

        self._downloading = True
        self._download_mode = "single"
        self._active_progress_bar = self.progress_bar

        try:
            self.download_btn.configure(state="disabled", text="Downloading...")
            self.pause_btn.configure(state="normal", text="Pause")
            self.cancel_btn.configure(state="normal")
            self.progress_row.pack(pady=(14, 0), fill="x")
            self.progress_bar.set(0)
            self.status_label.configure(text="Starting...", text_color=theme.FG_DIM)
        except Exception:
            pass

        try:
            self._downloader = Downloader(
                window=self,
                on_progress=self._on_dl_progress,
                on_status=self._on_dl_status,
                on_done=self._on_dl_done,
            )
            self._downloader.start(link, save_dir)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._downloading = False
            try:
                self.download_btn.configure(state="normal", text="Download")
                self.pause_btn.configure(state="disabled", text="Pause")
                self.cancel_btn.configure(state="disabled")
            except Exception:
                pass
            self._show_status(f"Failed to start download: {e}", error=True)

    def _on_download_all(self):
        if self._converting or self._compressing:
            self._multi_status("Another operation is running.", error=True)
            return
        if self._downloading:
            if self._downloader is not None and self._downloader.is_running():
                return
            self._downloading = False

        raw = self.multi_tab.textbox.get_value()
        if not raw:
            self._multi_status("Paste at least one link.", error=True)
            return

        urls = extract_youtube_urls(raw)
        if not urls:
            self._multi_status("No YouTube links found.", error=True)
            return

        save_dir = theme.get_setting("download_dir", _default_download_dir())
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception:
            self._multi_status(f"Cannot use folder: {save_dir}", error=True)
            return

        folder_name = _folder_name_now()

        self._downloading = True
        self._download_mode = "batch"
        self._active_progress_bar = self.multi_tab.progress_bar

        try:
            self.multi_tab.download_btn.configure(state="disabled", text="Downloading...")
            self.multi_tab.cancel_btn.configure(state="normal")
            self.multi_tab.progress_bar.set(0)
            self.multi_tab.show_progress()
            self.multi_tab.status_label.configure(
                text=f"Found {len(urls)} links. Starting...",
                text_color=theme.FG_DIM,
            )
            self.download_btn.configure(state="disabled")
        except Exception:
            pass

        try:
            self._downloader = Downloader(
                window=self,
                on_progress=self._on_dl_progress,
                on_status=self._on_dl_status,
                on_done=self._on_dl_done,
            )
            self._downloader.start_batch(urls, save_dir, folder_name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._downloading = False
            try:
                self.multi_tab.download_btn.configure(state="normal", text="Download All")
                self.multi_tab.cancel_btn.configure(state="disabled")
                self.download_btn.configure(state="normal")
            except Exception:
                pass
            self._multi_status(f"Failed to start batch: {e}", error=True)

    # ---------------- conversion ----------------
    def _on_convert(self, paths, delete_source=False):
        if self._downloading or self._compressing:
            self.conversion_tab.set_status("Another operation is running.", error=True)
            return
        if self._converting:
            return

        self._converting = True
        try:
            self.conversion_tab.set_converting(True)
            self.conversion_tab.show_progress()
            self.conversion_tab.set_progress(0)
            suffix = " (deleting originals)" if delete_source else ""
            self.conversion_tab.set_status(
                f"Converting {len(paths)} file(s){suffix}...", error=False,
            )
            self.download_btn.configure(state="disabled")
            self.multi_tab.download_btn.configure(state="disabled")
        except Exception:
            pass

        try:
            self._converter = Converter(
                window=self,
                on_progress=self._on_convert_progress,
                on_status=self._on_convert_status,
                on_done=self._on_convert_done,
            )
            self._converter.start(paths, delete_source=delete_source)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._converting = False
            try:
                self.conversion_tab.set_converting(False)
            except Exception:
                pass
            self.conversion_tab.set_status(f"Failed to start: {e}", error=True)

    def _on_convert_progress(self, frac):
        try:
            self.conversion_tab.set_progress(frac)
        except Exception:
            pass

    def _on_convert_status(self, text):
        try:
            self.conversion_tab.set_status(text, error=False)
        except Exception:
            pass

    def _on_convert_done(self, success, message):
        self._converting = False
        try:
            self.conversion_tab.set_converting(False)
        except Exception:
            pass
        try:
            self.download_btn.configure(state="normal")
            self.multi_tab.download_btn.configure(state="normal")
        except Exception:
            pass

        if success:
            try:
                self.conversion_tab.set_progress(1.0)
                self.conversion_tab.set_status(message, error=False)
                self.after(4000, self.conversion_tab.hide_progress)
            except Exception:
                pass
        else:
            try:
                self.conversion_tab.set_progress(0)
                self.conversion_tab.set_status(message, error=True)
            except Exception:
                pass

    def _on_convert_cancel(self):
        if self._converter is None or not self._converter.is_running():
            return
        try:
            self._converter.cancel()
            self.conversion_tab.set_status("Cancelling...", error=True)
            self.conversion_tab.cancel_btn.configure(state="disabled")
        except Exception:
            pass

    # ---------------- compression ----------------
    def _on_compress_start(self, input_path, target_mb):
        if self._downloading or self._converting:
            self.compress_tab.set_status("Another operation is running.", error=True)
            return
        if self._compressing:
            return

        self._compressing = True
        try:
            self.compress_tab.set_running(True)
            self.compress_tab.set_progress(0)
            self.compress_tab.set_status(
                f"Preparing to compress to ~{target_mb} MB...",
            )
            self.download_btn.configure(state="disabled")
            self.multi_tab.download_btn.configure(state="disabled")
        except Exception:
            pass

        try:
            self._compressor = Compressor(
                window=self,
                on_progress=self._on_compress_progress,
                on_status=self._on_compress_status,
                on_done=self._on_compress_done,
            )
            self._compressor.start(input_path, target_mb)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._compressing = False
            try:
                self.compress_tab.set_running(False)
            except Exception:
                pass
            self.compress_tab.set_status(f"Failed to start: {e}", error=True)

    def _on_compress_progress(self, frac):
        try:
            self.compress_tab.set_progress(frac)
        except Exception:
            pass

    def _on_compress_status(self, text):
        try:
            self.compress_tab.set_status(text, error=False)
        except Exception:
            pass

    def _on_compress_done(self, success, message):
        self._compressing = False
        try:
            self.compress_tab.set_running(False)
        except Exception:
            pass
        try:
            self.download_btn.configure(state="normal")
            self.multi_tab.download_btn.configure(state="normal")
        except Exception:
            pass

        if success:
            try:
                self.compress_tab.set_progress(1.0)
                out = None
                try:
                    sel = self.compress_tab._selected_file
                    if sel:
                        base, ext = os.path.splitext(sel)
                        cand = base + "_compressed" + (ext or ".mp4")
                        if os.path.isfile(cand):
                            out = cand
                except Exception:
                    pass
                self.compress_tab.finish_success(message, out or "")
                self.compress_tab.hide_progress_later()
            except Exception:
                pass
        else:
            try:
                self.compress_tab.finish_failure(message)
            except Exception:
                pass

    def _on_compress_cancel(self):
        if self._compressor is None or not self._compressor.is_running():
            return
        try:
            self._compressor.cancel()
            self.compress_tab.set_status("Cancelling...", error=True)
            self.compress_tab.cancel_btn.configure(state="disabled")
        except Exception:
            pass

    # ---------------- pause / cancel ----------------
    def _on_pause_resume(self):
        if self._downloader is None or not self._downloader.is_running():
            return
        try:
            if self._downloader.is_paused():
                self._downloader.resume()
                self.pause_btn.configure(text="Pause")
                self.status_label.configure(text="Resumed", text_color=theme.FG_DIM)
            else:
                self._downloader.pause()
                self.pause_btn.configure(text="Resume")
                self.status_label.configure(text="Paused", text_color=theme.ACCENT)
        except Exception:
            pass

    def _on_cancel(self):
        if self._downloader is None or not self._downloader.is_running():
            return
        try:
            self._downloader.cancel()
            self.status_label.configure(text="Cancelling...", text_color="#ff5a5a")
            self.multi_tab.status_label.configure(text="Cancelling...", text_color="#ff5a5a")
            self.cancel_btn.configure(state="disabled")
            self.multi_tab.cancel_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled", text="Pause")
        except Exception:
            pass

    # ---------------- downloader callbacks ----------------
    def _on_dl_progress(self, frac):
        try:
            if self._active_progress_bar is not None:
                self._active_progress_bar.set(frac)
        except Exception:
            pass

    def _on_dl_status(self, text):
        try:
            if self._download_mode == "batch":
                self.multi_tab.status_label.configure(text=text, text_color=theme.FG_DIM)
            else:
                self.status_label.configure(text=text, text_color=theme.FG_DIM)
        except Exception:
            pass

    def _on_dl_done(self, success, message):
        mode = self._download_mode
        self._downloading = False

        try:
            self.download_btn.configure(state="normal", text="Download")
            self.pause_btn.configure(state="disabled", text="Pause")
            self.cancel_btn.configure(state="disabled")
        except Exception:
            pass

        try:
            self.multi_tab.download_btn.configure(state="normal", text="Download All")
            self.multi_tab.cancel_btn.configure(state="disabled")
        except Exception:
            pass

        if mode == "single":
            if success:
                try:
                    if self._active_progress_bar is not None:
                        self._active_progress_bar.set(1.0)
                    self.status_label.configure(text=message, text_color=theme.ACCENT)
                    self.link_entry.clear()
                    self.after(3000, self._hide_progress_row)
                except Exception:
                    pass
            else:
                try:
                    if self._active_progress_bar is not None:
                        self._active_progress_bar.set(0)
                    self.status_label.configure(text=message, text_color="#ff5a5a")
                except Exception:
                    pass
        else:
            if success:
                try:
                    self.multi_tab.progress_bar.set(1.0)
                    self.multi_tab.status_label.configure(text=message, text_color=theme.ACCENT)
                    self.multi_tab.textbox.clear()
                    self.after(4000, self.multi_tab.hide_progress)
                except Exception:
                    pass
            else:
                try:
                    self.multi_tab.progress_bar.set(0)
                    self.multi_tab.status_label.configure(text=message, text_color="#ff5a5a")
                except Exception:
                    pass

        if self._history_panel is not None:
            try:
                if getattr(self._history_panel, "_visible", False):
                    self._history_panel._refresh_entries()
            except Exception:
                pass

        if self._active_tab == "Conversion" and hasattr(self, "conversion_tab"):
            try:
                self.conversion_tab.refresh()
            except Exception:
                pass

    def _hide_progress_row(self):
        try:
            self.progress_row.pack_forget()
        except Exception:
            pass

    def _show_status(self, text, error=False):
        try:
            self.progress_row.pack(pady=(14, 0), fill="x")
            self.progress_bar.set(0)
            self.status_label.configure(
                text=text,
                text_color="#ff5a5a" if error else theme.FG_DIM,
            )
            self.after(2500, self._hide_progress_row)
        except Exception:
            pass

    def _multi_status(self, text, error=False):
        try:
            self.multi_tab.show_progress()
            self.multi_tab.status_label.configure(
                text=text,
                text_color="#ff5a5a" if error else theme.FG_DIM,
            )
        except Exception:
            pass

    # ---------------- actions ----------------
    def _on_discord(self):
        if self._discord_dialog is not None and self._discord_dialog.winfo_exists():
            self._discord_dialog.focus()
            return
        self._discord_dialog = DiscordPromptDialog(
            self,
            on_confirm=self._open_discord,
            on_cancel=self._close_discord_dialog,
        )

    def _close_discord_dialog(self):
        self._discord_dialog = None

    def _open_discord(self):
        self._discord_dialog = None
        import webbrowser
        webbrowser.open(DISCORD_URL)

    def _on_theme_changed(self, name):
        if not theme.apply_theme(name):
            return
        remembered_tab = self._active_tab
        download_still_running = (
            self._downloading
            and self._downloader is not None
            and self._downloader.is_running()
        )
        conversion_still_running = (
            self._converting
            and self._converter is not None
            and self._converter.is_running()
        )
        compression_still_running = (
            self._compressing
            and self._compressor is not None
            and self._compressor.is_running()
        )
        for child in list(self.winfo_children()):
            child.destroy()
        self._closing = False
        self._transitioning = False
        self._downloading = download_still_running
        self._converting = conversion_still_running
        self._compressing = compression_still_running
        self._discord_dialog = None
        self._settings_panel = None
        self._history_panel = None
        self._active_tab = remembered_tab
        self.configure(fg_color=theme.BG_BASE)
        self._build_titlebar()
        self._build_body()

    # ---------------- window actions ----------------
    def _on_minimize(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._restore_override)

    def _restore_override(self, _event=None):
        self.unbind("<Map>")
        self.overrideredirect(True)

    def _on_close(self):
        if self._closing:
            return
        self._closing = True
        show_confirm = theme.get_setting("exit_confirm", True)
        if not show_confirm:
            self._run_crt_and_exit()
            return
        ExitConfirmDialog(
            self,
            on_confirm=self._run_crt_and_exit,
            on_cancel=self._cancel_close,
        )

    def _cancel_close(self):
        self._closing = False

    def _run_crt_and_exit(self):
        CRTShutdown(self, on_done=self._quit).play()

    def _quit(self):
        try:
            if self._downloader is not None and self._downloader.is_running():
                self._downloader.cancel()
        except Exception:
            pass
        try:
            if self._converter is not None and self._converter.is_running():
                self._converter.cancel()
        except Exception:
            pass
        try:
            if self._compressor is not None and self._compressor.is_running():
                self._compressor.cancel()
        except Exception:
            pass
        try:
            self.destroy()
        finally:
            import sys
            sys.exit(0)


# ----------------------------------------------------------------------------
# Discord confirmation dialog
# ----------------------------------------------------------------------------
class DiscordPromptDialog(ctk.CTkToplevel):
    W, H = 420, 220

    def __init__(self, parent, on_confirm, on_cancel):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self.overrideredirect(True)
        self.configure(fg_color=theme.BG_PANEL)
        self.resizable(False, False)

        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - self.W) // 2
        y = py + (ph - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        ctk.CTkFrame(self, height=2, fg_color=theme.ACCENT, corner_radius=0).pack(
            side="top", fill="x"
        )

        ctk.CTkLabel(
            self,
            text=(
                "By clicking this, you will be redirected to my Discord server, "
                "where you will be able to report bugs or talk with the community. "
                "Do you wanna proceed?"
            ),
            font=("Segoe UI", 12), text_color=theme.FG_TEXT,
            wraplength=self.W - 48, justify="center",
        ).pack(pady=(26, 22), padx=24)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 22))

        ctk.CTkButton(
            btn_row, text="NO!", width=120, height=36,
            font=theme.FONT_BUTTON,
            fg_color=theme.BG_INPUT, hover_color=theme.MIN_HOVER,
            text_color=theme.FG_TEXT, corner_radius=8,
            command=self._cancel,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="Yes", width=120, height=36,
            font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.BG_BASE, corner_radius=8,
            command=self._confirm,
        ).pack(side="left")

        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._confirm())
        self.after(50, self.focus_force)

    def _confirm(self):
        self.destroy()
        self._on_confirm()

    def _cancel(self):
        self.destroy()
        self._on_cancel()