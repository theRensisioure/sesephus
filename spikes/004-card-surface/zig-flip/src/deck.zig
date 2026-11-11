//! Spike 004b: the deck rules of the two-face card as plain Zig.
//!
//! - Flip is the only way between faces.
//! - Face 2 (the ledger) is read-only.
//! - Left/right decide on face 1 only; they are inert on face 2.
//! - Every answer is one appended line, never rewritten.
//! - A card id already in the ledger is dropped from the deck.
//! - A torn or malformed ledger line is skipped and counted, never fatal.

const std = @import("std");
const Allocator = std.mem.Allocator;

pub const Face = enum { decision, ledger };
pub const Answer = enum { no, yes };
pub const Arrow = enum { left, right };

/// A ledger line longer than this is skipped without being parsed.
pub const max_line_bytes: usize = 1 << 20;

/// Strings are borrowed: they must outlive the Deck. `slug` is written as the
/// row's "card" key and `disk` as its "disk" key, as the real Clivor row does.
pub const Card = struct {
    id: []const u8,
    question: []const u8,
    disk: []const u8 = "",
    slug: []const u8 = "clivor",
};

pub const Press = union(enum) {
    /// Arrow pressed on face 2: nothing changed.
    inert,
    /// No cards left to answer: nothing changed.
    empty,
    /// One line was appended; the slice is owned by the ledger and stays valid
    /// until deinit (each line is its own allocation).
    answered: []const u8,
};

pub fn arrowAnswer(a: Arrow) Answer {
    return switch (a) {
        .left => .no,
        .right => .yes,
    };
}

/// Render one ledger line (no trailing newline) into `buf`, byte for byte the
/// way the real Clivor card does (`json.dumps` of {ts, card, id, question,
/// answer, disk}): ", " and ": " separators, non-ASCII as \uXXXX. `ts` is a
/// string such as 2026-10-06T12:00:00 supplied by the caller.
pub fn renderLine(
    buf: []u8,
    card: Card,
    answer: Answer,
    ts: []const u8,
) error{NoSpaceLeft}![]const u8 {
    var w: std.Io.Writer = .fixed(buf);
    writeLine(&w, card, answer, ts) catch return error.NoSpaceLeft;
    return w.buffered();
}

const json_opts: std.json.Stringify.Options = .{ .escape_unicode = true };

fn writeLine(w: *std.Io.Writer, card: Card, answer: Answer, ts: []const u8) std.Io.Writer.Error!void {
    try w.writeAll("{\"ts\": ");
    try std.json.Stringify.encodeJsonString(ts, json_opts, w);
    try w.writeAll(", \"card\": ");
    try std.json.Stringify.encodeJsonString(card.slug, json_opts, w);
    try w.writeAll(", \"id\": ");
    try std.json.Stringify.encodeJsonString(card.id, json_opts, w);
    try w.writeAll(", \"question\": ");
    try std.json.Stringify.encodeJsonString(card.question, json_opts, w);
    try w.print(", \"answer\": \"{s}\", \"disk\": ", .{@tagName(answer)});
    try std.json.Stringify.encodeJsonString(card.disk, json_opts, w);
    try w.writeAll("}");
}

const Verdict = enum { kept, blank, bad, duplicate };

