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

    // Archive linkage (shared with T:/Archive/db/archive.db + dimensional.db)
    archive_seq: ?i64 = null,
    ingest_source: ?[]const u8 = null,
    sha256: ?[]const u8 = null,
    transcript_status: ?[]const u8 = null,
    archive_raw_path: ?[]const u8 = null,
    schema_version: ?[]const u8 = null,

    // Semantic Context and Inference Prioritization
    high_intent: ?bool = null,
    proven_demo: ?bool = null,
    behavioral_inference_rel: ?f32 = null,
    demographic: ?[]const u8 = null,
    marked_importance: ?bool = null,
    intent_density: ?f32 = null,
    semantic_cluster: ?[]const u8 = null,

    // Dialogue / prose capture (covenant spine). Text records share the same
    // encrypted frame format as audio entries; absent on pre-existing records
    // (reads use ignore_unknown_fields, so both directions stay compatible).
    entry_kind: ?[]const u8 = null, // "prose" for text records; null = audio
    text: ?[]const u8 = null,
    prompt: ?[]const u8 = null, // the question that elicited this entry
    session_id: ?[]const u8 = null,
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

pub fn replicateDatabase(src_path: []const u8, dest_path: []const u8, io: std.Io) !void {
    var src_file = try DbFile.open(src_path, io);
    defer src_file.close();
    try src_file.seekToEnd();
    const len = src_file.offset;
    try src_file.seekTo(0);

    // Create parent directories of dest_path if missing
    if (std.fs.path.dirname(dest_path)) |dir_path| {
        if (dir_path.len > 0) {
            std.Io.Dir.cwd().createDirPath(io, dir_path) catch {};
        }
    }

    var dest_file = try DbFile.create(dest_path, io);
    defer dest_file.close();

    var buf: [4096]u8 = undefined;
    var copied: u64 = 0;
    while (copied < len) {
        const to_read = @min(len - copied, buf.len);
        const read_bytes = try src_file.read(buf[0..to_read]);
        if (read_bytes == 0) break;
        try dest_file.writeAll(buf[0..read_bytes]);
        copied += read_bytes;
    }
}

pub fn auditDatabase(file_path: []const u8, key: [32]u8, io: std.Io) !void {
    var file = try DbFile.open(file_path, io);
    defer file.close();

    var magic: [8]u8 = undefined;
    try file.readNoEof(&magic);
    if (!std.mem.eql(u8, &magic, MAGIC)) {
        return error.NotADatabaseFile;
    }

    // Seek past Header validation block
    try file.seekTo(68);

    var nonce: [12]u8 = undefined;
    var tag: [16]u8 = undefined;
    var len_buf: [4]u8 = undefined;
    var record_index: usize = 0;

    std.debug.print("[Audit] Starting vault integrity scan...\n", .{});

    while (true) {
        const offset = file.offset;
        const bytes_read = file.read(&nonce) catch |err| {
            std.debug.print("[Audit] Error reading nonce at offset {}: {}\n", .{offset, err});
            return err;
        };
        if (bytes_read == 0) break;
        if (bytes_read < 12) {
            std.debug.print("[Audit] Corrupt record header at offset {}\n", .{offset});
            return error.CorruptRecordHeader;
        }

        try file.readNoEof(&tag);
        try file.readNoEof(&len_buf);
        const len = std.mem.readInt(u32, &len_buf, .big);

        const ciphertext = try std.heap.page_allocator.alloc(u8, len);
        defer std.heap.page_allocator.free(ciphertext);
        try file.readNoEof(ciphertext);

        // Decrypt to verify AEAD tag
        _ = crypto.decrypt(std.heap.page_allocator, ciphertext, key, nonce, tag) catch |err| {
            std.debug.print("[Audit] AEAD Tag Verification FAILED for record {} at offset {}: {}\n", .{record_index, offset, err});
            return err;
        };

        record_index += 1;
    }

    std.debug.print("[Audit] Cryptographic scan completed. Verified {} records. 0 errors detected.\n", .{record_index});
}

const SortContext = struct {
    demographic_target: ?[]const u8 = null,
};

