#!/usr/bin/env python3
"""Thin tangent-analyzer UI. Clip chrome. Lower plate is leftover rank, not transcription.

Paste is the corpus. Voice is captured, transcribed, used as the prompt, then shredded.
"""
from __future__ import annotations

import array
import json
import os
import queue
import re
import struct
import sys
import tempfile
import threading
import time
import wave
from collections import deque
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
TA_BAT = APP_ROOT / "Ta.bat"
TA_UI_BAT = APP_ROOT / "Ta-ui.bat"

DEVICE_LINE = re.compile(r"^\[(\d+)\]\s+(.*?)(?:\s+\(current\))?\s*$")
RATE = 16000
CHUNK_SAMPLES = 1600
NBUFS = 6
SILENCE_PEAK = 500
DEFAULT_SECONDS = 10
MAX_SECONDS = 40
SECONDS_PER_CLICK = 10
MAX_RECORD_CLICKS = 4
CLICK_WAIT_MS = 450
PLATE_LABEL = "tangent analysis"

sys.path.insert(0, str(HERE))
from ta_config import list_input_devices, load_config  # noqa: E402
from ta_look import (  # noqa: E402
    CYAN,
    INK_MUTE,
    LINE,
    VOID,
    apply as apply_look,
    ink_button,
    log_box,
    plate,
)

LOWER_PLATE_LABEL = PLATE_LABEL


def parse_device_list(text: str) -> tuple[list[tuple[int, str]], int]:
    devices: list[tuple[int, str]] = []
    current = 0
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("current_index="):
            try:
                current = int(line.split("=", 1)[1].strip())
            except ValueError:
                current = 0
            continue
        m = DEVICE_LINE.match(line)
        if m:
            devices.append((int(m.group(1)), m.group(2).strip()))
    if not devices:
        devices = [(0, "default")]
    return devices, current


def pick_default_device(devices: list[tuple[int, str]], current: int = 0) -> int:
    """Maono USB first, then any Maono, then a USB mic (not Stereo Mix)."""
    if not devices:
        return 0
    ranked: list[tuple[int, int]] = []
    for i, name in devices:
        n = name.lower()
        mix = "mix" in n or "stereo" in n or "loopback" in n
        score = 0
        if "maono" in n and "usb" in n:
            score = 4
        elif "maono" in n:
            score = 3
        elif "usb" in n and not mix:
            score = 2
        elif "usb" in n:
            score = 1
        ranked.append((score, i))
    ranked.sort(key=lambda t: t[0], reverse=True)
    if ranked[0][0] > 0:
        return ranked[0][1]
    ids = {i for i, _ in devices}
    if current in ids:
        return current
    return devices[0][0]


def device_is_usb_mic(name: str) -> bool:
    n = name.lower()
    if "mix" in n or "stereo" in n:
        return False
    return "maono" in n or "usb" in n


def parse_seconds(text: str, default: int = DEFAULT_SECONDS) -> int:
    raw = (text or "").strip()
    if not raw:
        return default
    try:
        n = int(float(raw))
    except ValueError:
        return default
    if n < 1:
        return default
    return min(n, MAX_SECONDS)


def record_clicks_to_seconds(clicks: int) -> int:
    n = max(1, min(int(clicks), MAX_RECORD_CLICKS))
    return n * SECONDS_PER_CLICK


def ui_state_path() -> Path:
    env = os.environ.get("SESEFUS_TA_UI_STATE")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    return home / ".sesefus" / "ta-ui.json"


def load_recent_dir(state: Path | None = None) -> Path | None:
    p = state or ui_state_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    raw = str(data.get("last_dir") or "").strip()
    if not raw:
        return None
    dest = Path(os.path.expandvars(raw)).expanduser()
    if dest.is_dir():
        return dest.resolve()
    return None


def save_recent_dir(folder: Path, state: Path | None = None) -> Path:
    p = state or ui_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body: dict[str, Any] = {}
    if p.is_file():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                body = prev
        except (OSError, json.JSONDecodeError):
            body = {}
    body["last_dir"] = str(Path(folder).resolve())
    p.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return p


def is_silent(pcm: bytes, peak_min: int = SILENCE_PEAK) -> bool:
    if len(pcm) < 4:
        return True
    n = len(pcm) // 2
    if n <= 0:
        return True
    samples = struct.unpack("<" + "h" * n, pcm[: n * 2])
    return max(abs(s) for s in samples) < peak_min