pub const Deck = struct {
    gpa: Allocator,
    /// The deck after drops. Borrowed strings.
    cards: std.ArrayList(Card) = .empty,
    /// Append-only. Readable history lines (first line per id) first, then
    /// this sitting's answers. Skipped lines are not in it.
    ledger: std.ArrayList([]u8) = .empty,
    /// Every id that is in the ledger or already in the deck. Keys are owned.
    known: std.StringHashMapUnmanaged(void) = .empty,
    cursor: usize = 0,
    face: Face = .decision,
    /// How many input cards were dropped (id in ledger, or repeated).
    dropped: usize = 0,
    /// History lines skipped as unreadable: not JSON, not an object, no string
    /// id, invalid UTF-8, a second object on the line, or over `max_line_bytes`.
    bad_lines: usize = 0,
    /// History lines skipped because they were empty or only spaces and tabs.
    blank_lines: usize = 0,
    /// History lines skipped because their id was already seen (first wins).
    duplicate_ids: usize = 0,
    /// The history bytes did not end in a newline. The writer must put one
    /// newline in front of the next appended line, then call `newlineWritten`.
    needs_newline: bool = false,
    /// The final history line had no newline and was unreadable: the mark of a
    /// crash in the middle of an append.
    torn_tail: bool = false,

    /// `history` is the existing ledger, one JSON line each (already split).
    /// Bad lines are skipped and counted. Cards whose id appears in a kept line
    /// are dropped, and so is a repeated id within `cards`. Only
    /// `error.OutOfMemory` fails.
    pub fn init(gpa: Allocator, cards: []const Card, history: []const []const u8) !Deck {
        var d: Deck = .{ .gpa = gpa };
        errdefer d.deinit();
        for (history) |line| _ = try d.takeLine(line);
        try d.takeCards(cards);
        return d;
    }

    /// As `init`, from the raw bytes of the ledger file. Splits on LF only,
    /// strips a trailing CR from each line, and sets `needs_newline` and
    /// `torn_tail`. The bytes are never modified.
    pub fn initFromBytes(gpa: Allocator, cards: []const Card, bytes: []const u8) !Deck {
        var d: Deck = .{ .gpa = gpa };
        errdefer d.deinit();
        if (bytes.len > 0) {
            const ends_with_lf = bytes[bytes.len - 1] == '\n';
            const body = if (ends_with_lf) bytes[0 .. bytes.len - 1] else bytes;
            var last: Verdict = .blank;
            var it = std.mem.splitScalar(u8, body, '\n');
            while (it.next()) |line| last = try d.takeLine(line);
            d.needs_newline = !ends_with_lf;
            d.torn_tail = !ends_with_lf and last == .bad;
        }
        try d.takeCards(cards);
        return d;
    }

    /// Call once the writer has put the newline that `needs_newline` asked for.
    pub fn newlineWritten(self: *Deck) void {
        self.needs_newline = false;
    }

    fn takeLine(self: *Deck, raw: []const u8) !Verdict {
        const line = std.mem.trimEnd(u8, raw, "\r");
        if (std.mem.trim(u8, line, " \t").len == 0) {
            self.blank_lines += 1;
            return .blank;
        }
        if (line.len > max_line_bytes) {
            self.bad_lines += 1;
            return .bad;
        }
        const Row = struct { id: []const u8 };
        const parsed = std.json.parseFromSlice(Row, self.gpa, line, .{ .ignore_unknown_fields = true }) catch |err| switch (err) {
            error.OutOfMemory => return error.OutOfMemory,
            else => {
                self.bad_lines += 1;
                return .bad;
            },
        };
        defer parsed.deinit();
        if (self.known.contains(parsed.value.id)) {
            self.duplicate_ids += 1;
            return .duplicate;
        }
        try self.remember(parsed.value.id);
        const copy = try self.gpa.dupe(u8, line);
        errdefer self.gpa.free(copy);
        try self.ledger.append(self.gpa, copy);
        return .kept;
    }

    fn takeCards(self: *Deck, cards: []const Card) !void {
        for (cards) |c| {
            if (self.known.contains(c.id)) {
                self.dropped += 1;
                continue;
            }
            try self.remember(c.id);
            try self.cards.append(self.gpa, c);
        }
    }

    pub fn deinit(self: *Deck) void {
        for (self.ledger.items) |line| self.gpa.free(line);
        self.ledger.deinit(self.gpa);
        var it = self.known.keyIterator();
        while (it.next()) |k| self.gpa.free(k.*);
        self.known.deinit(self.gpa);
        self.cards.deinit(self.gpa);
        self.* = undefined;
    }

    fn remember(self: *Deck, id: []const u8) !void {
        if (self.known.contains(id)) return;
        const key = try self.gpa.dupe(u8, id);
        errdefer self.gpa.free(key);
        try self.known.put(self.gpa, key, {});
    }

    /// The card now showing on face 1, if any.
    pub fn current(self: *const Deck) ?Card {
        if (self.cursor >= self.cards.items.len) return null;
        return self.cards.items[self.cursor];
    }

    pub fn remaining(self: *const Deck) usize {
        return self.cards.items.len - self.cursor;
    }

    /// The only way between faces. Never touches the ledger or the cursor.
    pub fn flip(self: *Deck) void {
        self.face = switch (self.face) {
            .decision => .ledger,
            .ledger => .decision,
        };
    }

    /// Left = no, right = yes, on face 1 only. `scratch` is where the line is
    /// rendered before it is copied into the ledger; on any error nothing has
    /// changed (the cursor moves only after the append succeeded).
    pub fn press(self: *Deck, arrow: Arrow, ts: []const u8, scratch: []u8) !Press {
        if (self.face != .decision) return .inert;
        const card = self.current() orelse return .empty;
        const line = try renderLine(scratch, card, arrowAnswer(arrow), ts);
        const copy = try self.gpa.dupe(u8, line);
        errdefer self.gpa.free(copy);
        try self.ledger.append(self.gpa, copy);
        self.cursor += 1;
        return .{ .answered = copy };
    }
};

