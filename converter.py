"""core/converter.py — convert video files to mp3 using ffmpeg.

Optional delete of source files after successful conversion, controlled by
the `delete_source` argument to `start()`.
"""

import os
import subprocess
import threading
import time
import traceback

from core.downloader import _find_ffmpeg


class Converter:
    STATUS_THROTTLE_MS = 100

    def __init__(self, window, on_progress, on_status, on_done):
        self.window = window
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_done = on_done
        self._thread = None
        self._cancelled = False
        self._last_status_t = 0.0
        self._ffmpeg = _find_ffmpeg()
        self._delete_source = False

    def start(self, input_paths, delete_source=False):
        if self.is_running():
            return
        self._cancelled = False
        self._last_status_t = 0.0
        self._delete_source = bool(delete_source)
        self._thread = threading.Thread(
            target=self._run, args=(list(input_paths),), daemon=True,
        )
        self._thread.start()

    def cancel(self):
        self._cancelled = True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ worker
    def _run(self, paths):
        try:
            if not self._ffmpeg:
                self._done(False, "ffmpeg not found. Install ffmpeg to use the converter.")
                return

            total = len(paths)
            if total == 0:
                self._done(False, "No files selected.")
                return

            succeeded = 0
            failed = 0
            deleted = 0

            for i, path in enumerate(paths):
                if self._cancelled:
                    self._done(False, f"Conversion cancelled at {i}/{total}")
                    return

                if not os.path.isfile(path):
                    failed += 1
                    continue

                base, ext = os.path.splitext(path)
                if ext.lower() == ".mp3":
                    failed += 1
                    continue

                out_path = base + ".mp3"

                self._status(f"Converting {i+1}/{total}...", force=True)
                self._progress(i / total, force=True)

                try:
                    result = subprocess.run(
                        [
                            self._ffmpeg,
                            "-y",
                            "-i", path,
                            "-vn",
                            "-acodec", "libmp3lame",
                            "-q:a", "2",
                            out_path,
                        ],
                        capture_output=True,
                        timeout=900,
                    )
                    if result.returncode == 0 and os.path.isfile(out_path):
                        succeeded += 1
                        # optional delete of the source
                        if self._delete_source:
                            try:
                                os.remove(path)
                                deleted += 1
                            except Exception as e:
                                print(f"[Iridium/converter] could not delete {path}: {e}")
                    else:
                        failed += 1
                        try:
                            err = result.stderr.decode(errors="replace")[-250:]
                            print(f"[Iridium/converter] failed {path}: {err}")
                        except Exception:
                            pass
                except subprocess.TimeoutExpired:
                    failed += 1
                    print(f"[Iridium/converter] timeout {path}")
                except Exception as e:
                    failed += 1
                    print(f"[Iridium/converter] error {path}: {e}")

            self._progress(1.0, force=True)

            msg = f"Converted {succeeded}/{total} files to mp3"
            if failed:
                msg += f" ({failed} failed)"
            if deleted:
                msg += f" · deleted {deleted} original{'s' if deleted != 1 else ''}"

            self._done(succeeded > 0, msg)

        except Exception as exc:
            print("[Iridium/converter]", traceback.format_exc())
            self._done(False, f"Conversion failed: {exc}")

    # ------------------------------------------------------------------ callbacks
    def _progress(self, frac, force=False):
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