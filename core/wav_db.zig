// core/wav_db.zig
// Simple SQLite wrapper for storing WAV metadata and binary data.
// Uses the built-in sqlite3 C library via @cImport.

const std = @import("std");
const c = @cImport({
    @cInclude("sqlite3.h");
});

pub const Recording = struct {
    id: i64,
    client_id: []const u8,
    start_time: i64, // Unix epoch ms
    duration_ms: i64,
    tags: []const u8,
    wav_path: []const u8,
};

pub fn initDatabase(allocator: *std.mem.Allocator) !*c.sqlite3 {
    var db: ?*c.sqlite3 = null;
    const rc = c.sqlite3_open("V:\\sesephus_vault.db", &db);
    if (rc != c.SQLITE_OK) return error.DatabaseOpenFailed;
    const db_ptr = db.?;
    // Create table if not exists
    const create_sql =
        "CREATE TABLE IF NOT EXISTS recordings (" ++
        "id INTEGER PRIMARY KEY AUTOINCREMENT," ++
        "client_id TEXT NOT NULL," ++
        "start_time INTEGER NOT NULL," ++
        "duration_ms INTEGER NOT NULL," ++
        "tags TEXT," ++
        "wav_path TEXT NOT NULL" ++
        ");";
    var stmt: ?*c.sqlite3_stmt = null;
    defer if (stmt) |s| c.sqlite3_finalize(s);
    if (c.sqlite3_prepare_v2(db_ptr, create_sql, -1, &stmt, null) != c.SQLITE_OK) return error.SqlError;
    if (c.sqlite3_step(stmt) != c.SQLITE_DONE) return error.SqlError;
    if (c.sqlite3_finalize(stmt) != c.SQLITE_OK) return error.SqlError;
    return db_ptr;
}

pub fn insertRecording(db: *c.sqlite3, rec: Recording) !void {
    const insert_sql = "INSERT INTO recordings (client_id, start_time, duration_ms, tags, wav_path) VALUES (?, ?, ?, ?, ?);";
    var stmt: ?*c.sqlite3_stmt = null;
    defer if (stmt) |s| c.sqlite3_finalize(s);
    if (c.sqlite3_prepare_v2(db, insert_sql, -1, &stmt, null) != c.SQLITE_OK) return error.SqlError;
    const s = stmt.?;
    _ = c.sqlite3_bind_text(s, 1, rec.client_id.ptr, @intCast(c.int, rec.client_id.len), c.SQLITE_TRANSIENT);
    _ = c.sqlite3_bind_int64(s, 2, rec.start_time);
    _ = c.sqlite3_bind_int64(s, 3, rec.duration_ms);
    _ = c.sqlite3_bind_text(s, 4, rec.tags.ptr, @intCast(c.int, rec.tags.len), c.SQLITE_TRANSIENT);
    _ = c.sqlite3_bind_text(s, 5, rec.wav_path.ptr, @intCast(c.int, rec.wav_path.len), c.SQLITE_TRANSIENT);
    if (c.sqlite3_step(s) != c.SQLITE_DONE) return error.SqlError;
}

// Additional query helpers can be added as needed.