def write_pcm16_wav(path: Path, pcm: bytes, rate: int = RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def write_session_config(
    path: Path,
    *,
    out_dir: str,
    input_index: int,
    base: dict[str, Any] | None = None,
) -> Path:
    src = base if base is not None else {}
    body = {
        "out_dir": str(out_dir),
        "input_index": int(input_index),
    }
    if src:
        body["input_index"] = int(input_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def list_devices_cli() -> tuple[list[tuple[int, str]], int]:
    devices = list_input_devices()
    current = int(load_config().get("input_index") or 0)
    return devices, current


def prompt_session_dir() -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    recent = load_recent_dir()
    start = str(recent) if recent is not None else str(Path.home() / "test-write")
    start_p = Path(str(start))
    if not start_p.is_dir():
        start_p = Path.home()
    chosen = filedialog.askdirectory(
        parent=root,
        title="tangent-analyzer — folder for this session",
        initialdir=str(start_p),
        mustexist=True,
    )
    root.destroy()
    if not chosen:
        return None
    dest = Path(chosen)
    dest.mkdir(parents=True, exist_ok=True)
    return dest


class WinmmCapture:
    """Chunked WinMM capture. One device. Same 16 kHz mono as journal-clip."""

    def __init__(
        self,
        device_index: int,
        seconds: float,
        on_peak: Callable[[float], None] | None = None,
    ) -> None:
        self.device_index = device_index
        self.seconds = seconds
        self.on_peak = on_peak
        self._stop = threading.Event()
        self.pcm = bytearray()
        self.error: str | None = None

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> bytes:
        if sys.platform != "win32":
            self.error = "WinMM is Windows only"
            return b""
        import ctypes
        from ctypes import wintypes

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", wintypes.WORD),
                ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD),
                ("cbSize", wintypes.WORD),
            ]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [
                ("lpData", ctypes.c_void_p),
                ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD),
                ("dwUser", ctypes.c_void_p),
                ("dwFlags", wintypes.DWORD),
                ("dwLoops", wintypes.DWORD),
                ("lpNext", ctypes.c_void_p),
                ("reserved", ctypes.c_void_p),
            ]

        WHDR_DONE = 0x00000001
        chunk_bytes = CHUNK_SAMPLES * 2
        winmm = ctypes.windll.winmm
        wfx = WAVEFORMATEX(1, 1, RATE, RATE * 2, 2, 16, 0)
        hwi = ctypes.c_void_p()
        rc = winmm.waveInOpen(
            ctypes.byref(hwi),
            ctypes.c_uint(self.device_index),
            ctypes.byref(wfx),
            0,
            0,
            0,
        )
        if rc != 0:
            self.error = f"waveInOpen device {self.device_index} failed ({rc})"
            return b""

        bufs = [ctypes.create_string_buffer(chunk_bytes) for _ in range(NBUFS)]
        hdrs = (WAVEHDR * NBUFS)()
        for i, buf in enumerate(bufs):
            hdrs[i].lpData = ctypes.cast(buf, ctypes.c_void_p).value
            hdrs[i].dwBufferLength = chunk_bytes
            hdrs[i].dwBytesRecorded = 0
            hdrs[i].dwFlags = 0
            hdrs[i].dwLoops = 0
            if winmm.waveInPrepareHeader(hwi, ctypes.byref(hdrs[i]), ctypes.sizeof(WAVEHDR)) != 0:
                self.error = "waveInPrepareHeader failed"
                winmm.waveInClose(hwi)
                return b""
            winmm.waveInAddBuffer(hwi, ctypes.byref(hdrs[i]), ctypes.sizeof(WAVEHDR))

        if winmm.waveInStart(hwi) != 0:
            self.error = "waveInStart failed"
            winmm.waveInReset(hwi)
            winmm.waveInClose(hwi)
            return b""

        deadline = time.monotonic() + max(0.4, float(self.seconds))
        try:
            while not self._stop.is_set() and time.monotonic() < deadline:
                for i, buf in enumerate(bufs):
                    if hdrs[i].dwFlags & WHDR_DONE:
                        n = int(hdrs[i].dwBytesRecorded)
                        if n > 0:
                            chunk = buf.raw[:n]
                            self.pcm.extend(chunk)
                            if self.on_peak:
                                arr = array.array("h")
                                arr.frombytes(chunk[: len(chunk) // 2 * 2])
                                pk = max((abs(x) for x in arr), default=0) / 32767.0
                                self.on_peak(pk)
                        hdrs[i].dwBytesRecorded = 0
                        hdrs[i].dwFlags = hdrs[i].dwFlags & ~WHDR_DONE
                        winmm.waveInAddBuffer(hwi, ctypes.byref(hdrs[i]), ctypes.sizeof(WAVEHDR))
                time.sleep(0.01)
        finally:
            winmm.waveInStop(hwi)
            winmm.waveInReset(hwi)
            for i in range(NBUFS):
                winmm.waveInUnprepareHeader(hwi, ctypes.byref(hdrs[i]), ctypes.sizeof(WAVEHDR))
            winmm.waveInClose(hwi)
        return bytes(self.pcm)


class TaUi:
    def __init__(self, out_dir: Path) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.out_dir = out_dir.resolve()
        self.session_cfg = Path(tempfile.gettempdir()) / f"sesefus-ta-ui-{os.getpid()}.json"
        self.log_q: queue.Queue[str] = queue.Queue()
        self.busy = False
        self.capturing = False
        self.capture: WinmmCapture | None = None
        self.devices: list[tuple[int, str]] = [(0, "default")]
        self.peaks: deque[float] = deque([0.0] * 120, maxlen=120)
        self.peak_lock = threading.Lock()
        self._record_clicks = 0
        self._record_click_job: str | int | None = None
        save_recent_dir(self.out_dir)

        self.root = tk.Tk()
        self.root.title("tangent-analyzer")
        self.root.geometry("560x780")
        self.root.minsize(460, 560)
        style = ttk.Style(self.root)
        apply_look(self.root, style)

        pad = ttk.Frame(self.root)
        pad.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

        ttk.Label(pad, text="⬡  tangent-analyzer  /  leftover rank", style="Mast.TLabel").pack(
            anchor="w"
        )
        ttk.Label(pad, text="speak the prompt · paste the corpus · plate the rank", style="Soft.TLabel").pack(
            anchor="w", pady=(6, 10)
        )

        dirrow = ttk.Frame(pad)
        dirrow.pack(fill=tk.X, pady=(0, 8))
        self.dir_label = ttk.Label(dirrow, text=str(self.out_dir), style="Mute.TLabel", wraplength=400)
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ink_button(dirrow, "change", self.change_folder).pack(side=tk.RIGHT)

        ttk.Label(pad, text="input", style="Mute.TLabel").pack(anchor="w")
        self.device_var = tk.StringVar()
        self.combo = ttk.Combobox(pad, textvariable=self.device_var, state="readonly", width=62)
        self.combo.pack(fill=tk.X, pady=(0, 4))
        self.warn = ttk.Label(pad, text="", style="Warn.TLabel")
        self.warn.pack(anchor="w", pady=(0, 8))

        ttk.Label(
            pad,
            text="record clicks  1=10s  2=20s  3=30s  4=40s   ·  stop sends early",
            style="Mute.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.wave = tk.Canvas(
            pad,
            height=72,
            bg=VOID,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.wave.pack(fill=tk.X, pady=(0, 8))

        self.record_btn = ink_button(pad, "record   1–4 clicks", self.on_record_click, primary=True)
        self.record_btn.pack(fill=tk.X, pady=(0, 8))

        self.status = ttk.Label(pad, text="ready", style="Soft.TLabel")
        self.status.pack(anchor="w", pady=(0, 6))

        ttk.Label(pad, text="paste", style="Mute.TLabel").pack(anchor="w")
        self.paste = plate(pad, height=6)
        self.paste.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.paste.insert("1.0", "")

        ttk.Label(pad, text="voice prompt", style="Mute.TLabel").pack(anchor="w")
        self.prompt_line = ttk.Label(pad, text="(speak after you paste)", style="Soft.TLabel")
        self.prompt_line.pack(anchor="w", pady=(0, 6))

        ttk.Label(pad, text=LOWER_PLATE_LABEL, style="Mute.TLabel").pack(anchor="w")
        self.plate = plate(pad, height=8)
        self.plate.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.plate.insert("1.0", "ranked leftovers land here.")
        self.plate.configure(state="disabled")

        ttk.Label(pad, text="log", style="Mute.TLabel").pack(anchor="w")
        self.log = log_box(pad, height=5)
        self.log.pack(fill=tk.X)
        self.log.configure(state="disabled")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.reload_devices()
        self.root.after(50, self._pump)

    def paste_text(self) -> str:
        return self.paste.get("1.0", "end").strip()

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        if not text.endswith("\n"):
            self.log.insert("end", "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _pump(self) -> None:
        try:
            while True:
                self.append_log(self.log_q.get_nowait())
        except queue.Empty:
            pass
        self._draw_wave()
        self.root.after(50, self._pump)

    def _draw_wave(self) -> None:
        c = self.wave
        w = int(c.winfo_width() or 500)
        h = int(c.winfo_height() or 72)
        c.delete("all")
        mid = h // 2
        c.create_line(0, mid, w, mid, fill=LINE)
        with self.peak_lock:
            peaks = list(self.peaks)
        n = len(peaks)
        if n < 2:
            return
        pts: list[float] = []
        for i, p in enumerate(peaks):
            x = i * (w - 1) / (n - 1)
            y = mid - p * (h * 0.42)
            pts.extend((x, y))
        color = CYAN if self.capturing else INK_MUTE
        c.create_line(*pts, fill=color, smooth=True)

    def selected_index(self) -> int:
        raw = self.device_var.get()
        m = re.match(r"^\[(\d+)\]", raw)
        if m:
            return int(m.group(1))
        return self.devices[0][0] if self.devices else 0

    def selected_name(self) -> str:
        raw = self.device_var.get()
        m = re.match(r"^\[\d+\]\s+(.*)$", raw)
        return m.group(1).strip() if m else ""

    def set_warn(self, text: str) -> None:
        self.warn.configure(text=text)

    def set_plate(self, text: str) -> None:
        self.plate.configure(state="normal")
        self.plate.delete("1.0", "end")
        self.plate.insert("1.0", text)
        self.plate.configure(state="disabled")

    def reload_devices(self) -> None:
        try:
            self.devices, current = list_devices_cli()
        except Exception as e:
            self.devices, current = [(0, "default")], 0
            self.append_log(f"device list failed: {e}")
        labels = [f"[{i}] {name}" for i, name in self.devices]
        self.combo["values"] = labels
        pick_i = pick_default_device(self.devices, current)
        pick = next((lab for lab in labels if lab.startswith(f"[{pick_i}]")), None)
        self.device_var.set(pick or (labels[0] if labels else "[0] default"))
        name = self.selected_name()
        if not self.devices or (len(self.devices) == 1 and self.devices[0][1] == "default"):
            self.set_warn("no capture device — plug in the USB mic")
        elif not device_is_usb_mic(name):
            self.set_warn("USB / Maono mic not found — pick it in the list if it is plugged in")
        else:
            self.set_warn("")

    def change_folder(self) -> None:
        if self.busy:
            return
        chosen = prompt_session_dir()
        if chosen is None:
            return
        self.out_dir = chosen.resolve()
        save_recent_dir(self.out_dir)
        self.dir_label.configure(text=str(self.out_dir))
        self.append_log(f"— folder {self.out_dir}")

    def on_record_click(self) -> None:
        if self.capturing and self.capture is not None:
            self.capture.stop()
            return
        if self.busy and self._record_click_job is None:
            return
        self._record_clicks = min(self._record_clicks + 1, MAX_RECORD_CLICKS)
        seconds = record_clicks_to_seconds(self._record_clicks)
        self.status.configure(text=f"{seconds}s — click again up to 40s")
        if self._record_click_job is not None:
            try:
                self.root.after_cancel(self._record_click_job)
            except Exception:
                pass
        self._record_click_job = self.root.after(CLICK_WAIT_MS, self._commit_record_clicks)

    def _commit_record_clicks(self) -> None:
        clicks = self._record_clicks
        self._record_clicks = 0
        self._record_click_job = None
        self.start_record(record_clicks_to_seconds(clicks))

    def start_record(self, seconds: int) -> None:
        if self.busy or self.capturing:
            return
        if not self.paste_text():
            self.set_warn("paste the corpus first — voice is the prompt, not the data")
            self.set_plate("tangent analysis failed.\nempty paste")
            self.status.configure(text="empty paste")
            return
        idx = self.selected_index()
        write_session_config(
            self.session_cfg,
            out_dir=str(self.out_dir),
            input_index=idx,
            base=load_config(),
        )
        self.busy = True
        self.capturing = True
        self.record_btn.configure(text="stop / send")
        self.status.configure(text=f"recording prompt — speak  (max {seconds}s)")
        self.set_warn("")
        self.set_plate("listening for the voice prompt…")
        self.append_log(f"— capture  dir={self.out_dir}  input={idx}  seconds={seconds}")
        with self.peak_lock:
            self.peaks.clear()
            self.peaks.extend([0.0] * 120)
        cap = WinmmCapture(idx, seconds, on_peak=self._on_peak)
        self.capture = cap
        threading.Thread(target=self._capture_then_analyze, args=(cap,), daemon=True).start()

    def _on_peak(self, peak: float) -> None:
        with self.peak_lock:
            self.peaks.append(max(0.0, min(1.0, peak)))

    def _capture_then_analyze(self, cap: WinmmCapture) -> None:
        pcm = cap.run()
        self.capturing = False
        self.capture = None
        if cap.error:
            self.log_q.put(f"— capture failed: {cap.error}")
            self.root.after(0, lambda: self.set_plate("no input — capture failed."))
            self.root.after(0, lambda: self._idle("no input — capture failed"))
            self.root.after(0, lambda: self.set_warn("no input detected (device failed to open)"))
            return
        if is_silent(pcm):
            self.log_q.put("— no input detected (mic silent or wrong device)")
            self.root.after(0, lambda: self._warn_silent())
            return
        wav = Path(tempfile.gettempdir()) / f"sesefus-ta-ui-{os.getpid()}-{int(time.time())}.wav"
        write_pcm16_wav(wav, pcm)
        dur = len(pcm) / (RATE * 2)
        self.log_q.put(f"— captured {dur:.1f}s  → whisper then leftover rank")
        self.root.after(0, lambda: self.status.configure(text="transcribing prompt…"))
        paste = self.paste_text()
        self.root.after(0, lambda: self.record_btn.configure(text="working…", state="disabled"))
        self._run_heavy(wav, paste)

    def _warn_silent(self) -> None:
        self.set_warn("no input detected — USB mic muted, unplugged, or wrong device")
        self.set_plate("no input detected.")
        self._idle("no input detected")

    def _run_heavy(self, wav: Path, paste: str) -> None:
        from ta_heavy import run as heavy_run

        result: dict[str, Any] | None = None
        err: str | None = None
        try:
            result = heavy_run(prompt="", paste=paste, wav=wav)
        except Exception as e:
            err = str(e)
            if wav.is_file():
                from ta_heavy import shred_temp

                shred_temp(wav)
        if err:
            self.log_q.put(f"— analysis failed: {err}")
            self.root.after(0, lambda: self.set_plate(f"tangent analysis failed.\n{err}"))
            self.root.after(0, lambda: self._idle("tangent analysis failed"))
            return
        assert result is not None
        prompt = str(result.get("prompt") or "").strip()
        self.root.after(0, lambda: self.prompt_line.configure(text=prompt or "(empty prompt)"))
        if not result.get("ok"):
            msg = str(result.get("error") or "analysis failed")
            self.log_q.put(f"— {msg}")
            self.root.after(0, lambda: self.set_plate(f"tangent analysis failed.\n{msg}"))
            self.root.after(0, lambda: self._idle("tangent analysis failed"))
            return
        text = str(result.get("analysis") or "").strip()
        n = len(result.get("clusters") or [])
        self.log_q.put(f"— ranked {n} leftover cluster(s)  wav_shredded={result.get('wav_shredded')}")
        self.root.after(0, lambda: self._show_analysis(text, n, list(result.get("degraded") or [])))

    def _show_analysis(self, text: str, n: int, degraded: list[str]) -> None:
        self.set_plate(text or "(empty)")
        if degraded:
            self.set_warn(f"{n} clusters · mouth issue: {degraded[0]}")
        else:
            self.set_warn("")
        self._idle("ready")

    def _idle(self, status: str) -> None:
        self.busy = False
        self.capturing = False
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        self.record_btn.configure(state="normal", text="record   1–4 clicks")
        self.status.configure(text=status)

    def on_close(self) -> None:
        if self._record_click_job is not None:
            try:
                self.root.after_cancel(self._record_click_job)
            except Exception:
                pass
        if self.capture is not None:
            self.capture.stop()
        if not self.busy:
            try:
                if self.session_cfg.is_file():
                    self.session_cfg.unlink()
            except OSError:
                pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    out = load_recent_dir()
    if out is None:
        out = prompt_session_dir()
    if out is None:
        return 0
    save_recent_dir(out)
    TaUi(out).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
