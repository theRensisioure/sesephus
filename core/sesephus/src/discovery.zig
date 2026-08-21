const std = @import("std");

pub const HostHit = struct {
    ip: []const u8,
    port: u16,
};

pub fn scanSubnet(
    allocator: std.mem.Allocator,
    io: std.Io,
    prefix: []const u8,
    port: u16,
    hits: *std.ArrayList(HostHit),
) !void {
    var ip_buf: [32]u8 = undefined;
    var host: u8 = 1;
    while (host < 255) : (host += 1) {
        const ip = std.fmt.bufPrint(&ip_buf, "{s}.{d}", .{ prefix, host }) catch continue;
        if (try probeHost(io, ip, port)) {
            const owned = try allocator.dupe(u8, ip);
            try hits.append(allocator, .{ .ip = owned, .port = port });
        }
    }
}

fn probeHost(io: std.Io, ip: []const u8, port: u16) !bool {
    const address = std.Io.net.IpAddress.parseIp4(ip, port) catch return false;
    const stream = address.connect(io, .{ .mode = .stream }) catch return false;
    stream.close(io);
    return true;
}

pub fn defaultPrefixes(allocator: std.mem.Allocator) ![][]const u8 {
    const defaults = [_][]const u8{ "192.168.1", "192.168.0", "10.0.0" };
    var list: std.ArrayList([]const u8) = .empty;
    errdefer {
        for (list.items) |p| allocator.free(p);
        list.deinit(allocator);
    }
    for (defaults) |d| {
        try list.append(allocator, try allocator.dupe(u8, d));
    }
    return list.toOwnedSlice(allocator);
}

pub fn discoverHosts(allocator: std.mem.Allocator, io: std.Io, port: u16) ![]HostHit {
    const prefixes = try defaultPrefixes(allocator);
    defer {
        for (prefixes) |p| allocator.free(p);
        allocator.free(prefixes);
    }

    var hits: std.ArrayList(HostHit) = .empty;
    errdefer {
        for (hits.items) |h| allocator.free(h.ip);
        hits.deinit(allocator);
    }

    for (prefixes) |prefix| {
        try scanSubnet(allocator, io, prefix, port, &hits);
    }
    return hits.toOwnedSlice(allocator);
}

pub fn freeHits(allocator: std.mem.Allocator, hits: []HostHit) void {
    for (hits) |h| allocator.free(h.ip);
    allocator.free(hits);
}

pub fn selectHost(allocator: std.mem.Allocator, io: std.Io, hits: []const HostHit) !?[]const u8 {
    if (hits.len == 0) return null;
    if (hits.len == 1) return try allocator.dupe(u8, hits[0].ip);

    const stdout = std.Io.File.stdout();
    for (hits, 0..) |h, i| {
        var line_buf: [128]u8 = undefined;
        const line = std.fmt.bufPrint(&line_buf, "  [{d}] {s}:{d}\n", .{ i + 1, h.ip, h.port }) catch continue;
        try stdout.writeStreamingAll(io, line);
    }
    try stdout.writeStreamingAll(io, "Select host [1-N]: ");

    const stdin = std.Io.File.stdin();
    var buf: [32]u8 = undefined;
    var reader = stdin.reader(io, &buf);
    const line = (try reader.interface.takeDelimiter('\n')) orelse return null;
    const trimmed = std.mem.trim(u8, line, "\r\n ");
    const choice = std.fmt.parseInt(usize, trimmed, 10) catch return null;
    if (choice == 0 or choice > hits.len) return null;
    return try allocator.dupe(u8, hits[choice - 1].ip);
}

pub fn resolveHostForClient(allocator: std.mem.Allocator, io: std.Io, explicit_host: ?[]const u8, port: u16) ![]const u8 {
    if (explicit_host) |h| {
        if (h.len > 0 and !std.mem.eql(u8, h, "auto")) {
            return try allocator.dupe(u8, h);
        }
    }

    std.debug.print("[Discovery] Scanning LAN for Sesephus hosts on port {d}...\n", .{port});
    const hits = try discoverHosts(allocator, io, port);
    defer freeHits(allocator, hits);

    if (try selectHost(allocator, io, hits)) |picked| {
        return picked;
    }

    std.debug.print("[Discovery] No hosts found. Falling back to 127.0.0.1\n", .{});
    return try allocator.dupe(u8, "127.0.0.1");
}