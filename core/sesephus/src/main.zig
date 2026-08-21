const std = @import("std");

const host = @import("host.zig");
const client = @import("client.zig");
const runtime_config = @import("runtime_config.zig");
const discovery = @import("discovery.zig");

fn restartWithRole(init: std.process.Init, io: std.Io, role: runtime_config.Role) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    const exe = if (args.len > 0) args[0] else "sesefus.exe";
    const role_str: []const u8 = if (role == .host) "host" else "client";
    const argv = [_][]const u8{ exe, "--role", role_str };
    var child = try std.process.spawn(io, .{ .argv = &argv });
    _ = try child.wait(io);
    std.process.exit(0);
}

fn parseRoleArg(args: []const []const u8) ?runtime_config.Role {
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        if (std.mem.eql(u8, args[i], "--role") and i + 1 < args.len) {
            if (std.mem.eql(u8, args[i + 1], "host")) return .host;
            if (std.mem.eql(u8, args[i + 1], "client")) return .client;
        }
    }
    return null;
}

fn wantsFlag(args: []const []const u8, flag: []const u8) bool {
    for (args[1..]) |arg| {
        if (std.mem.eql(u8, arg, flag)) return true;
    }
    return false;
}

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const args = try init.minimal.args.toSlice(init.arena.allocator());

    if (wantsFlag(args, "--reset-role")) {
        runtime_config.deleteConfig(allocator, io);
        std.debug.print("Runtime role config cleared. Restart to re-prompt.\n", .{});
        return;
    }

    var cfg = runtime_config.load(allocator, io) catch null;
    defer if (cfg) |*c| c.deinit(allocator);

    if (cfg == null) {
        if (parseRoleArg(args)) |r| {
            // Explicit --role: honor it non-interactively without persisting,
            // so first runs never block on the prompt or write runtime.json.
            cfg = runtime_config.Config{ .role = r };
            std.debug.print("No runtime config found; running as '{s}' for this session (not saved).\n", .{if (r == .host) "host" else "client"});
        } else {
            const fresh = try runtime_config.promptAndSave(allocator, io);
            std.debug.print("Saved role '{s}'. Restarting...\n", .{if (fresh.role == .host) "host" else "client"});
            try restartWithRole(init, io, fresh.role);
        }
    }

    var active = cfg.?;
    if (parseRoleArg(args)) |r| active.role = r;

    if (active.role == .host) {
        host.embed_local_client = active.embed_local_client or !wantsFlag(args, "--production");
        try host.runHost(init);
        return;
    }

    const rescan = wantsFlag(args, "--rescan");
    var explicit_host: ?[]const u8 = null;
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        if (std.mem.eql(u8, args[i], "--host") and i + 1 < args.len) {
            explicit_host = args[i + 1];
            i += 1;
        }
    }

    var host_ip: []const u8 = undefined;
    var host_ip_owned: ?[]const u8 = null;
    defer if (host_ip_owned) |h| allocator.free(h);

    if (rescan or explicit_host == null or std.mem.eql(u8, explicit_host.?, "auto")) {
        host_ip_owned = try discovery.resolveHostForClient(allocator, io, explicit_host, active.last_port);
        host_ip = host_ip_owned.?;
    } else {
        host_ip = explicit_host.?;
    }

    try client.runClient(init, host_ip, active.last_port);
}