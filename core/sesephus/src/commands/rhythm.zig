const std = @import("std");

pub fn handleRhythmCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    _ = allocator;
    _ = io;
    const action = it.next() orelse {
        std.debug.print("Usage: rhythm <schedule|status|next>\n", .{});
        return true;
    };

    if (std.mem.eql(u8, action, "schedule")) {
        const time_slot = it.next() orelse "morning";
        std.debug.print("[Rhythm] Scheduling {s} anchor cue...\n", .{time_slot});
    } else if (std.mem.eql(u8, action, "status")) {
        std.debug.print("[Rhythm] Current circadian entrainment state is: ALIGNED\n", .{});
    } else if (std.mem.eql(u8, action, "next")) {
        std.debug.print("[Rhythm] Next anchor cue scheduled in 4 hours.\n", .{});
    } else {
        std.debug.print("Unknown rhythm command: {s}\n", .{action});
    }
    return true;
}
