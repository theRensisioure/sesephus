// Shared flip math — keep in lockstep with core/sesephus/src/anim/flip.zig
export const FLIP_STEPS = 8;
export const FLIP_MS = 16;
export const PORTRAIT = 4 / 5;

export function flipWidthScale(step, steps) {
  const n = Math.max(2, steps);
  const half = Math.floor(n / 2);
  const s = Math.max(0, step);
  if (s <= 0 || s >= n) return 1;
  if (s <= half) return Math.max(0.02, 1 - (s / half));
  return Math.max(0.02, (s - half) / half);
}

export function flipSwapStep(steps) {
  return Math.max(1, Math.floor(steps / 2));
}

export function portraitBox(slotW, slotH, ratio) {
  const h = Math.max(1, slotH);
  const cap = Math.trunc(h * ratio);
  return { w: Math.max(1, Math.min(slotW, cap)), h: h };
}

export function createFlip() {
  return {
    is_back: false,
    flipping: false,
    step: 0,
    dest_back: false,
    timer: 0,
    start(animate) {
      if (this.flipping) return false;
      const nxt = !this.is_back;
      if (!animate) {
        this.is_back = nxt;
        return true;
      }
      this.flipping = true;
      this.step = 0;
      this.dest_back = nxt;
      return true;
    },
    tick() {
      const step = this.step;
      if (step === flipSwapStep(FLIP_STEPS)) this.is_back = this.dest_back;
      const scale = flipWidthScale(step, FLIP_STEPS);
      if (step >= FLIP_STEPS) {
        this.flipping = false;
        return 1;
      }
      this.step = step + 1;
      return scale;
    },
    resetFront() {
      clearTimeout(this.timer);
      this.flipping = false;
      this.step = 0;
      this.is_back = false;
      this.dest_back = false;
    },
  };
}