pub fn profileDatabase(file_path: []const u8, key: [32]u8, allocator: std.mem.Allocator, io: std.Io) !void {
    var file = try DbFile.open(file_path, io);
    defer file.close();
    try file.seekToEnd();
    const file_size = file.offset;

    std.debug.print("\n=== Vault Profile ===\n", .{});
    std.debug.print("Vault Path: {s}\n", .{file_path});
    std.debug.print("Disk Size:  {} bytes\n", .{file_size});

    // Read all records to compute statistics
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try readAllRecords(file_path, key, arena.allocator(), io);
    std.debug.print("Records:    {}\n", .{records.len});

    // Compute Shannon Entropy on the file payload to verify ciphertext quality
    try file.seekTo(68);
    var byte_counts = std.mem.zeroes([256]f64);
    var total_bytes: f64 = 0;
    var read_buf: [1024]u8 = undefined;
    while (true) {
        const n = try file.read(&read_buf);
        if (n == 0) break;
        for (read_buf[0..n]) |b| {
            byte_counts[b] += 1.0;
        }
        total_bytes += @floatFromInt(n);
    }

    var entropy: f64 = 0.0;
    if (total_bytes > 0) {
        for (byte_counts) |count| {
            if (count > 0.0) {
                const p = count / total_bytes;
                entropy -= p * (std.math.log2(p));
            }
        }
    }
    std.debug.print("Entropy:    {d:.4} (Ideal: ~8.0000 for pure random/ciphertext)\n", .{entropy});

    // Print client statistics
    std.debug.print("\n--- Records by Client ID ---\n", .{});
    const ClientStat = struct {
        client_id: []const u8,
        count: usize,
    };
    var client_stats = std.ArrayList(ClientStat).empty;
    defer client_stats.deinit(allocator);

    for (records) |r| {
        var found = false;
        for (client_stats.items) |*stat| {
            if (std.mem.eql(u8, stat.client_id, r.client_id)) {
                stat.count += 1;
                found = true;
                break;
            }
        }
        if (!found) {
            try client_stats.append(allocator, .{ .client_id = r.client_id, .count = 1 });
        }
    }

    for (client_stats.items) |stat| {
        std.debug.print("  - Client '{s}': {} entries\n", .{stat.client_id, stat.count});
    }

    // Prioritized Context Mapping
    std.debug.print("\n--- Prioritized Vault Context Layout ---\n", .{});

    var priority_list = std.ArrayList(JournalEntry).empty;
    defer priority_list.deinit(allocator);
    var remainder_list = std.ArrayList(JournalEntry).empty;
    defer remainder_list.deinit(allocator);

    for (records) |r| {
        const is_priority = (r.marked_importance orelse false) or
                            (r.high_intent orelse false) or
                            (r.proven_demo orelse false) or
                            ((r.behavioral_inference_rel orelse 0.0) > 0.7) or
                            (r.demographic != null);
        if (is_priority) {
            try priority_list.append(allocator, r);
        } else {
            try remainder_list.append(allocator, r);
        }
    }

    const sortCtx = SortContext{ .demographic_target = "developer" };
    const sortFn = struct {
        fn lessThan(ctx: SortContext, lhs: JournalEntry, rhs: JournalEntry) bool {
            const l_imp = lhs.marked_importance orelse false;
            const r_imp = rhs.marked_importance orelse false;
            if (l_imp != r_imp) return l_imp;

            const l_int = lhs.high_intent orelse false;
            const r_int = rhs.high_intent orelse false;
            if (l_int != r_int) return l_int;

            const l_demo = lhs.proven_demo orelse false;
            const r_demo = rhs.proven_demo orelse false;
            if (l_demo != r_demo) return l_demo;

            const l_rel = lhs.behavioral_inference_rel orelse 0.0;
            const r_rel = rhs.behavioral_inference_rel orelse 0.0;
            if (l_rel != r_rel) return l_rel > r_rel;

            if (ctx.demographic_target) |t| {
                const l_match = if (lhs.demographic) |d| std.mem.eql(u8, d, t) else false;
                const r_match = if (rhs.demographic) |d| std.mem.eql(u8, d, t) else false;
                if (l_match != r_match) return l_match;
            }

            return lhs.timestamp < rhs.timestamp;
        }
    }.lessThan;
    std.mem.sort(JournalEntry, priority_list.items, sortCtx, sortFn);

    const ClusterGroup = struct {
        name: []const u8,
        entries: std.ArrayList(JournalEntry),
        avg_density: f32,
    };
    var clusters = std.ArrayList(*ClusterGroup).empty;
    defer {
        for (clusters.items) |c| {
            c.entries.deinit(allocator);
            allocator.destroy(c);
        }
        clusters.deinit(allocator);
    }

    for (remainder_list.items) |r| {
        const cluster_name = r.semantic_cluster orelse "unclustered";
        var found_c: ?*ClusterGroup = null;
        for (clusters.items) |c| {
            if (std.mem.eql(u8, c.name, cluster_name)) {
                found_c = c;
                break;
            }
        }
        if (found_c == null) {
            const new_c = try allocator.create(ClusterGroup);
            new_c.* = ClusterGroup{
                .name = cluster_name,
                .entries = std.ArrayList(JournalEntry).empty,
                .avg_density = 0.0,
            };
            try clusters.append(allocator, new_c);
            found_c = new_c;
        }
        try found_c.?.entries.append(allocator, r);
    }

    for (clusters.items) |c| {
        var sum: f32 = 0.0;
        for (c.entries.items) |e| {
            sum += e.intent_density orelse 0.0;
        }
        c.avg_density = if (c.entries.items.len > 0) sum / @as(f32, @floatFromInt(c.entries.items.len)) else 0.0;

        const densitySort = struct {
            fn lessThan(_: void, lhs: JournalEntry, rhs: JournalEntry) bool {
                return (lhs.intent_density orelse 0.0) > (rhs.intent_density orelse 0.0);
            }
        }.lessThan;
        std.mem.sort(JournalEntry, c.entries.items, {}, densitySort);
    }

    const clusterSort = struct {
        fn lessThan(_: void, lhs: *ClusterGroup, rhs: *ClusterGroup) bool {
            return lhs.avg_density > rhs.avg_density;
        }
    }.lessThan;
    std.mem.sort(*ClusterGroup, clusters.items, {}, clusterSort);

    std.debug.print("[Top Priority Context Shards]\n", .{});
    for (priority_list.items, 0..) |e, idx| {
        std.debug.print("  {:2}. Client: {s} | Time: {} | Importance: {} | HighIntent: {} | BehavioralRel: {d:.2} | Demo: {s}\n", .{
            idx + 1, e.client_id, e.timestamp, e.marked_importance orelse false, e.high_intent orelse false, e.behavioral_inference_rel orelse 0.0, e.demographic orelse "none",
        });
    }
    if (priority_list.items.len == 0) {
        std.debug.print("  None\n", .{});
    }

    std.debug.print("\n[Semantic Density Clustered Shards]\n", .{});
    for (clusters.items) |c| {
        std.debug.print("  Cluster '{s}' (Avg Intent Density: {d:.3}):\n", .{c.name, c.avg_density});
        for (c.entries.items) |e| {
            std.debug.print("    - Client: {s} | Density: {d:.2} | Path: {s}\n", .{
                e.client_id, e.intent_density orelse 0.0, e.local_path orelse "embedded",
            });
        }
    }
    if (clusters.items.len == 0) {
        std.debug.print("  None\n", .{});
    }
    std.debug.print("=====================\n\n", .{});
}

