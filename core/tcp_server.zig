// core/tcp_server.zig
// Minimal async TCP server that receives a header and raw WAV data,
// saves the file to the `recordings/` directory, and inserts a row
// into the SQLite database via `wav_db.zig`.

const std = @import("std");
const wavdb = @import("../core/wav_db.zig");

pub const Header = struct {
    client_id_len: u16,
    client_id: []const u8,
    start_time_ms: i64,
    wav_len: u64,
    tags_len: u16,
    tags: []const u8,
};

fn readHeader(stream: *std.net.Stream) !Header {
    var reader = stream.reader();
    const client_id_len = try reader.readInt(u16, .big);
    var client_id_buf = try std.heap.page_allocator.alloc(u8, client_id_len);
    defer std.heap.page_allocator.free(client_id_buf);
    try reader.readAll(client_id_buf);
    const start_time_ms = try reader.readInt(i64, .big);
    const wav_len = try reader.readInt(u64, .big);
    const tags_len = try reader.readInt(u16, .big);
    var tags_buf = try std.heap.page_allocator.alloc(u8, tags_len);
    defer std.heap.page_allocator.free(tags_buf);
    try reader.readAll(tags_buf);
    return Header{ .client_id_len = client_id_len, .client_id = client_id_buf, .start_time_ms = start_time_ms, .wav_len = wav_len, .tags_len = tags_len, .tags = tags_buf };
}

pub fn startServer(port: u16) !void {
    var server = try std.net.StreamServer.listen(.{ .address = .{ .ipv4 = .{ .address = 0, .port = port } }, .reuse_address = true });
    defer server.deinit();
    const db = try wavdb.initDatabase(&std.heap.page_allocator);
    defer _ = c.sqlite3_close(db);
    std.debug.print("Server listening on port {d}\n", .{port});
    while (true) {
        const connection = try server.accept();
        std.debug.print("Accepted connection\n", .{});
        // Handle each connection in a new async task (simplified sync for now)
        var stream = connection.stream;
        const hdr = try readHeader(&stream);
        // Prepare file path
        const recordings_dir = "recordings";
        try std.fs.cwd().makePath(recordings_dir);
        const filename = std.fmt.allocPrint(std.heap.page_allocator, "{s}_{d}.wav", .{ hdr.client_id, hdr.start_time_ms }) catch return error.OutOfMemory;
        defer std.heap.page_allocator.free(filename);
        const filepath = try std.fs.path.join(std.heap.page_allocator, &[_][]const u8{ recordings_dir, filename });
        defer std.heap.page_allocator.free(filepath);
        var file = try std.fs.cwd().createFile(filepath, .{ .read = true, .write = true });
        defer file.close();
        // Write raw WAV data directly
        var remaining = hdr.wav_len;
        var writer = file.writer();
        while (remaining > 0) {
            var buf: [4096]u8 = undefined;
            const to_read = @intCast(usize, if (remaining > buf.len) buf.len else remaining);
            const read = try stream.reader().readAll(buf[0..to_read]);
            try writer.writeAll(buf[0..read]);
            remaining -= @intCast(u64, read);
        }
        // Insert DB record
        const rec = wavdb.Recording{ .id = 0, .client_id = hdr.client_id, .start_time = hdr.start_time_ms, .duration_ms = 0, .tags = hdr.tags, .wav_path = filepath };
        try wavdb.insertRecording(db, rec);
        std.debug.print("Stored recording {s}\n", .{filepath});
    }
}
