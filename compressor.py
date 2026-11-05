"""core/compressor.py — single-pass CRF-based compression.

Much faster than two-pass, much lower CPU use. Uses -preset faster (or
veryfast for Max Space tier) and runs ffmpeg at BELOW_NORMAL_PRIORITY_CLASS
on Windows so it doesn't burn the fan.

Quality tiers by target/original ratio:
    ratio >= 0.70  → CRF 23, preset faster   (~Keep Quality)
    ratio <= 0.35  → CRF 32, preset veryfast (~Max Space)
    otherwise      → CRF 28, preset faster   (default)

Audio-only files re-encode at a bitrate derived from the target size (clamped
64-256 kbps) — no video processing.
"""

import os
import shutil
import subprocess
import sys
import threading
import time
import traceback

from core.downloader import _find_ffmpeg


def _find_ffprobe(ffmpeg_path):
    import sys
    import os
    import shutil

    # 1) bundled next to ffmpeg inside _MEIPASS
    try:
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(sys._MEIPASS, "ffprobe.exe")
            if os.path.isfile(bundled):
                return bundled
    except Exception:
        pass

    # 2) next to the ffmpeg we found
    if ffmpeg_path:
        d = os.path.dirname(ffmpeg_path)
        for name in ("ffprobe.exe", "ffprobe"):
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand

    # 3) PATH
    return shutil.which("ffprobe")


_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")

# Windows: BELOW_NORMAL_PRIORITY_CLASS. 0 is a no-op on other platforms.
_CREATE_FLAGS = 0x00004000 if sys.platform.startswith("win") else 0


def _popen(args, **kw):
    """Popen helper that always passes creationflags."""
    return subprocess.Popen(args, creationflags=_CREATE_FLAGS, **kw)


class Compressor:
    def __init__(self, window, on_progress, on_status, on_done):
        self.window = window
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_done = on_done
        self._thread = None
        self._cancelled = False
        self._last_status_t = 0.0
        self._ffmpeg = _find_ffmpeg()
        self._ffprobe = _find_ffprobe(self._ffmpeg)

    def start(self, input_path, target_mb, output_path=None):
        if self.is_running():
            return
        self._cancelled = False
        self._last_status_t = 0.0
        self._thread = threading.Thread(
            target=self._run, args=(input_path, target_mb, output_path), daemon=True,
        )
        self._thread.start()

    def cancel(self):
        self._cancelled = True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ callbacks
    def _status(self, text, force=False):
        now = time.monotonic()
        if not force and (now - self._last_status_t) * 1000 < 100:
            return
        self._last_status_t = now
        try:
            self.window.after(0, self.on_status, text)
        except Exception:
            pass

    def _progress(self, frac):
        try:
            self.window.after(0, self.on_progress, frac)
        except Exception:
            pass

    def _done(self, success, message):
        try:
            self.window.after(0, self.on_done, success, message)
        except Exception:
            pass

    # ------------------------------------------------------------------ helpers
    def _probe_duration(self, path):
        if self._ffprobe:
            try:
                r = subprocess.run(
                    [
                        self._ffprobe, "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        path,
                    ],
                    capture_output=True, timeout=30,
                )
                text = r.stdout.decode(errors="replace").strip()
                return float(text)
            except Exception:
                pass
        try:
            r = subprocess.run([self._ffmpeg, "-i", path], capture_output=True, timeout=30)
            import re
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)",
                          r.stderr.decode(errors="replace"))
            if m:
                h, mnt, s, cs = m.groups()
                return int(h) * 3600 + int(mnt) * 60 + int(s) + int(cs) / 100.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _is_audio_only(path):
        return os.path.splitext(path)[1].lower() in _AUDIO_EXTS

    @staticmethod
    def _tiers_for_ratio(ratio):
        if ratio >= 0.70:
            return "23", "faster"
        if ratio <= 0.35:
            return "32", "veryfast"
        return "28", "faster"

    # ------------------------------------------------------------------ worker
    def _run(self, input_path, target_mb, output_path):
        try:
            if not self._ffmpeg:
                self._done(False, "ffmpeg not found. Install ffmpeg to use the compressor.")
                return
            if not os.path.isfile(input_path):
                self._done(False, f"File not found: {input_path}")
                return

            self._status("Preparing...", force=True)
            self._progress(0.0)

            try:
                orig_bytes = os.path.getsize(input_path)
            except Exception:
                self._done(False, "Could not read input file size.")
                return
            orig_mb = orig_bytes / (1024 * 1024)
            if orig_mb <= 0:
                self._done(False, "Input file is empty.")
                return

            target_mb_f = float(target_mb)
            ratio = max(0.05, min(1.0, target_mb_f / orig_mb))

            base, ext = os.path.splitext(input_path)
            if not ext:
                ext = ".mp4"
            if not output_path:
                output_path = base + "_compressed" + ext

            # ---------------- audio-only path ----------------
            if self._is_audio_only(input_path):
                duration = self._probe_duration(input_path)
                if duration > 0:
                    target_bytes = target_mb_f * 1024 * 1024
                    computed = int((target_bytes * 8) / duration / 1000)
                    audio_kbps = max(64, min(256, computed))
                else:
                    audio_kbps = 128

                self._status(
                    f"Compressing audio at {audio_kbps} kbps (single pass)...",
                    force=True,
                )
                self._progress(0.1)

                args = [
                    self._ffmpeg, "-y", "-i", input_path,
                    "-b:a", f"{audio_kbps}k",
                    output_path,
                ]
                proc = _popen(
                    args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                self._poll_proc(proc)
                if proc.returncode == 0 and os.path.isfile(output_path):
                    self._progress(1.0)
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    self._done(True, f"Saved {size_mb:.1f} MB to {os.path.basename(output_path)}")
                else:
                    self._done(False, "Audio compression failed.")
                return

            # ---------------- video path (single-pass CRF) ----------------
            crf, preset = self._tiers_for_ratio(ratio)
            self._status(
                f"Encoding (CRF {crf}, preset {preset}, low priority)...",
                force=True,
            )
            self._progress(0.05)

            args = [
                self._ffmpeg, "-y", "-i", input_path,
                "-c:v", "libx264",
                "-crf", crf,
                "-preset", preset,
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ]
            proc = _popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._poll_proc(proc)

            if proc.returncode == 0 and os.path.isfile(output_path):
                self._progress(1.0)
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                self._done(True, f"Saved {size_mb:.1f} MB to {os.path.basename(output_path)}")
            else:
                self._done(False, "Video compression failed.")

        except Exception as exc:
            print("[Iridium/compressor]", traceback.format_exc())
            self._done(False, f"Compression error: {exc}")

    # ------------------------------------------------------------------ polling
    def _poll_proc(self, proc):
        """Poll until proc finishes; emit fake eased progress; handle cancel."""
        start = time.monotonic()
        while proc.poll() is None:
            if self._cancelled:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                except Exception:
                    pass
                self._done(False, "Compression cancelled.")
                return
            elapsed = time.monotonic() - start
            import math as _m
            fake = min(0.90, 0.05 + 0.85 * (1 - _m.exp(-elapsed / 30.0)))
            self._progress(fake)
            time.sleep(0.30)