// ---- tests ------------------------------------------------------------

const testing = std.testing;

const three = [_]Card{
    .{ .id = "c1", .question = "first" },
    .{ .id = "c2", .question = "second" },
    .{ .id = "c3", .question = "third" },
};

const ts0 = "2026-10-06T12:00:00";

const row_head = "{\"ts\": \"" ++ ts0 ++ "\", \"card\": \"clivor\", \"id\": \"";
const row_tail = "\", \"question\": \"x\", \"answer\": \"yes\", \"disk\": \"\"}";

fn row(comptime id: []const u8) *const [row_head.len + id.len + row_tail.len]u8 {
    return row_head ++ id ++ row_tail;
}

test "left is no, right is yes, one appended line each" {
    var d = try Deck.init(testing.allocator, &three, &.{});
    defer d.deinit();
    var buf: [256]u8 = undefined;

    const p1 = try d.press(.left, "2026-10-06T12:00:00", &buf);
    try testing.expectEqualStrings(
        "{\"ts\": \"2026-10-06T12:00:00\", \"card\": \"clivor\", \"id\": \"c1\", \"question\": \"first\", \"answer\": \"no\", \"disk\": \"\"}",
        p1.answered,
    );
    const p2 = try d.press(.right, "2026-10-06T12:00:01", &buf);
    try testing.expectEqualStrings(
        "{\"ts\": \"2026-10-06T12:00:01\", \"card\": \"clivor\", \"id\": \"c2\", \"question\": \"second\", \"answer\": \"yes\", \"disk\": \"\"}",
        p2.answered,
    );
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 1), d.remaining());
}

test "golden lines: byte for byte what Python json.dumps wrote for the real Clivor row" {
    // Expected strings were produced by python -I with stdlib json.dumps on
    // the six keys in the real order. No journal-clip or Clivor code ran.
    var buf: [512]u8 = undefined;
    const a: Card = .{ .id = "a1", .question = "Is it done?", .disk = "C:\\dev\\x" };
    try testing.expectEqualStrings(
        "{\"ts\": \"2026-10-06T12:00:01\", \"card\": \"clivor\", \"id\": \"a1\", \"question\": \"Is it done?\", \"answer\": \"no\", \"disk\": \"C:\\\\dev\\\\x\"}",
        try renderLine(&buf, a, .no, "2026-10-06T12:00:01"),
    );
    const g: Card = .{ .id = "g\"1", .question = "caf\u{e9} \u{2713} \u{1F600} \x7f \x01 \x08 \x0c\n\t\\ end" };
    try testing.expectEqualStrings(
        "{\"ts\": \"2026-10-06T12:00:00\", \"card\": \"clivor\", \"id\": \"g\\\"1\", \"question\": \"caf\\u00e9 \\u2713 \\ud83d\\ude00 \\u007f \\u0001 \\b \\f\\n\\t\\\\ end\", \"answer\": \"yes\", \"disk\": \"\"}",
        try renderLine(&buf, g, .yes, "2026-10-06T12:00:00"),
    );
}

