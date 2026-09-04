const std = @import("std");

/// External Desktop Clippers — sole supported Voice capture owner.
/// This handler is a finishable STUB: it does not record, import, vendor,
/// submodule, or launch Clippers. Finish path = consume `takes.jsonl` schema=1.
pub const clippers_root = "C:\\dev\\journal-clippers\\audio-journal-system";
pub const tape_name = "takes.jsonl";
pub const tape_schema: i64 = 1;

pub const TapeRow = struct {
    id: []const u8,
    text: []const u8,
    schema: i64,
};

const ParsedTape = struct {
    id: []const u8,
    text: []const u8,
    schema: i64,
    title: []const u8 = "",
    source: []const u8 = "clip",
};

fn contains(haystack: []const u8, needle: []const u8) bool {
    if (needle.len == 0 or needle.len > haystack.len) return false;
    var i: usize = 0;
    while (i + needle.len <= haystack.len) : (i += 1) {
        if (std.mem.eql(u8, haystack[i .. i + needle.len], needle)) return true;
    }
    return false;
}

fn openTape(io: std.Io, path: []const u8) !std.Io.File {
    if (std.fs.path.isAbsolute(path)) {
        return std.Io.Dir.openFileAbsolute(io, path, .{ .mode = .read_only });
    }
    return std.Io.Dir.cwd().openFile(io, path, .{ .mode = .read_only });
}

/// Read the last schema=1 tape row with non-empty text.
/// Wav is not consulted — Clippers already destroyed it. No microphone.
pub fn consumeTapeFinish(allocator: std.mem.Allocator, io: std.Io, tape_path: []const u8) !TapeRow {
    const file = openTape(io, tape_path) catch return error.TapeMissing;
    defer file.close(io);

    var read_buf: [4096]u8 = undefined;
    var reader = file.reader(io, &read_buf);
    const data = try reader.interface.allocRemaining(allocator, .unlimited);
    defer allocator.free(data);

    var last: ?ParsedTape = null;
    var parsed_hold: ?std.json.Parsed(ParsedTape) = null;

    var lines = std.mem.splitScalar(u8, data, '\n');
    while (lines.next()) |raw| {
        const line = std.mem.trim(u8, raw, " \r\t");
        if (line.len == 0) continue;
        const parsed = std.json.parseFromSlice(ParsedTape, allocator, line, .{
            .ignore_unknown_fields = true,
        }) catch continue;
        if (parsed.value.schema != tape_schema or parsed.value.text.len == 0) {
            parsed.deinit();
            continue;
        }
        if (parsed_hold) |old| old.deinit();
        parsed_hold = parsed;
        last = parsed.value;
    }

    const row = last orelse {
        if (parsed_hold) |old| old.deinit();
        return error.NoTapeRow;
    };
    const id = try allocator.dupe(u8, row.id);
    errdefer allocator.free(id);
    const text = try allocator.dupe(u8, row.text);
    errdefer allocator.free(text);
    if (parsed_hold) |old| old.deinit();
    return TapeRow{ .id = id, .text = text, .schema = tape_schema };
}

pub fn freeTapeRow(allocator: std.mem.Allocator, row: TapeRow) void {
    allocator.free(row.id);
    allocator.free(row.text);
}

fn writeStubHeader(aw: *std.Io.Writer, action: []const u8) !void {
    try aw.print("[Journal] STUB — {s} is not a recorder and did not capture audio.\n", .{action});
    try aw.print("Capture owner: {s}\n", .{clippers_root});
    try aw.print("Finish path: consume Clippers {s} (schema={d}). Keep text; wav already destroyed. No microphone.\n", .{ tape_name, tape_schema });
}

/// Shipped journal reply. Tests call this; the REPL prints it.
pub fn renderJournal(
    allocator: std.mem.Allocator,
    io: std.Io,
    action: []const u8,
    tape_path: ?[]const u8,
) ![]u8 {
    var body = std.ArrayList(u8).empty;
    errdefer body.deinit(allocator);
    var allocating: std.Io.Writer.Allocating = .fromArrayList(allocator, &body);
    const aw = &allocating.writer;

    if (std.mem.eql(u8, action, "record") or std.mem.eql(u8, action, "review") or std.mem.eql(u8, action, "prompt")) {
        try writeStubHeader(aw, action);
        if (std.mem.eql(u8, action, "record")) {
            try aw.print("Do not use this command as a journal loop. Record in Clippers; this stub will not start a session.\n", .{});
        } else if (std.mem.eql(u8, action, "prompt")) {
            try aw.print("A later finish may prompt from tape text. It will not run Whisper or invent a stoic prompt here.\n", .{});
        }
        if (tape_path) |path| {
            if (consumeTapeFinish(allocator, io, path)) |row| {
                defer freeTapeRow(allocator, row);
                try aw.print("STUB finish-path consumed tape id={s} schema={d} (no wav, no microphone):\n{s}\n", .{ row.id, row.schema, row.text });
            } else |err| {
                try aw.print("STUB finish-path: tape not consumed ({s}) at {s}. Still not a capture.\n", .{ @errorName(err), path });
            }
        } else if (std.mem.eql(u8, action, "review")) {
            try aw.print("Pass --tape <takes.jsonl> to exercise the finish-path reader. Default owner tree is Clippers, not this repo.\n", .{});
        }
    } else {
        try aw.print("Unknown journal command: {s}\n", .{action});
        try aw.print("Usage: journal <record|review|prompt> [--tape <takes.jsonl>]\n", .{});
    }

    body = allocating.toArrayList();
    return try body.toOwnedSlice(allocator);
}

