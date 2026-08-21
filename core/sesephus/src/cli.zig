const std = @import("std");

pub const Command = enum {
    alarm,
    group,
    vault,
    status,
    help,
    exit,
    unknown,
};

pub const GlobalFlags = struct {
    production: bool = false,
    dry_run: bool = false,
    json: bool = false,
    expert: bool = false,
};

pub fn parseGlobalFlags(args: []const []const u8) !GlobalFlags {
    var flags = GlobalFlags{};
    for (args[1..]) |arg| {
        if (std.mem.eql(u8, arg, "--production")) {
            flags.production = true;
        } else if (std.mem.eql(u8, arg, "--dry-run") or std.mem.eql(u8, arg, "-n")) {
            flags.dry_run = true;
        } else if (std.mem.eql(u8, arg, "--json")) {
            flags.json = true;
        } else if (std.mem.eql(u8, arg, "--expert")) {
            flags.expert = true;
        }
    }
    return flags;
}

pub fn parseCommand(cmd: []const u8) Command {
    if (std.mem.eql(u8, cmd, "alarm")) return .alarm;
    if (std.mem.eql(u8, cmd, "group")) return .group;
    if (std.mem.eql(u8, cmd, "vault")) return .vault;
    if (std.mem.eql(u8, cmd, "status") or std.mem.eql(u8, cmd, "s")) return .status;
    if (std.mem.eql(u8, cmd, "help") or std.mem.eql(u8, cmd, "h")) return .help;
    if (std.mem.eql(u8, cmd, "exit")) return .exit;
    return .unknown;
}

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