test "arrow on face 2 changes nothing" {
    var d = try Deck.init(testing.allocator, &three, &.{});
    defer d.deinit();
    var buf: [256]u8 = undefined;
    _ = try d.press(.right, ts0, &buf); // one real answer first

    d.flip();
    try testing.expectEqual(Face.ledger, d.face);
    const cursor_before = d.cursor;
    const len_before = d.ledger.items.len;
    const first_before = try testing.allocator.dupe(u8, d.ledger.items[0]);
    defer testing.allocator.free(first_before);

    for ([_]Arrow{ .left, .right, .left, .right }) |a| {
        const r = try d.press(a, ts0, &buf);
        try testing.expect(r == .inert);
    }
    try testing.expectEqual(cursor_before, d.cursor);
    try testing.expectEqual(len_before, d.ledger.items.len);
    try testing.expectEqualStrings(first_before, d.ledger.items[0]);
    try testing.expectEqual(Face.ledger, d.face); // arrows do not flip either

    // flip is the way back, and then arrows work again
    d.flip();
    try testing.expectEqual(Face.decision, d.face);
    const r = try d.press(.left, ts0, &buf);
    try testing.expect(r == .answered);
    try testing.expectEqual(len_before + 1, d.ledger.items.len);
}

test "a card id already in the ledger is dropped from the deck" {
    const history = [_][]const u8{row("c2")};
    var d = try Deck.init(testing.allocator, &three, &history);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 2), d.cards.items.len);
    try testing.expectEqual(@as(usize, 1), d.dropped);
    try testing.expectEqualStrings("c1", d.cards.items[0].id);
    try testing.expectEqualStrings("c3", d.cards.items[1].id);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len); // history kept
}

test "a repeated card id inside the input is dropped" {
    const dup = [_]Card{
        .{ .id = "a", .question = "one" },
        .{ .id = "a", .question = "one again" },
        .{ .id = "b", .question = "two" },
    };
    var d = try Deck.init(testing.allocator, &dup, &.{});
    defer d.deinit();
    try testing.expectEqual(@as(usize, 2), d.cards.items.len);
    try testing.expectEqual(@as(usize, 1), d.dropped);
    try testing.expectEqualStrings("one", d.cards.items[0].question);
}

test "an answered card is asked once: a rebuilt deck drops it" {
    var d1 = try Deck.init(testing.allocator, &three, &.{});
    defer d1.deinit();
    var buf: [256]u8 = undefined;
    _ = try d1.press(.right, ts0, &buf);
    _ = try d1.press(.left, ts0, &buf);

    var d2 = try Deck.init(testing.allocator, &three, d1.ledger.items);
    defer d2.deinit();
    try testing.expectEqual(@as(usize, 1), d2.cards.items.len);
    try testing.expectEqualStrings("c3", d2.current().?.id);
    try testing.expectEqual(@as(usize, 2), d2.dropped);
    try testing.expectEqual(@as(usize, 0), d2.bad_lines);
}

test "an empty deck answers nothing" {
    var d = try Deck.init(testing.allocator, &.{}, &.{});
    defer d.deinit();
    var buf: [64]u8 = undefined;
    const r = try d.press(.right, ts0, &buf);
    try testing.expect(r == .empty);
    try testing.expectEqual(@as(usize, 0), d.ledger.items.len);
}