pub fn handleJournalCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const action = it.next() orelse {
        std.debug.print("Usage: journal <record|review|prompt> [--tape <takes.jsonl>]\n", .{});
        std.debug.print("[Journal] STUB. Capture owner: {s}\n", .{clippers_root});
        return true;
    };

    var tape_path: ?[]const u8 = null;
    while (it.next()) |tok| {
        if (std.mem.eql(u8, tok, "--tape")) {
            tape_path = it.next();
        }
    }

    const msg = try renderJournal(allocator, io, action, tape_path);
    defer allocator.free(msg);
    std.debug.print("{s}", .{msg});
    return true;
}

fn writeFixture(io: std.Io, path: []const u8, body: []const u8) !void {
    const cwd = std.Io.Dir.cwd();
    const file = try cwd.createFile(io, path, .{});
    defer file.close(io);
    try file.writeStreamingAll(io, body);
}

test "journal record is STUB, names Clippers, refuses capture success" {
    const allocator = std.testing.allocator;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const msg = try renderJournal(allocator, io, "record", null);
    defer allocator.free(msg);

    try std.testing.expect(contains(msg, "STUB"));
    try std.testing.expect(contains(msg, clippers_root));
    try std.testing.expect(contains(msg, "takes.jsonl"));
    try std.testing.expect(contains(msg, "schema=1"));
    try std.testing.expect(contains(msg, "No microphone"));
    try std.testing.expect(!contains(msg, "Starting audio" ++ " journaling session"));
    try std.testing.expect(!contains(msg, "use voice.bat" ++ " (the real journal loop)"));
}

test "journal review/prompt stay STUB and do not fake work" {
    const allocator = std.testing.allocator;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const review = try renderJournal(allocator, io, "review", null);
    defer allocator.free(review);
    const prompt = try renderJournal(allocator, io, "prompt", null);
    defer allocator.free(prompt);

    try std.testing.expect(contains(review, "STUB"));
    try std.testing.expect(contains(review, clippers_root));
    try std.testing.expect(!contains(review, "Reviewing recent" ++ " audio entries"));
    try std.testing.expect(contains(prompt, "STUB"));
    try std.testing.expect(!contains(prompt, "Generating a stoic" ++ " reflection prompt"));
}

test "finish-path reads fixture tape schema=1 text and does not need wav" {
    const allocator = std.testing.allocator;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const fixture_text = "spoken take kept after shred";
    const tape_path = "test_clippers_takes.jsonl";
    const row_json =
        \\{"id":"1","date":"2026-09-04","time":"12:00:00","kind":"dump","score":0.0,"text":"spoken take kept after shred","structured":"spoken take kept after shred","title":"","source":"clip","schema":1,"extra":{}}
        \\
    ;
    try writeFixture(io, tape_path, row_json);
    defer std.Io.Dir.cwd().deleteFile(io, tape_path) catch {};

    const row = try consumeTapeFinish(allocator, io, tape_path);
    defer freeTapeRow(allocator, row);
    try std.testing.expectEqual(tape_schema, row.schema);
    try std.testing.expectEqualStrings(fixture_text, row.text);

    const msg = try renderJournal(allocator, io, "review", tape_path);
    defer allocator.free(msg);
    try std.testing.expect(contains(msg, "STUB"));
    try std.testing.expect(contains(msg, fixture_text));
    try std.testing.expect(contains(msg, "no microphone") or contains(msg, "No microphone"));
    try std.testing.expect(!contains(msg, "Starting audio" ++ " journaling session"));
}

test "handleJournalCommand record entry point stays stub" {
    const allocator = std.testing.allocator;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    var it = std.mem.tokenizeAny(u8, "record", " ");
    try std.testing.expect(try handleJournalCommand(&it, allocator, threaded.io()));
}
