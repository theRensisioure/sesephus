import sys
src = open(sys.argv[1], encoding="utf-8").read().splitlines()
code = "\n".join(src[27:63])   # FLIP_STEPS .. portrait_box
ns = {}
exec("from __future__ import annotations\n" + code, ns)
for steps in (0, 1, 2, 3, 5, 8, 9, 16):
    for step in (-2, 0, 1, 2, 3, 4, 5, 7, 8, 9, 20):
        print("s", step, steps, repr(ns["flip_width_scale"](step, steps)))
    print("w", steps, ns["flip_swap_step"](steps))
for w in (-5, 0, 1, 7, 100, 484, 1100, 240, 900):
    for h in (-3, 0, 1, 3, 7, 240, 648, 650, 900, 12345):
        print("b", w, h, ns["portrait_box"](w, h))