pub fn shuffleDatabase(src_path: []const u8, dest_path: []const u8, key: [32]u8, allocator: std.mem.Allocator, io: std.Io) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try readAllRecords(src_path, key, arena.allocator(), io);

    var list = try std.ArrayList(JournalEntry).initCapacity(allocator, records.len);
    defer list.deinit(allocator);
    for (records) |r| {
        try list.append(allocator, r);
    }

    if (list.items.len > 1) {
        var i: usize = list.items.len - 1;
        while (i > 0) : (i -= 1) {
            var rand_bytes: [8]u8 = undefined;
            crypto.getRandomBytes(&rand_bytes);
            const r_idx = @as(usize, @intCast(@mod(std.mem.readInt(u64, &rand_bytes, .little), i + 1)));
            const temp = list.items[i];
            list.items[i] = list.items[r_idx];
            list.items[r_idx] = temp;
        }
    }

    var src_file = try DbFile.open(src_path, io);
    defer src_file.close();
    try src_file.seekTo(8);
    var salt: [16]u8 = undefined;
    try src_file.readNoEof(&salt);

    var dest_file = try DbFile.create(dest_path, io);
    defer dest_file.close();

    var verify_nonce: [12]u8 = undefined;
    crypto.getRandomBytes(&verify_nonce);
    
    var verify_tag: [16]u8 = undefined;
    var verify_ciphertext: [16]u8 = undefined;
    ChaCha20Poly1305.encrypt(&verify_ciphertext, &verify_tag, VERIFY_TEXT, "", verify_nonce, key);
    
    try dest_file.writeAll(MAGIC);
    try dest_file.writeAll(&salt);
    try dest_file.writeAll(&verify_nonce);
    try dest_file.writeAll(&verify_tag);
    try dest_file.writeAll(&verify_ciphertext);

    for (list.items) |entry| {
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
        
        try dest_file.writeAll(&nonce);
        try dest_file.writeAll(&tag);
        try dest_file.writeAll(&len_buf);
        try dest_file.writeAll(ciphertext);
    }
}

