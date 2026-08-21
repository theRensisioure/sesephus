//! Length-prefixed JSON message protocol shared by the alarms host and capture clients.
//! Extracted from core/sesephus/src/common.zig (strict-main lineage).

const std = @import("std");
const builtin = @import("builtin");

// Windows API to get precise file time
pub extern "kernel32" fn GetSystemTimeAsFileTime(lpSystemTimeAsFileTime: *u64) callconv(.winapi) void;
pub extern "kernel32" fn Sleep(dwMilliseconds: u32) callconv(.winapi) void;

/// Sleep the current thread for the specified number of milliseconds
pub fn sleepMs(ms: u32) void {
    if (builtin.os.tag == .windows) {
        Sleep(ms);
    } else {
        const timespec = std.posix.timespec{
            .sec = @intCast(ms / 1000),
            .nsec = @intCast((ms % 1000) * 1_000_000),
        };
        _ = std.posix.system.nanosleep(&timespec, null);
    }
}

/// Get system millisecond timestamp, adjusted to Unix epoch (1970-01-01)
pub fn getMilliTimestamp() i64 {
    if (builtin.os.tag == .windows) {
        var ft: u64 = 0;
        GetSystemTimeAsFileTime(&ft);
        const win_epoch_adjust: u64 = 11644473600000;
        const ms_since_1601 = ft / 10000;
        return @as(i64, @intCast(ms_since_1601 - win_epoch_adjust));
    } else {
        var ts: std.posix.timespec = undefined;
        _ = std.posix.system.clock_gettime(std.posix.CLOCK.REALTIME, &ts);
        const ns = @as(u128, @intCast(ts.sec)) * std.time.ns_per_s + @as(u128, @intCast(ts.nsec));
        return @as(i64, @intCast(@divTrunc(ns, std.time.ns_per_ms)));
    }
}

pub const Message = struct {
    type: []const u8,
    // Optional payload fields
    client_id: ?[]const u8 = null,
    friendly_name: ?[]const u8 = null,
    server_time: ?i64 = null,
    client_offset: ?i64 = null,
    alarm_id: ?[]const u8 = null,
    action: ?[]const u8 = null,
    duration: ?f32 = null,
    filename: ?[]const u8 = null,
    timestamp: ?i64 = null,
    audio_data_base64: ?[]const u8 = null,
    success: ?bool = null,
    message: ?[]const u8 = null,
    local_path: ?[]const u8 = null,
};

pub const ParsedMessage = struct {
    raw_buffer: []u8,
    parsed: std.json.Parsed(Message),
    allocator: std.mem.Allocator,

    pub fn deinit(self: ParsedMessage) void {
        self.parsed.deinit();
        self.allocator.free(self.raw_buffer);
    }
};

pub fn writeMessage(stream: std.Io.net.Stream, msg: Message, allocator: std.mem.Allocator, io: std.Io) !void {
    var string = std.ArrayList(u8).empty;
    defer string.deinit(allocator);

    var aw: std.Io.Writer.Allocating = .fromArrayList(allocator, &string);
    try std.json.Stringify.value(msg, .{}, &aw.writer);
    string = aw.toArrayList();

    const len: u32 = @intCast(string.items.len);
    var len_buf: [4]u8 = undefined;
    std.mem.writeInt(u32, &len_buf, len, .big);

    var write_buf: [1024]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    try stream_writer.interface.writeAll(&len_buf);
    try stream_writer.interface.writeAll(string.items);
    try stream_writer.interface.flush();
}

pub fn readMessage(stream: std.Io.net.Stream, allocator: std.mem.Allocator, io: std.Io) !ParsedMessage {
    var len_buf: [4]u8 = undefined;
    var read_buf: [1024]u8 = undefined;
    var stream_reader = stream.reader(io, &read_buf);

    try stream_reader.interface.readSliceAll(&len_buf);
    const len = std.mem.readInt(u32, &len_buf, .big);

    const raw_buffer = try allocator.alloc(u8, len);
    errdefer allocator.free(raw_buffer);
    try stream_reader.interface.readSliceAll(raw_buffer);

    const parsed = try std.json.parseFromSlice(Message, allocator, raw_buffer, .{ .ignore_unknown_fields = true });
    errdefer parsed.deinit();

    return ParsedMessage{
        .raw_buffer = raw_buffer,
        .parsed = parsed,
        .allocator = allocator,
    };
}
