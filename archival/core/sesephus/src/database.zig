const std = @import("std");
const crypto = @import("crypto.zig");
const ChaCha20Poly1305 = std.crypto.aead.chacha_poly.ChaCha20Poly1305;

pub const DbFile = struct {
    file: std.Io.File,
    io: std.Io,
    offset: u64,

    pub fn create(path: []const u8, io: std.Io) !DbFile {
        const f = if (std.fs.path.isAbsolute(path))
            try std.Io.Dir.createFileAbsolute(io, path, .{ .read = true })
        else blk: {
            const cwd = std.Io.Dir.cwd();
            break :blk try cwd.createFile(io, path, .{ .read = true });
        };
        return DbFile{
            .file = f,
            .io = io,
            .offset = 0,
        };
    }

    pub fn open(path: []const u8, io: std.Io) !DbFile {
        const f = if (std.fs.path.isAbsolute(path))
            try std.Io.Dir.openFileAbsolute(io, path, .{ .mode = .read_write })
        else blk: {
            const cwd = std.Io.Dir.cwd();
            break :blk try cwd.openFile(io, path, .{ .mode = .read_write });
        };
        return DbFile{
            .file = f,
            .io = io,
            .offset = 0,
        };
    }

    pub fn close(self: DbFile) void {
        self.file.close(self.io);
    }

    pub fn writeAll(self: *DbFile, data: []const u8) !void {
        try self.file.writePositionalAll(self.io, data, self.offset);
        self.offset += data.len;
    }

    pub fn read(self: *DbFile, data: []u8) !usize {
        const n = try self.file.readPositionalAll(self.io, data, self.offset);
        self.offset += n;
        return n;
    }

    pub fn readNoEof(self: *DbFile, buffer: []u8) !void {
        var total_read: usize = 0;
        while (total_read < buffer.len) {
            const read_bytes = try self.read(buffer[total_read..]);
            if (read_bytes == 0) return error.EndOfStream;
            total_read += read_bytes;
        }
    }

    pub fn seekToEnd(self: *DbFile) !void {
        const len = try self.file.length(self.io);
        self.offset = len;
    }

    pub fn seekTo(self: *DbFile, offset: i32) !void {
        self.offset = @intCast(offset);
    }
};

pub const JournalEntry = struct {
    client_id: []const u8,
    timestamp: i64,
    filename: []const u8,
    audio_data_base64: []const u8,
    local_path: ?[]const u8 = null,
};

const MAGIC = "SESEPHUS";
const VERIFY_TEXT = "VerifySesephusDB";

/// Initializes a new database file at `file_path` with a verification block encrypted by a derived key from `password`
pub fn initNewDatabase(file_path: []const u8, password: []const u8, io: std.Io) !void {
    var file = try DbFile.create(file_path, io);
    defer file.close();
    
    var salt: [16]u8 = undefined;
    crypto.getRandomBytes(&salt);
    
    var key: [32]u8 = undefined;
    try crypto.deriveKey(password, &salt, &key);
    
    var verify_nonce: [12]u8 = undefined;
    crypto.getRandomBytes(&verify_nonce);
    
    var verify_tag: [16]u8 = undefined;
    var verify_ciphertext: [16]u8 = undefined;
    ChaCha20Poly1305.encrypt(&verify_ciphertext, &verify_tag, VERIFY_TEXT, "", verify_nonce, key);
    
    try file.writeAll(MAGIC);
    try file.writeAll(&salt);
    try file.writeAll(&verify_nonce);
    try file.writeAll(&verify_tag);
    try file.writeAll(&verify_ciphertext);
}

/// Validates the password against the database file at `file_path` and returns the derived 32-byte key if successful
pub fn openDatabase(file_path: []const u8, password: []const u8, key_out: *[32]u8, io: std.Io) !void {
    var file = try DbFile.open(file_path, io);
    defer file.close();
    
    var magic: [8]u8 = undefined;
    try file.readNoEof(&magic);
    if (!std.mem.eql(u8, &magic, MAGIC)) {
        return error.NotADatabaseFile;
    }
    
    var salt: [16]u8 = undefined;
    try file.readNoEof(&salt);
    
    try crypto.deriveKey(password, &salt, key_out);
    
    var verify_nonce: [12]u8 = undefined;
    try file.readNoEof(&verify_nonce);
    
    var verify_tag: [16]u8 = undefined;
    try file.readNoEof(&verify_tag);
    
    var verify_ciphertext: [16]u8 = undefined;
    try file.readNoEof(&verify_ciphertext);
    
    var decrypted_verify: [16]u8 = undefined;
    ChaCha20Poly1305.decrypt(&decrypted_verify, &verify_ciphertext, verify_tag, "", verify_nonce, key_out.*) catch {
        return error.InvalidPassword;
    };
    
    if (!std.mem.eql(u8, &decrypted_verify, VERIFY_TEXT)) {
        return error.InvalidPassword;
    }
}