test "ledger is append-only: earlier lines never change, line slices stay valid" {
    var d = try Deck.init(testing.allocator, &three, &.{});
    defer d.deinit();
    var buf: [256]u8 = undefined;
    const p = try d.press(.right, ts0, &buf);
    const first = p.answered;
    const snapshot = try testing.allocator.dupe(u8, first);
    defer testing.allocator.free(snapshot);
    _ = try d.press(.left, ts0, &buf);
    _ = try d.press(.left, ts0, &buf);
    d.flip();
    d.flip();
    try testing.expectEqualStrings(snapshot, first); // same memory, same bytes
    try testing.expectEqualStrings(snapshot, d.ledger.items[0]);
    try testing.expectEqual(@as(usize, 3), d.ledger.items.len);
}

test "an answer line with a quote and a newline in the card text parses back" {
    const nasty = "he said \"yes\"\nthen left\\ \t and \x01 end";
    const card: Card = .{ .id = "q\"1", .question = nasty, .disk = "d\"k" };
    var buf: [512]u8 = undefined;
    const line = try renderLine(&buf, card, .yes, ts0);

    // one physical line: no raw newline or carriage return survives
    try testing.expect(std.mem.indexOfScalar(u8, line, '\n') == null);
    try testing.expect(std.mem.indexOfScalar(u8, line, '\r') == null);

    const Row = struct { ts: []const u8, card: []const u8, id: []const u8, question: []const u8, answer: Answer, disk: []const u8 };
    const parsed = try std.json.parseFromSlice(Row, testing.allocator, line, .{});
    defer parsed.deinit();
    try testing.expectEqualStrings(ts0, parsed.value.ts);
    try testing.expectEqualStrings("clivor", parsed.value.card);
    try testing.expectEqualStrings(card.id, parsed.value.id);
    try testing.expectEqualStrings(nasty, parsed.value.question);
    try testing.expectEqual(Answer.yes, parsed.value.answer);
    try testing.expectEqualStrings("d\"k", parsed.value.disk);
}

test "the nasty line survives the full path: press, ledger, rebuild" {
    const nasty = [_]Card{.{ .id = "n1", .question = "a \"quoted\"\nline" }};
    var d = try Deck.init(testing.allocator, &nasty, &.{});
    defer d.deinit();
    var buf: [256]u8 = undefined;
    _ = try d.press(.left, ts0, &buf);

    var d2 = try Deck.init(testing.allocator, &nasty, d.ledger.items);
    defer d2.deinit();
    try testing.expectEqual(@as(usize, 0), d2.cards.items.len);
    try testing.expectEqual(@as(usize, 1), d2.dropped);
}

test "non-ASCII text round-trips" {
    const card: Card = .{ .id = "u", .question = "caf\xc3\xa9 \xe2\x9c\x93 \xf0\x9f\x98\x80" };
    var buf: [256]u8 = undefined;
    const line = try renderLine(&buf, card, .no, ts0);
    for (line) |ch| try testing.expect(ch < 0x80); // written as \u escapes, like json.dumps
    const Row = struct { id: []const u8, question: []const u8 };
    const parsed = try std.json.parseFromSlice(Row, testing.allocator, line, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    try testing.expectEqualStrings(card.question, parsed.value.question);
}

test "a too-small buffer is an error and the deck is unchanged" {
    var d = try Deck.init(testing.allocator, &three, &.{});
    defer d.deinit();
    var tiny: [8]u8 = undefined;
    try testing.expectError(error.NoSpaceLeft, d.press(.right, ts0, &tiny));
    try testing.expectEqual(@as(usize, 0), d.cursor);
    try testing.expectEqual(@as(usize, 0), d.ledger.items.len);
    try testing.expectError(error.NoSpaceLeft, renderLine(&tiny, three[0], .yes, ts0));
}

test "a malformed history line in the middle is skipped, counted, and the rest loads" {
    const history = [_][]const u8{
        row("c1"),
        "{not json",
        row("c2"),
    };
    var d = try Deck.init(testing.allocator, &three, &history);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.bad_lines);
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
    try testing.expectEqualStrings(row("c1"), d.ledger.items[0]);
    try testing.expectEqualStrings(row("c2"), d.ledger.items[1]);
    try testing.expectEqual(@as(usize, 1), d.cards.items.len);
    try testing.expectEqualStrings("c3", d.cards.items[0].id);
    try testing.expectEqual(@as(usize, 2), d.dropped);
}

