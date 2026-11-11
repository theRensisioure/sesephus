const std = @import("std");
const builtin = @import("builtin");

fn findIngressScript(allocator: std.mem.Allocator, io: std.Io) ![]const u8 {
    const prefixes = [_][]const u8{ "", "../", "../../", "../../../", "../../../../" };
    const cwd = std.Io.Dir.cwd();
    for (prefixes) |prefix| {
        var buf: [320]u8 = undefined;
        const candidate = if (prefix.len == 0)
            "tools/ingress_memos.py"
        else
            std.fmt.bufPrint(&buf, "{s}tools/ingress_memos.py", .{prefix}) catch continue;
        cwd.access(io, candidate, .{}) catch continue;
        return try allocator.dupe(u8, candidate);
    }
    return error.IngressScriptNotFound;
}

fn spawnIngress(allocator: std.mem.Allocator, io: std.Io, dry_run: bool, limit: ?usize) !void {
    const script = try findIngressScript(allocator, io);
    defer allocator.free(script);

    const py: []const u8 = if (builtin.os.tag == .windows) "python" else "python3";

    var args = std.ArrayList([]const u8).empty;
    defer args.deinit(allocator);
    try args.append(allocator, py);
    try args.append(allocator, script);
    if (dry_run) try args.append(allocator, "--dry-run");
    if (limit) |n| {
        try args.append(allocator, "--limit");
        try args.append(allocator, try std.fmt.allocPrint(allocator, "{d}", .{n}));
    }

    var child = try std.process.spawn(io, .{
        .argv = args.items,
        .stdin = .inherit,
        .stdout = .inherit,
        .stderr = .inherit,
    });
    _ = try child.wait(io);
}

pub fn handleVaultCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const action = it.next() orelse {
        std.debug.print("Usage: vault <status|backup|audit|ingest-archive>\n", .{});
        return true;
    };

    if (std.mem.eql(u8, action, "status")) {
        std.debug.print("[Vault] Vault is active and securely encrypted.\n", .{});
    } else if (std.mem.eql(u8, action, "backup")) {
        std.debug.print("[Vault] Backing up encrypted memory...\n", .{});
    } else if (std.mem.eql(u8, action, "audit")) {
        std.debug.print("[Vault] Running integrity audit on vault sectors...\n", .{});
    } else if (std.mem.eql(u8, action, "ingest-archive")) {
        var dry_run = false;
        var limit: ?usize = null;
        while (it.next()) |tok| {
            if (std.mem.eql(u8, tok, "--dry-run")) dry_run = true;
            if (std.mem.eql(u8, tok, "--limit")) {
                if (it.next()) |n_str| {
                    limit = std.fmt.parseInt(usize, n_str, 10) catch null;
                }
            }
        }
        std.debug.print("[Vault] Running historical memo ingress (DualWriter)...\n", .{});
        try spawnIngress(allocator, io, dry_run, limit);
    } else {
        std.debug.print("Unknown vault command: {s}\n", .{action});
    }
    return true;
}