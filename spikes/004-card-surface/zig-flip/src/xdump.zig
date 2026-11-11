const std = @import("std");
const f = @import("flip.zig");
test "dump" {
    for ([_]i32{ 0, 1, 2, 3, 5, 8, 9, 16 }) |steps| {
        for ([_]i32{ -2, 0, 1, 2, 3, 4, 5, 7, 8, 9, 20 }) |step| {
            std.debug.print("s {d} {d} {d}\n", .{ step, steps, f.flipWidthScale(step, steps) });
        }
        std.debug.print("w {d} {d}\n", .{ steps, f.flipSwapStep(steps) });
    }
    for ([_]i64{ -5, 0, 1, 7, 100, 484, 1100, 240, 900 }) |w| {
        for ([_]i64{ -3, 0, 1, 3, 7, 240, 648, 650, 900, 12345 }) |h| {
            const b = f.portraitBox(w, h, f.PORTRAIT);
            std.debug.print("b {d} {d} ({d}, {d})\n", .{ w, h, b.w, b.h });
        }
    }
}
