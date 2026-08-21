const std = @import("std");

pub fn handleStoicCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    _ = allocator;
    _ = io;
    const action = it.next() orelse {
        std.debug.print("Usage: stoic <daily-reflection|virtue-check|obstacle>\n", .{});
        return true;
    };

    if (std.mem.eql(u8, action, "daily-reflection")) {
        std.debug.print("[Stoic] Starting evening daily reflection...\n", .{});
    } else if (std.mem.eql(u8, action, "virtue-check")) {
        const virtue = it.next() orelse "courage";
        std.debug.print("[Stoic] Virtue alignment check-in for: {s}\n", .{virtue});
    } else if (std.mem.eql(u8, action, "obstacle")) {
        std.debug.print("[Stoic] Journaling current obstacle and premeditatio malorum...\n", .{});
    } else {
        std.debug.print("Unknown stoic command: {s}\n", .{action});
    }
    return true;
}
