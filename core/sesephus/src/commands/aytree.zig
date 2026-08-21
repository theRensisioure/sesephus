const std = @import("std");
const builtin = @import("builtin");

const launch_rel: []const u8 = "tools/aytree_launch.py";

fn findLaunchScript(allocator: std.mem.Allocator, io: std.Io) ![]const u8 {
    const prefixes = [_][]const u8{ "", "../", "../../", "../../../", "../../../../" };
    const cwd = std.Io.Dir.cwd();
    for (prefixes) |prefix| {
        var buf: [320]u8 = undefined;
        const candidate = if (prefix.len == 0)
            launch_rel
        else
            std.fmt.bufPrint(&buf, "{s}{s}", .{ prefix, launch_rel }) catch continue;
        cwd.access(io, candidate, .{}) catch continue;
        return try allocator.dupe(u8, candidate);
    }
    return error.AytreeScriptNotFound;
}

fn spawnLaunch(allocator: std.mem.Allocator, io: std.Io, action: []const u8) !void {
    const script = try findLaunchScript(allocator, io);
    defer allocator.free(script);

    const py: []const u8 = if (builtin.os.tag == .windows) "python" else "python3";

    var args = std.ArrayList([]const u8).empty;
    defer args.deinit(allocator);

    try args.append(allocator, py);
    try args.append(allocator, script);
    try args.append(allocator, action);

    std.debug.print("[AyTree] launching suite derivation map ({s})\n", .{action});

    var child = try std.process.spawn(io, .{
        .argv = args.items,
        .stdin = .inherit,
        .stdout = .inherit,
        .stderr = .inherit,
    });
    _ = try child.wait(io);
}

/// Suite module: aytree open|map|tree|serve|status|help
/// Spawns tools/aytree_launch.py — same pattern as lead qualify / vault ingest.
pub fn handleAytreeCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const action = it.next() orelse "open";

    if (std.mem.eql(u8, action, "help") or std.mem.eql(u8, action, "h")) {
        std.debug.print(
            \\AyTree — Sesefus Version Control / derivation-map module
            \\  aytree open|map   Open directory lineage map (/derivation)
            \\  aytree tree       Open in-repo tree + notes tool
            \\  aytree serve      Run AyTree server in foreground
            \\  aytree status     Probe local server
            \\  aytree help
            \\
            \\Resolves AyTree via AYTREE_ROOT, sesefus.config.json aytree_root,
            \\or sibling ../AyTree — no hardcoded suite project roster.
            \\
        , .{});
        return true;
    }

    const known = std.mem.eql(u8, action, "open") or
        std.mem.eql(u8, action, "map") or
        std.mem.eql(u8, action, "tree") or
        std.mem.eql(u8, action, "serve") or
        std.mem.eql(u8, action, "status");

    if (!known) {
        std.debug.print("Unknown aytree command: {s}. Try: aytree help\n", .{action});
        return true;
    }

    spawnLaunch(allocator, io, action) catch |err| {
        std.debug.print("[AyTree] launch failed: {} (is tools/aytree_launch.py present?)\n", .{err});
    };
    return true;
}