test "a history line with no id is skipped and counted, its card stays in the deck" {
    const history = [_][]const u8{
        "{\"question\":\"x\",\"answer\":\"yes\"}",
        "{\"id\":7,\"question\":\"c1\"}",
        "{\"id\":null}",
    };
    var d = try Deck.init(testing.allocator, &three, &history);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 3), d.bad_lines);
    try testing.expectEqual(@as(usize, 0), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 3), d.cards.items.len);
}

test "valid JSON that is not an object is skipped and counted" {
    const history = [_][]const u8{ "123", "[1,2]", "\"c1\"", "null", "true" };
    var d = try Deck.init(testing.allocator, &three, &history);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 5), d.bad_lines);
    try testing.expectEqual(@as(usize, 0), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 3), d.cards.items.len);
}

test "two objects glued on one line (a merged append) is skipped and counted" {
    const glued = row("c1") ++ row("c2");
    const history = [_][]const u8{glued};
    var d = try Deck.init(testing.allocator, &three, &history);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.bad_lines);
    try testing.expectEqual(@as(usize, 3), d.cards.items.len);
}

test "a torn final line with no newline: skipped, counted, flagged, next append gets its own line" {
    const good = row("c1") ++ "\n";
    const torn = "{\"ts\": \"2026-10-06T12:00:01\", \"card\": \"cli";
    const file = good ++ torn;

    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.bad_lines);
    try testing.expect(d.torn_tail);
    try testing.expect(d.needs_newline);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 2), d.cards.items.len);

    // What a file layer must do: newline first, then the line, then newline.
    var buf: [256]u8 = undefined;
    const p = try d.press(.right, "2026-10-06T12:00:02", &buf);
    var after: std.ArrayList(u8) = .empty;
    defer after.deinit(testing.allocator);
    try after.appendSlice(testing.allocator, file);
    if (d.needs_newline) {
        try after.append(testing.allocator, '\n');
        d.newlineWritten();
    }
    try after.appendSlice(testing.allocator, p.answered);
    try after.append(testing.allocator, '\n');
    try testing.expect(!d.needs_newline);

    // The old bytes are a prefix of the new file: nothing was rewritten.
    try testing.expect(std.mem.startsWith(u8, after.items, file));

    // Reading it back: the torn line is still one bad line, the new answer survives.
    var d2 = try Deck.initFromBytes(testing.allocator, &three, after.items);
    defer d2.deinit();
    try testing.expectEqual(@as(usize, 1), d2.bad_lines);
    try testing.expect(!d2.torn_tail);
    try testing.expect(!d2.needs_newline);
    try testing.expectEqual(@as(usize, 2), d2.ledger.items.len);
    try testing.expectEqualStrings(p.answered, d2.ledger.items[1]);
    try testing.expectEqual(@as(usize, 1), d2.cards.items.len);
    try testing.expectEqualStrings("c3", d2.cards.items[0].id);
}

test "without the newline the next answer is glued to the torn line and lost" {
    const torn = "{\"ts\": \"2026-10-06T12:00:01\", \"card\": \"cli";
    var d = try Deck.initFromBytes(testing.allocator, &three, torn);
    defer d.deinit();
    var buf: [256]u8 = undefined;
    const p = try d.press(.right, ts0, &buf);
    var wrong: std.ArrayList(u8) = .empty;
    defer wrong.deinit(testing.allocator);
    try wrong.appendSlice(testing.allocator, torn);
    try wrong.appendSlice(testing.allocator, p.answered);
    try wrong.append(testing.allocator, '\n');
    var d2 = try Deck.initFromBytes(testing.allocator, &three, wrong.items);
    defer d2.deinit();
    try testing.expectEqual(@as(usize, 1), d2.bad_lines);
    try testing.expectEqual(@as(usize, 0), d2.ledger.items.len);
    try testing.expectEqual(@as(usize, 3), d2.cards.items.len); // c1 would be asked again
}

