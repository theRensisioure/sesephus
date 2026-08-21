const std = @import("std");

pub fn handleJournalCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    _ = allocator;
    _ = io;
    const action = it.next() orelse {
        std.debug.print("Usage: journal <record|review|prompt>\n", .{});
        return true;
    };

    if (std.mem.eql(u8, action, "record")) {
        std.debug.print("[Journal] Starting audio journaling session...\n", .{});
    } else if (std.mem.eql(u8, action, "review")) {
        std.debug.print("[Journal] Reviewing recent audio entries...\n", .{});
    } else if (std.mem.eql(u8, action, "prompt")) {
        std.debug.print("[Journal] Generating a stoic reflection prompt...\n", .{});
    } else {
        std.debug.print("Unknown journal command: {s}\n", .{action});
    }
    return true;
}
