//! Spike 004b: the flip math of clip_flip.py as pure Zig functions.
//! Ported by hand from the Python original; no allocation, no I/O, no UI.

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

/// The biggest card a slot this size holds that is still portrait.
/// Width is capped at `ratio` of the height; height is never trimmed.
/// Both dimensions are at least 1, so a zero-size slot gives a 1x1 box.
pub fn portraitBox(slot_w: i64, slot_h: i64, ratio: f64) Box {
    const h = @max(1, slot_h);
    const h_f: f64 = @floatFromInt(h);
    const cap: i64 = @intFromFloat(h_f * ratio); // truncates toward zero, like Python int()
    return .{ .w = @max(1, @min(slot_w, cap)), .h = h };
}

/// The flip state machine of FlipFaces, minus the widgets.
/// `start` is the button; `tick` is the timer callback (call every FLIP_MS).
pub const Flip = struct {
    is_back: bool = false,
    flipping: bool = false,
    step: i32 = 0,
    dest_back: bool = false,

    /// Returns false if ignored because a flip is already running.
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

    /// One timer tick. Returns the width scale to apply now.
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

    /// Stop a flip mid-turn. is_back stays wherever the last swap left it.
    pub fn cancel(self: *Flip) void {
        self.flipping = false;
    }
};

// ---- tests copied (by hand) from python/tests/test_flip.py -------------

const testing = std.testing;

test "flip scale is edge-on at midpoint" {
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(0, 8));
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(8, 8));
    try testing.expect(flipWidthScale(4, 8) <= 0.02);
    try testing.expectEqual(@as(i32, 4), flipSwapStep(8));
    try testing.expect(flipWidthScale(2, 8) > flipWidthScale(4, 8));
    try testing.expect(flipWidthScale(6, 8) > flipWidthScale(4, 8));
}

test "card box is portrait in any slot" {
    const slots = [_][2]i64{ .{ 1100, 650 }, .{ 484, 648 }, .{ 240, 900 }, .{ 900, 240 }, .{ 1, 1 } };
    for (slots) |slot| {
        const b = portraitBox(slot[0], slot[1], PORTRAIT);
        try testing.expect(b.w <= slot[0]);
        try testing.expectEqual(@max(1, slot[1]), b.h); // always reaches the bottom
        const limit: f64 = @as(f64, @floatFromInt(b.h)) * PORTRAIT + 1;
        try testing.expect(@as(f64, @floatFromInt(b.w)) <= limit);
    }
    // wide: width capped at the ratio
    const wide = portraitBox(1100, 650, PORTRAIT);
    try testing.expectEqual(@as(i64, @intFromFloat(@as(f64, 650) * PORTRAIT)), wide.w);
    try testing.expectEqual(@as(i64, 650), wide.h);
    // tall: nothing trimmed
    const tall = portraitBox(240, 900, PORTRAIT);
    try testing.expectEqual(@as(i64, 240), tall.w);
    try testing.expectEqual(@as(i64, 900), tall.h);
}

test "the reference card is not trimmed" {
    const b = portraitBox(484, 648, PORTRAIT);
    try testing.expectEqual(@as(i64, 484), b.w);
    try testing.expectEqual(@as(i64, 648), b.h);
}

// ---- extra edge cases -------------------------------------------------

test "PORTRAIT is the same double as Python 4/5" {
    try testing.expectEqual(@as(u64, 0x3FE999999999999A), @as(u64, @bitCast(PORTRAIT)));
}

test "wide slot gives 520 for height 650 (float product is exact)" {
    try testing.expectEqual(@as(i64, 520), portraitBox(1100, 650, PORTRAIT).w);
}

test "zero-size slot gives a 1x1 box" {
    const b = portraitBox(0, 0, PORTRAIT);
    try testing.expectEqual(@as(i64, 1), b.w);
    try testing.expectEqual(@as(i64, 1), b.h);
}

test "negative slot gives a 1x1 box" {
    const b = portraitBox(-5, -9, PORTRAIT);
    try testing.expectEqual(@as(i64, 1), b.w);
    try testing.expectEqual(@as(i64, 1), b.h);
}

test "scale curve over all 8 steps" {
    const want = [_]f64{ 1.0, 0.75, 0.5, 0.25, 0.02, 0.25, 0.5, 0.75, 1.0 };
    for (want, 0..) |w, i| {
        try testing.expectApproxEqAbs(w, flipWidthScale(@intCast(i), 8), 1e-12);
    }
}

test "scale clamps odd inputs like the Python" {
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(-3, 8));
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(99, 8));
    // steps below 2 are raised to 2: step 1 of 2 is the midpoint
    try testing.expectEqual(@as(f64, 0.02), flipWidthScale(1, 0));
    try testing.expectEqual(@as(i32, 1), flipSwapStep(0));
    try testing.expectEqual(@as(i32, 1), flipSwapStep(1));
}

test "state machine: non-animated flip toggles at once" {
    var f: Flip = .{};
    try testing.expect(f.start(false));
    try testing.expect(f.is_back);
    try testing.expect(!f.flipping);
}

test "state machine: animated flip swaps at step 4 and ends at 1.0" {
    var f: Flip = .{};
    try testing.expect(f.start(true));
    try testing.expect(!f.is_back); // not swapped until the midpoint
    var i: i32 = 0;
    while (i < 4) : (i += 1) {
        _ = f.tick();
        try testing.expect(!f.is_back);
    }
    _ = f.tick(); // step 4
    try testing.expect(f.is_back);
    while (f.flipping) _ = f.tick();
    try testing.expect(f.is_back);
    try testing.expectEqual(@as(f64, 1.0), flipWidthScale(f.step, FLIP_STEPS));
}

test "state machine: a second flip during a flip is ignored" {
    var f: Flip = .{};
    try testing.expect(f.start(true));
    try testing.expect(!f.start(true));
    try testing.expect(!f.start(false));
    try testing.expect(!f.is_back);
}

test "state machine: cancel leaves the face where the last swap put it" {
    var f: Flip = .{};
    _ = f.start(true);
    _ = f.tick();
    f.cancel();
    try testing.expect(!f.flipping);
    try testing.expect(!f.is_back);
}