test "a final line that is whole but has no newline: kept, flagged, not torn" {
    const file = row("c1") ++ "\n" ++ row("c2");
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 0), d.bad_lines);
    try testing.expect(!d.torn_tail);
    try testing.expect(d.needs_newline);
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
}

test "a file that ends in a newline needs none, and an empty file is empty" {
    var d = try Deck.initFromBytes(testing.allocator, &three, row("c1") ++ "\n");
    defer d.deinit();
    try testing.expect(!d.needs_newline);
    try testing.expectEqual(@as(usize, 0), d.blank_lines);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len);

    var e = try Deck.initFromBytes(testing.allocator, &three, "");
    defer e.deinit();
    try testing.expect(!e.needs_newline);
    try testing.expectEqual(@as(usize, 0), e.blank_lines + e.bad_lines);
    try testing.expectEqual(@as(usize, 3), e.cards.items.len);
}

test "blank lines are skipped and counted apart from bad lines" {
    const file = "\n" ++ row("c1") ++ "\n   \n\t\n\r\n" ++ row("c2") ++ "\n\n";
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 5), d.blank_lines);
    try testing.expectEqual(@as(usize, 0), d.bad_lines);
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
    try testing.expect(!d.needs_newline);
}

test "CRLF lines load, and the kept line has no carriage return" {
    const file = row("c1") ++ "\r\n" ++ row("c2") ++ "\r\n";
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 0), d.bad_lines);
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
    try testing.expectEqualStrings(row("c1"), d.ledger.items[0]);
    try testing.expectEqualStrings(row("c2"), d.ledger.items[1]);
    try testing.expectEqual(@as(usize, 1), d.cards.items.len);
}

test "duplicate ids: the first line wins, later ones are counted" {
    const first = "{\"id\":\"c2\",\"answer\":\"yes\"}";
    const second = "{\"id\":\"c2\",\"answer\":\"no\"}";
    const file = first ++ "\n" ++ second ++ "\n" ++ row("c1") ++ "\n";
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.duplicate_ids);
    try testing.expectEqual(@as(usize, 0), d.bad_lines);
    try testing.expectEqual(@as(usize, 2), d.ledger.items.len);
    try testing.expectEqualStrings(first, d.ledger.items[0]);
    try testing.expectEqual(@as(usize, 1), d.cards.items.len);
    try testing.expectEqualStrings("c3", d.cards.items[0].id);
}

test "a very long line of junk is skipped without parsing, a long valid line is kept" {
    const big = try testing.allocator.alloc(u8, max_line_bytes + 1);
    defer testing.allocator.free(big);
    @memset(big, 'x');

    var junk: std.ArrayList(u8) = .empty;
    defer junk.deinit(testing.allocator);
    try junk.appendSlice(testing.allocator, big);
    try junk.append(testing.allocator, '\n');
    try junk.appendSlice(testing.allocator, row("c1"));
    try junk.append(testing.allocator, '\n');
    var d = try Deck.initFromBytes(testing.allocator, &three, junk.items);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.bad_lines);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len);

    // 100 KiB of question text is a real, valid row and stays.
    var long: std.ArrayList(u8) = .empty;
    defer long.deinit(testing.allocator);
    try long.appendSlice(testing.allocator, "{\"id\":\"c2\",\"question\":\"");
    try long.appendNTimes(testing.allocator, 'y', 100 * 1024);
    try long.appendSlice(testing.allocator, "\"}\n");
    var e = try Deck.initFromBytes(testing.allocator, &three, long.items);
    defer e.deinit();
    try testing.expectEqual(@as(usize, 0), e.bad_lines);
    try testing.expectEqual(@as(usize, 1), e.ledger.items.len);
    try testing.expectEqual(@as(usize, 2), e.cards.items.len);
}

