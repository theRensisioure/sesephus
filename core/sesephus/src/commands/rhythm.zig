const std = @import("std");

fn contains(haystack: []const u8, needle: []const u8) bool {
    if (needle.len == 0 or needle.len > haystack.len) return false;
    var i: usize = 0;
    while (i + needle.len <= haystack.len) : (i += 1) {
        if (std.mem.eql(u8, haystack[i .. i + needle.len], needle)) return true;
    }
    return false;
}

/// Shipped rhythm reply. Still STUB — live scheduler is `alarm`.
pub fn renderRhythm(allocator: std.mem.Allocator, action: []const u8, slot: []const u8) ![]u8 {
    var body = std.ArrayList(u8).empty;
    errdefer body.deinit(allocator);
    var allocating: std.Io.Writer.Allocating = .fromArrayList(allocator, &body);
    const aw = &allocating.writer;

    if (std.mem.eql(u8, action, "schedule")) {
        try aw.print("[Rhythm] STUB — schedule is not live. Use alarm schedule (not rhythm {s}).\n", .{slot});
    } else if (std.mem.eql(u8, action, "status")) {
        try aw.print("[Rhythm] STUB — no live circadian state. Use alarm list.\n", .{});
    } else if (std.mem.eql(u8, action, "next")) {
        try aw.print("[Rhythm] STUB — deferred to alarm. No fake countdown. Use alarm list.\n", .{});
    } else {
        try aw.print("Unknown rhythm command: {s}\n", .{action});
        try aw.print("Usage: rhythm <schedule|status|next> — STUB; live scheduler is alarm.\n", .{});
    }

    body = allocating.toArrayList();
    return try body.toOwnedSlice(allocator);
}

pub fn handleRhythmCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    _ = io;
    const action = it.next() orelse {
        std.debug.print("Usage: rhythm <schedule|status|next> — STUB; live scheduler is alarm.\n", .{});
        return true;
    };
    const slot = it.next() orelse "morning";
    const msg = try renderRhythm(allocator, action, slot);
    defer allocator.free(msg);
    std.debug.print("{s}", .{msg});
    return true;
}

test "rhythm stays STUB and defers to alarm without fake ALIGNED or 4 hours" {
    const allocator = std.testing.allocator;

    const status = try renderRhythm(allocator, "status", "morning");
    defer allocator.free(status);
    const next = try renderRhythm(allocator, "next", "morning");
    defer allocator.free(next);
    const schedule = try renderRhythm(allocator, "schedule", "evening");
    defer allocator.free(schedule);

    try std.testing.expect(contains(status, "STUB"));
    try std.testing.expect(contains(status, "alarm"));
    try std.testing.expect(!contains(status, "ALIGNED"));
    try std.testing.expect(contains(next, "STUB"));
    try std.testing.expect(contains(next, "alarm"));
    try std.testing.expect(!contains(next, "4 hours"));
    try std.testing.expect(contains(schedule, "STUB"));
    try std.testing.expect(contains(schedule, "alarm"));
}

test "handleRhythmCommand status entry point stays stub" {
    const allocator = std.testing.allocator;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    var it = std.mem.tokenizeAny(u8, "status", " ");
    try std.testing.expect(try handleRhythmCommand(&it, allocator, threaded.io()));
}
