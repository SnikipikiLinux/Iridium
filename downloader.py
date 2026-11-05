"""
core/downloader.py — yt-dlp worker. Adds speed/ETA and records file path to history.
"""

import os
import shutil
import threading
import time
import traceback


def _find_ffmpeg():
    import sys
    import os
    import shutil

    # 1) bundled with PyInstaller exe
    try:
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(sys._MEIPASS, "ffmpeg.exe")
            if os.path.isfile(bundled):
                return bundled
    except Exception:
        pass

    # 2) next to the script / next to the exe
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local = os.path.join(base, "ffmpeg.exe")
        if os.path.isfile(local):
            return local
    except Exception:
        pass

    # 3) PATH
    p = shutil.which("ffmpeg")
    if p:
        return p

    # 4) common winget / Program Files locations
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    winget_pkgs = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.isdir(winget_pkgs):
        for entry in os.listdir(winget_pkgs):
            if "ffmpeg" in entry.lower():
                pkg_dir = os.path.join(winget_pkgs, entry)
                for root, _dirs, files in os.walk(pkg_dir):
                    if "ffmpeg.exe" in files:
                        return os.path.join(root, "ffmpeg.exe")

    return None


def _find_newest_output(folder, since_ts):
    """Return path to the newest file in `folder` with mtime >= since_ts."""
    try:
        if not os.path.isdir(folder):
            return ""
        best = None
        for f in os.listdir(folder):
            full = os.path.join(folder, f)
            if not os.path.isfile(full):
                continue
            if f.endswith((".part", ".ytdl", ".temp")):
                continue
            try:
                mtime = os.path.getmtime(full)
            except Exception:
                continue
            if mtime >= since_ts - 0.1:
                if best is None or mtime > best[0]:
                    best = (mtime, full)
        return best[1] if best else ""
    except Exception:
        return ""


def _add_history(title, url, kind, path=""):
    try:
        from core import history as history_mod
        history_mod.add_entry(title=title, url=url, kind=kind, path=path or "")
    except Exception:
        pass


