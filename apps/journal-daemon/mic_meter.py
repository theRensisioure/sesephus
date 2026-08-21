#!/usr/bin/env python3
"""Levels-only shared-mic sample for the hop Record button.

One short WASAPI/DirectSound InputStream read. No file. No Whisper.
Record click does not depend on this meter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def sample_meter(
    device: str = "",
    duration_ms: int = 80,
    *,
    devices: Any = None,
    hostapis: Any = None,
    scratch: Path | None = None,
) -> dict:
    """Return one {ok, rms, peak, device_id} sample. scratch is ignored (no write)."""
    del scratch  # contract: never write a wav or sidecar
    duration_ms = min(100, max(1, int(duration_ms or 80)))
    from ui_serve import list_inputs

    prefer = str(device or "")
    listed = list_inputs(devices=devices, hostapis=hostapis, prefer=prefer)
    picked = listed.get("picked") if listed.get("ok") else None
    device_id = str((picked or {}).get("device_id") or "")
    if not picked:
        return {
            "ok": False,
            "error": listed.get("error") or "no shared input matching the selected device",
            "rms": 0.0,
            "peak": 0.0,
            "device_id": device_id,
        }

    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        return {
            "ok": False,
            "error": "sounddevice is not installed",
            "rms": 0.0,
            "peak": 0.0,
            "device_id": device_id,
        }

    idx = int(picked["index"])
    ch = min(2, max(1, int(picked.get("channels") or 1)))
    sr = int(picked.get("samplerate") or 48000)
    frames = max(1, int(sr * duration_ms / 1000.0))
    extra = None
    if "wasapi" in str(picked.get("hostapi") or "").lower():
        try:
            extra = sd.WasapiSettings(exclusive=False)
        except Exception:
            extra = None
    kwargs: dict[str, Any] = {
        "device": idx,
        "channels": ch,
        "samplerate": sr,
        "dtype": "float32",
        "blocksize": frames,
    }
    if extra is not None:
        kwargs["extra_settings"] = extra
    try:
        with sd.InputStream(**kwargs) as stream:
            data, _overflow = stream.read(frames)
    except Exception as e:
        return {
            "ok": False,
            "error": " ".join(str(e).split())[:200],
            "rms": 0.0,
            "peak": 0.0,
            "device_id": device_id,
        }

    arr = np.asarray(data, dtype=np.float32)
    if arr.size == 0:
        rms = 0.0
        peak = 0.0
    else:
        rms = float(np.sqrt(np.mean(np.square(arr))))
        peak = float(np.max(np.abs(arr)))
    return {"ok": True, "rms": rms, "peak": peak, "device_id": device_id}
