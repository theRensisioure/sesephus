#!/usr/bin/env python3
"""Goal-minting window. Not journal transcription. Not a mic recorder."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from cli import DEFAULT_OUT  # noqa: E402
from mint import EmptyInputError, mint, render_packet, write_packet  # noqa: E402

WINDOW_TITLE = "goal-minter · goal minting"
MAST = "⬡  goal-minter  /  goal minting"

BG = "#050509"
INK = "#e7e7f2"
CYAN = "#7cf7ff"
AMBER = "#e2a24a"
PANEL = "#101018"
VOID = "#0a0a10"
LINE = "#272739"


def attach_goal_divider(parent, tk, *, command):
    """Hairline between objective and packet; mint sits centered on it."""
    mid = tk.Frame(parent, bg=BG)
    mid.pack(fill=tk.X, pady=12)
    mid.grid_columnconfigure(0, weight=1)
    mid.grid_columnconfigure(1, weight=0)
    mid.grid_columnconfigure(2, weight=1)
    mid.grid_rowconfigure(0, weight=1)

    def hair(col: int) -> None:
        hold = tk.Frame(mid, bg=BG)
        hold.grid(row=0, column=col, sticky="nsew", padx=10)
        line = tk.Frame(hold, bg=LINE, height=1)
        line.place(relx=0, rely=0.5, relwidth=1, height=1, anchor="w")

    hair(0)
    tk.Button(
        mid,
        text="mint packet",
        command=command,
        bg=PANEL,
        fg=CYAN,
        activebackground="#17172a",
        activeforeground=CYAN,
        relief="flat",
        padx=16,
        pady=8,
    ).grid(row=0, column=1)
    hair(2)
    return mid


def run_window() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as e:
        print(f"error: goal-minting window unavailable: {e}", file=sys.stderr)
        return 1

    win = tk.Tk()
    win.title(WINDOW_TITLE)
    win.geometry("720x560")
    win.minsize(520, 420)
    win.configure(bg=BG)
    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", background=BG, foreground=INK, fieldbackground=PANEL)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("Mast.TLabel", background=BG, foreground=CYAN, font=("Consolas", 9))
    style.configure("Soft.TLabel", background=BG, foreground="#a7a7bd")
    style.configure("Warn.TLabel", background=BG, foreground=AMBER)

    pad = ttk.Frame(win)
    pad.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

    ttk.Label(pad, text=MAST, style="Mast.TLabel").pack(anchor="w")
    ttk.Label(
        pad,
        text="paste a messy objective. mint a 3-Q packet. not transcription.",
        style="Soft.TLabel",
    ).pack(anchor="w", pady=(6, 8))

    src = tk.Text(
        pad,
        height=8,
        bg=VOID,
        fg=INK,
        insertbackground=CYAN,
        relief="flat",
        wrap="word",
        highlightthickness=1,
        highlightbackground=LINE,
        font=("Segoe UI", 11),
    )
    src.pack(fill=tk.BOTH, expand=True)

    def show_plate(body: str) -> None:
        plate.configure(state="normal")
        plate.delete("1.0", "end")
        plate.insert("1.0", body)
        plate.configure(state="disabled")

    def on_mint() -> None:
        text = src.get("1.0", "end")
        try:
            packet = mint(text)
        except EmptyInputError as e:
            status.configure(text=str(e))
            show_plate("")
            return
        dest = write_packet(packet, DEFAULT_OUT)
        show_plate(render_packet(packet))
        status.configure(text=f"wrote {dest}")

    attach_goal_divider(pad, tk, command=on_mint)

    plate = tk.Text(
        pad,
        height=12,
        bg=VOID,
        fg=INK,
        insertbackground=CYAN,
        relief="flat",
        wrap="word",
        highlightthickness=1,
        highlightbackground=LINE,
        font=("Consolas", 9),
        state="disabled",
    )
    plate.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    status = ttk.Label(pad, text="", style="Warn.TLabel")
    status.pack(anchor="w")

    win.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_window())
