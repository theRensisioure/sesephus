//! Global CLI flags and shared prompts. Extracted from core/sesephus/src/cli.zig.

const std = @import("std");

pub const GlobalFlags = struct {
    production: bool = false,
    dry_run: bool = false,
    json: bool = false,
};

/// Scan the full argv for global flags; positional parsing happens per-command.
pub fn parseGlobalFlags(args: []const []const u8) GlobalFlags {
    var flags = GlobalFlags{};
    for (args) |arg| {
        if (std.mem.eql(u8, arg, "--production")) {
            flags.production = true;
        } else if (std.mem.eql(u8, arg, "--dry-run") or std.mem.eql(u8, arg, "-n")) {
            flags.dry_run = true;
        } else if (std.mem.eql(u8, arg, "--json")) {
            flags.json = true;
        }
    }
    return flags;
}

/// In production mode, destructive actions require an interactive y/N confirm.
pub fn confirmDestructive(production_mode: bool, io: std.Io) bool {
    if (!production_mode) return true;
    std.debug.print("\n[WARNING] Destructive action requested in PRODUCTION mode.\n", .{});
    std.debug.print("Are you sure you want to proceed? (y/N): ", .{});

    const stdin_file = std.Io.File.stdin();
    var stdin_buf: [10]u8 = undefined;
    var stdin_reader = stdin_file.reader(io, &stdin_buf);
    if (stdin_reader.interface.takeDelimiter('\n') catch null) |line| {
        const trimmed = std.mem.trim(u8, line, "\r ");
        if (std.mem.eql(u8, trimmed, "y") or std.mem.eql(u8, trimmed, "Y")) {
            return true;
        }
    }
    std.debug.print("Action aborted.\n", .{});
    return false;
}

/// CLI exit codes per docs/ARCHITECTURE.md
pub const ExitCode = struct {
    pub const success: u8 = 0;
    pub const usage: u8 = 1;
    pub const io_error: u8 = 2;
    pub const partial_failure: u8 = 3;
};