pub fn refactorDatabase(src_path: []const u8, dest_path: []const u8, key: [32]u8, allocator: std.mem.Allocator, io: std.Io) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try readAllRecords(src_path, key, arena.allocator(), io);

    var src_file = try DbFile.open(src_path, io);
    defer src_file.close();
    try src_file.seekTo(8);
    var salt: [16]u8 = undefined;
    try src_file.readNoEof(&salt);

    var dest_file = try DbFile.create(dest_path, io);
    defer dest_file.close();

    var verify_nonce: [12]u8 = undefined;
    crypto.getRandomBytes(&verify_nonce);
    
    var verify_tag: [16]u8 = undefined;
    var verify_ciphertext: [16]u8 = undefined;
    ChaCha20Poly1305.encrypt(&verify_ciphertext, &verify_tag, VERIFY_TEXT, "", verify_nonce, key);
    
    try dest_file.writeAll(MAGIC);
    try dest_file.writeAll(&salt);
    try dest_file.writeAll(&verify_nonce);
    try dest_file.writeAll(&verify_tag);
    try dest_file.writeAll(&verify_ciphertext);

    for (records) |entry| {
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
        
        try dest_file.writeAll(&nonce);
        try dest_file.writeAll(&tag);
        try dest_file.writeAll(&len_buf);
        try dest_file.writeAll(ciphertext);
    }
}

pub fn distributeDatabase(src_path: []const u8, dest_prefix: []const u8, key: [32]u8, allocator: std.mem.Allocator, io: std.Io) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try readAllRecords(src_path, key, arena.allocator(), io);

    var src_file = try DbFile.open(src_path, io);
    defer src_file.close();
    try src_file.seekTo(8);
    var salt: [16]u8 = undefined;
    try src_file.readNoEof(&salt);

    var clients_list = std.ArrayList([]const u8).empty;
    defer clients_list.deinit(allocator);

    for (records) |r| {
        var found = false;
        for (clients_list.items) |c| {
            if (std.mem.eql(u8, c, r.client_id)) {
                found = true;
                break;
            }
        }
        if (!found) {
            try clients_list.append(allocator, r.client_id);
        }
    }

    for (clients_list.items) |cid| {
        const dest_path = try std.fmt.allocPrint(allocator, "{s}_{s}.db", .{dest_prefix, cid});
        defer allocator.free(dest_path);

        var dest_file = try DbFile.create(dest_path, io);
        defer dest_file.close();

        var verify_nonce: [12]u8 = undefined;
        crypto.getRandomBytes(&verify_nonce);
        
        var verify_tag: [16]u8 = undefined;
        var verify_ciphertext: [16]u8 = undefined;
        ChaCha20Poly1305.encrypt(&verify_ciphertext, &verify_tag, VERIFY_TEXT, "", verify_nonce, key);
        
        try dest_file.writeAll(MAGIC);
        try dest_file.writeAll(&salt);
        try dest_file.writeAll(&verify_nonce);
        try dest_file.writeAll(&verify_tag);
        try dest_file.writeAll(&verify_ciphertext);

        for (records) |entry| {
            if (std.mem.eql(u8, entry.client_id, cid)) {
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
                
                try dest_file.writeAll(&nonce);
                try dest_file.writeAll(&tag);
                try dest_file.writeAll(&len_buf);
                try dest_file.writeAll(ciphertext);
            }
        }
        std.debug.print("[Distribute] Created sharded database: {s}\n", .{dest_path});
    }
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