/// Appends a new encrypted JournalEntry to the database file
pub fn appendRecord(file_path: []const u8, key: [32]u8, entry: JournalEntry, allocator: std.mem.Allocator, io: std.Io) !void {
    var file = try DbFile.open(file_path, io);
    defer file.close();
    try file.seekToEnd();
    
    var json_str = std.ArrayList(u8).empty;
    defer json_str.deinit(allocator);
    
    var aw: std.Io.Writer.Allocating = .fromArrayList(allocator, &json_str);
    try std.json.Stringify.value(entry, .{}, &aw.writer);
    json_str = aw.toArrayList();
    
    var nonce: [12]u8 = undefined;
    crypto.getRandomBytes(&nonce);
    
    var tag: [16]u8 = undefined;
    const ciphertext = try crypto.encrypt(allocator, json_str.items, key, nonce, &tag);
    defer allocator.free(ciphertext);
    
    const len: u32 = @intCast(ciphertext.len);
    var len_buf: [4]u8 = undefined;
    std.mem.writeInt(u32, &len_buf, len, .big);
    
    try file.writeAll(&nonce);
    try file.writeAll(&tag);
    try file.writeAll(&len_buf);
    try file.writeAll(ciphertext);
}

/// Reads and decrypts all records from the database using an arena allocator
pub fn readAllRecords(file_path: []const u8, key: [32]u8, arena_allocator: std.mem.Allocator, io: std.Io) ![]JournalEntry {
    var file = try DbFile.open(file_path, io);
    defer file.close();
    
    // Seek past Header: Magic (8) + Salt (16) + Nonce (12) + Tag (16) + Ciphertext (16) = 68 bytes
    try file.seekTo(68);
    
    var list: std.ArrayList(JournalEntry) = .empty;
    errdefer list.deinit(arena_allocator);
    
    var nonce: [12]u8 = undefined;
    var tag: [16]u8 = undefined;
    var len_buf: [4]u8 = undefined;
    
    while (true) {
        const bytes_read = file.read(&nonce) catch break;
        if (bytes_read == 0) break;
        if (bytes_read < 12) return error.CorruptRecordHeader;
        
        try file.readNoEof(&tag);
        try file.readNoEof(&len_buf);
        const len = std.mem.readInt(u32, &len_buf, .big);
        
        const ciphertext = try arena_allocator.alloc(u8, len);
        try file.readNoEof(ciphertext);
        
        const plaintext = try crypto.decrypt(arena_allocator, ciphertext, key, nonce, tag);
        
        const parsed = try std.json.parseFromSlice(JournalEntry, arena_allocator, plaintext, .{ .ignore_unknown_fields = true });
        try list.append(arena_allocator, parsed.value);
    }
    
    return list.toOwnedSlice(arena_allocator);
}

test "database init, open, append, readAll integration" {
    const allocator = std.testing.allocator;
    const db_name = "test_sesephus.db";
    
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();
    
    // Ensure we delete any pre-existing test db
    std.Io.Dir.cwd().deleteFile(io, db_name) catch {};
    defer std.Io.Dir.cwd().deleteFile(io, db_name) catch {};
    
    const password = "super_test_pass";
    try initNewDatabase(db_name, password, io);
    
    var key: [32]u8 = undefined;
    try openDatabase(db_name, password, &key, io);
    
    const entry1 = JournalEntry{
        .client_id = "test-client-1",
        .timestamp = 123456789,
        .filename = "audio1.wav",
        .audio_data_base64 = "U2VzZXBodXM=", // "Sesephus" in base64
    };
    
    const entry2 = JournalEntry{
        .client_id = "test-client-2",
        .timestamp = 987654321,
        .filename = "audio2.wav",
        .audio_data_base64 = "Q2lyY2FkaWE=", // "Circadia" in base64
    };
    
    try appendRecord(db_name, key, entry1, allocator, io);
    try appendRecord(db_name, key, entry2, allocator, io);
    
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    
    const records = try readAllRecords(db_name, key, arena.allocator(), io);
    
    try std.testing.expectEqual(@as(usize, 2), records.len);
    try std.testing.expectEqualStrings(entry1.client_id, records[0].client_id);
    try std.testing.expectEqual(entry1.timestamp, records[0].timestamp);
    try std.testing.expectEqualStrings(entry1.filename, records[0].filename);
    try std.testing.expectEqualStrings(entry1.audio_data_base64, records[0].audio_data_base64);
    
    try std.testing.expectEqualStrings(entry2.client_id, records[1].client_id);
    try std.testing.expectEqual(entry2.timestamp, records[1].timestamp);
    try std.testing.expectEqualStrings(entry2.filename, records[1].filename);
    try std.testing.expectEqualStrings(entry2.audio_data_base64, records[1].audio_data_base64);
}