test "a valid row over the line cap is skipped, so its card would be asked again" {
    var long: std.ArrayList(u8) = .empty;
    defer long.deinit(testing.allocator);
    try long.appendSlice(testing.allocator, "{\"id\":\"c1\",\"question\":\"");
    try long.appendNTimes(testing.allocator, 'y', max_line_bytes);
    try long.appendSlice(testing.allocator, "\"}\n");
    var d = try Deck.initFromBytes(testing.allocator, &three, long.items);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 1), d.bad_lines);
    try testing.expectEqual(@as(usize, 3), d.cards.items.len);
}

test "non-UTF8 bytes: the line is skipped and counted, its id is not remembered" {
    const file = "{\"id\":\"c1\",\"question\":\"\xff\xfe\"}\n" ++ row("c2") ++ "\n" ++ "\xc3\n" ++ "{\"id\":\"c3\xe2\x9c\"}\n";
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 3), d.bad_lines);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 2), d.cards.items.len);
    try testing.expectEqualStrings("c1", d.cards.items[0].id);
    try testing.expectEqualStrings("c3", d.cards.items[1].id);
}

test "valid non-ASCII rows load, and U+2028 inside a row does not split it" {
    const file = "{\"id\":\"c1\",\"question\":\"a\xe2\x80\xa8b \xc2\x85 c \xe2\x9c\x93\"}\n";
    var d = try Deck.initFromBytes(testing.allocator, &three, file);
    defer d.deinit();
    try testing.expectEqual(@as(usize, 0), d.bad_lines);
    try testing.expectEqual(@as(usize, 1), d.ledger.items.len);
    try testing.expectEqual(@as(usize, 2), d.cards.items.len);
}

test "reading history never changes the bytes it was given" {
    const original = row("c1") ++ "\r\n{bad\n\n" ++ row("c2") ++ "\n{torn";
    var copy: [original.len]u8 = undefined;
    @memcpy(&copy, original);
    var d = try Deck.initFromBytes(testing.allocator, &three, &copy);
    defer d.deinit();
    try testing.expectEqualStrings(original, &copy);
    try testing.expectEqual(@as(usize, 2), d.bad_lines);
    try testing.expectEqual(@as(usize, 1), d.blank_lines);
    try testing.expect(d.torn_tail);
}

fn loadForOom(gpa: Allocator, bytes: []const u8) !void {
    var d = try Deck.initFromBytes(gpa, &three, bytes);
    d.deinit();
}

test "out of memory while reading history is an error, never a skip, and leaks nothing" {
    const file = row("c1") ++ "\n{bad\n" ++ row("c2") ++ "\n" ++ row("c2") ++ "\n{torn";
    try testing.checkAllAllocationFailures(testing.allocator, loadForOom, .{@as([]const u8, file)});
}

fn loadBadOnlyForOom(gpa: Allocator, bytes: []const u8) !void {
    var d = try Deck.initFromBytes(gpa, &.{}, bytes);
    d.deinit();
}

test "out of memory inside the parse of a bad line is not mistaken for a bad line" {
    // Nothing allocates after the parse here, so a swallowed OutOfMemory
    // would come back as success and checkAllAllocationFailures would say so.
    try testing.checkAllAllocationFailures(testing.allocator, loadBadOnlyForOom, .{@as([]const u8, "{bad\n")});
}

test "flip twice is a round trip and touches no data" {
    var d = try Deck.init(testing.allocator, &three, &.{});
    defer d.deinit();
    d.flip();
    d.flip();
    try testing.expectEqual(Face.decision, d.face);
    try testing.expectEqual(@as(usize, 0), d.cursor);
    try testing.expectEqual(@as(usize, 0), d.ledger.items.len);
}
