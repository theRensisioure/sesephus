//! Shared flip math — single source for native and look prototypes.
//! Ported from spikes/004-card-surface/zig-flip; keep JS flip.js in lockstep.

const std = @import("std");

pub const FLIP_STEPS: i32 = 8;
pub const FLIP_MS: u32 = 16;

/// The widest a card may be, as w:h (4:5).
pub const PORTRAIT: f64 = 4.0 / 5.0;

/// Width scale for a squash flip. 1 at the ends, edge-on (0.02) at the midpoint.
pub fn flipWidthScale(step: i32, steps: i32) f64 {
    const n = @max(2, steps);
    const half = @divFloor(n, 2);
    const s = @max(0, step);
    if (s <= 0 or s >= n) return 1.0;
    const s_f: f64 = @floatFromInt(s);
    const half_f: f64 = @floatFromInt(half);
    if (s <= half) return @max(0.02, 1.0 - (s_f / half_f));
    return @max(0.02, (s_f - half_f) / half_f);
}

/// The step at which the faces swap (the midpoint, never below 1).
pub fn flipSwapStep(steps: i32) i32 {
    return @max(1, @divFloor(steps, 2));
}

pub const Box = struct { w: i64, h: i64 };

/// Biggest card a slot holds that is still portrait.
pub fn portraitBox(slot_w: i64, slot_h: i64, ratio: f64) Box {
    const h = @max(1, slot_h);
    const h_f: f64 = @floatFromInt(h);
    const cap: i64 = @intFromFloat(h_f * ratio);
    return .{ .w = @max(1, @min(slot_w, cap)), .h = h };
}

pub const Flip = struct {
    is_back: bool = false,
    flipping: bool = false,
    step: i32 = 0,
    dest_back: bool = false,

    pub fn start(self: *Flip, animate: bool) bool {
        if (self.flipping) return false;
        const nxt = !self.is_back;
        if (!animate) {
            self.is_back = nxt;
            return true;
        }
        self.flipping = true;
        self.step = 0;
        self.dest_back = nxt;
        return true;
    }

    pub fn tick(self: *Flip) f64 {
        const step = self.step;
        if (step == flipSwapStep(FLIP_STEPS)) self.is_back = self.dest_back;
        const scale = flipWidthScale(step, FLIP_STEPS);
        if (step >= FLIP_STEPS) {
            self.flipping = false;
            return 1.0;
        }
        self.step = step + 1;
        return scale;
    }

    pub fn cancel(self: *Flip) void {
        self.flipping = false;
    }
};

const testing = std.testing;

test "flip scale is edge-on at midpoint" {
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(0, 8));
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(8, 8));
    try testing.expect(flipWidthScale(4, 8) <= 0.02);
    try testing.expectEqual(@as(i32, 4), flipSwapStep(8));
}

test "scale curve over all 8 steps" {
    const want = [_]f64{ 1.0, 0.75, 0.5, 0.25, 0.02, 0.25, 0.5, 0.75, 1.0 };
    for (want, 0..) |w, i| {
        try testing.expectApproxEqAbs(w, flipWidthScale(@intCast(i), 8), 1e-12);
    }
}

test "card box is portrait" {
    const wide = portraitBox(1100, 650, PORTRAIT);
    try testing.expectEqual(@as(i64, 520), wide.w);
    try testing.expectEqual(@as(i64, 650), wide.h);
}

test "state machine swaps at step 4" {
    var f: Flip = .{};
    try testing.expect(f.start(true));
    var i: i32 = 0;
    while (i < 4) : (i += 1) {
        _ = f.tick();
        try testing.expect(!f.is_back);
    }
    _ = f.tick();
    try testing.expect(f.is_back);
}