class Downloader:
    PROGRESS_THROTTLE_MS = 50
    STATUS_THROTTLE_MS = 100

    def __init__(self, window, on_progress, on_status, on_done):
        self.window = window
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_done = on_done
        self._thread = None
        self._cancelled = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._last_progress_t = 0.0
        self._last_status_t = 0.0
        self._ffmpeg = _find_ffmpeg()
        self._mode = "single"

    def start(self, url, save_dir):
        if self.is_running():
            return
        self._mode = "single"
        self._reset()
        self._thread = threading.Thread(target=self._run, args=(url, save_dir), daemon=True)
        self._thread.start()

    def start_batch(self, urls, save_dir, folder_name):
        if self.is_running():
            return
        self._mode = "batch"
        self._reset()
        self._thread = threading.Thread(
            target=self._run_batch, args=(urls, save_dir, folder_name), daemon=True,
        )
        self._thread.start()

    def _reset(self):
        self._cancelled = False
        self._paused = False
        self._pause_event.set()
        self._last_progress_t = 0.0
        self._last_status_t = 0.0

    def pause(self):
        if self._paused:
            return
        self._paused = True
        self._pause_event.clear()

    def resume(self):
        if not self._paused:
            return
        self._paused = False
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self._pause_event.set()

    def is_paused(self):
        return self._paused

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def _detect_audio_only(info):
        formats = info.get("formats") or []
        if not formats:
            return True
        best_height = 0
        for f in formats:
            if f.get("vcodec") in (None, "none"):
                continue
            h = f.get("height") or 0
            if h > best_height:
                best_height = h
        return best_height < 360

    def _format_for(self, is_audio):
        if is_audio:
            return "bestaudio/best", None
        if self._ffmpeg:
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "mp4"
        return (
            "best[ext=mp4][vcodec!=none][acodec!=none]/"
            "best[vcodec!=none][acodec!=none]/bestaudio/best"
        ), None

    @staticmethod
    def _format_speed_eta(speed_bps, eta_sec):
        parts = []
        try:
            if speed_bps and speed_bps > 0:
                if speed_bps >= 1024 * 1024:
                    parts.append(f"{speed_bps / (1024 * 1024):.1f} MB/s")
                elif speed_bps >= 1024:
                    parts.append(f"{speed_bps / 1024:.0f} KB/s")
                else:
                    parts.append(f"{int(speed_bps)} B/s")
            if eta_sec and eta_sec > 0:
                m = int(eta_sec // 60)
                s = int(eta_sec % 60)
                parts.append(f"{m}m {s}s left" if m > 0 else f"{s}s left")
        except Exception:
            return ""
        return " · ".join(parts)

    def _progress(self, frac, force=False):
        now = time.monotonic()
        if not force and (now - self._last_progress_t) * 1000 < self.PROGRESS_THROTTLE_MS:
            return
        self._last_progress_t = now
        try:
            self.window.after(0, self.on_progress, frac)
        except Exception:
            pass

    def _status(self, text, force=False):
        now = time.monotonic()
        if not force and (now - self._last_status_t) * 1000 < self.STATUS_THROTTLE_MS:
            return
        self._last_status_t = now
        try:
            self.window.after(0, self.on_status, text)
        except Exception:
            pass

    def _done(self, success, message):
        try:
            self.window.after(0, self.on_done, success, message)
        except Exception:
            pass

    # ------------------------------------------------------------------ single
    def _run(self, url, save_dir):
        try:
            self._progress(0.0, force=True)
            self._status("Fetching info...", force=True)

            try:
                import yt_dlp
            except ImportError:
                self._done(False, "yt-dlp is not installed. Run: pip install yt-dlp")
                return

            probe_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            if self._ffmpeg:
                probe_opts["ffmpeg_location"] = self._ffmpeg

            try:
                with yt_dlp.YoutubeDL(probe_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as exc:
                self._done(False, f"Invalid link: {exc}")
                return

            if self._cancelled:
                self._done(False, "Download cancelled.")
                return

            is_audio = self._detect_audio_only(info)
            title = info.get("title", "Unknown")
            kind = "audio" if is_audio else "video"

            self._status(
                "Audio-only source detected. Downloading audio..." if is_audio
                else ("Downloading video..." if self._ffmpeg
                      else "ffmpeg not found — downloading best single-file format..."),
                force=True,
            )

            os.makedirs(save_dir, exist_ok=True)

            def hook(d):
                self._pause_event.wait()
                if self._cancelled:
                    raise yt_dlp.utils.DownloadCancelled()
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    done = d.get("downloaded_bytes") or 0
                    if total:
                        self._progress(min(0.999, done / total))
                    speed_text = self._format_speed_eta(d.get("speed"), d.get("eta"))
                    if speed_text:
                        self._status(f"Downloading {kind}... {speed_text}", force=False)
                elif d.get("status") == "finished":
                    self._progress(0.999, force=True)
                    self._status("Processing...", force=True)

            fmt, merge = self._format_for(is_audio)
            opts = {
                "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
                "format": fmt, "quiet": True, "no_warnings": True,
                "progress_hooks": [hook], "noprogress": True,
            }
            if merge:
                opts["merge_output_format"] = merge
            if self._ffmpeg:
                opts["ffmpeg_location"] = self._ffmpeg

            started_ts = time.time()
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            except yt_dlp.utils.DownloadCancelled:
                self._done(False, "Download cancelled.")
                return

            if self._cancelled:
                self._done(False, "Download cancelled.")
                return

            self._progress(1.0, force=True)
            path = _find_newest_output(save_dir, started_ts)
            _add_history(title, url, kind, path)
            self._done(True, f"Downloaded {kind} successfully.")

        except Exception as exc:
            print("[Iridium/downloader]", traceback.format_exc())
            msg = f"Download failed: {exc}"
            if "ffmpeg" in str(exc).lower() or "ffprobe" in str(exc).lower():
                msg = "Download failed: ffmpeg not found. Install ffmpeg for video downloads."
            self._done(False, msg)

    # ------------------------------------------------------------------ batch
    def _run_batch(self, urls, save_dir, folder_name):
        try:
            try:
                import yt_dlp
            except ImportError:
                self._done(False, "yt-dlp is not installed. Run: pip install yt-dlp")
                return

            total = len(urls)
            if total == 0:
                self._done(False, "No links to download.")
                return

            folder = os.path.join(save_dir, folder_name)
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                self._done(False, f"Cannot create folder: {e}")
                return

            self._progress(0.0, force=True)
            self._status(f"Preparing {total} downloads...", force=True)

            succeeded = 0
            failed = 0

            for i, url in enumerate(urls):
                if self._cancelled:
                    self._done(False, f"Batch cancelled at file {i+1}/{total}")
                    return

                self._status(f"Downloading {i+1}/{total}...", force=True)
                self._progress(i / total, force=True)

                probe_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                if self._ffmpeg:
                    probe_opts["ffmpeg_location"] = self._ffmpeg
                try:
                    with yt_dlp.YoutubeDL(probe_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    is_audio = self._detect_audio_only(info)
                    title = info.get("title", "Unknown")
                except Exception as e:
                    print(f"[Iridium/batch] skip {url}: {e}")
                    failed += 1
                    continue

                kind = "audio" if is_audio else "video"

                def make_hook(idx, kind_):
                    def hook(d):
                        self._pause_event.wait()
                        if self._cancelled:
                            raise yt_dlp.utils.DownloadCancelled()
                        if d.get("status") == "downloading":
                            tot_b = d.get("total_bytes") or d.get("total_bytes_estimate")
                            done_b = d.get("downloaded_bytes") or 0
                            if tot_b:
                                frac = min(0.999, done_b / tot_b)
                                self._progress((idx + frac) / total)
                            speed_text = self._format_speed_eta(d.get("speed"), d.get("eta"))
                            if speed_text:
                                self._status(
                                    f"Downloading {idx+1}/{total}... {speed_text}",
                                    force=False,
                                )
                        elif d.get("status") == "finished":
                            self._progress((idx + 0.999) / total, force=True)
                    return hook

                fmt, merge = self._format_for(is_audio)
                opts = {
                    "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
                    "format": fmt, "quiet": True, "no_warnings": True,
                    "progress_hooks": [make_hook(i, kind)], "noprogress": True,
                }
                if merge:
                    opts["merge_output_format"] = merge
                if self._ffmpeg:
                    opts["ffmpeg_location"] = self._ffmpeg

                file_started_ts = time.time()
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    succeeded += 1
                    path = _find_newest_output(folder, file_started_ts)
                    _add_history(title, url, kind, path)
                except yt_dlp.utils.DownloadCancelled:
                    self._done(False, "Batch cancelled.")
                    return
                except Exception as e:
                    print(f"[Iridium/batch] failed {url}: {e}")
                    failed += 1

            if self._cancelled:
                self._done(False, "Batch cancelled.")
                return

            self._progress(1.0, force=True)
            self._done(
                succeeded > 0,
                f"Downloaded {succeeded}/{total} files to '{folder_name}'"
                + (f" ({failed} failed)" if failed else ""),
            )

        except Exception as exc:
            print("[Iridium/downloader/batch]", traceback.format_exc())
            self._done(False, f"Batch failed: {exc}")