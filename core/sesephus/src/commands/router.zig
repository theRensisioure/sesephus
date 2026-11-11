//! Single table of host modules. Help text and dispatch must agree with this list.

const std = @import("std");

pub const Kind = enum { wired, stub, alias };

pub const Entry = struct {
    name: []const u8,
    kind: Kind,
    /// One-line help; null means listed only under a parent module line.
    help: ?[]const u8 = null,
};

/// Canonical host modules in display order.
pub const modules = [_]Entry{
    .{ .name = "status", .kind = .wired, .help = "Show state, clients, subgroups, pending alarms" },
    .{ .name = "dialogue", .kind = .wired, .help = "start [appliance] | review [n] [appliance]" },
    .{ .name = "alarm", .kind = .wired, .help = "schedule | group | list | toggle | bulk | interval | adjust" },
    .{ .name = "group", .kind = .wired, .help = "create | list | rename | edit | delete" },
    .{ .name = "lead", .kind = .wired, .help = "qualify <post_text> [--handle <h>] (mine|feed = STUB)" },
    .{ .name = "vault", .kind = .wired, .help = "ingest-archive | set-key (status|backup|audit = STUB)" },
    .{ .name = "aytree", .kind = .wired, .help = "open|map|tree|serve|status" },
    .{ .name = "tree", .kind = .alias, .help = "alias for aytree" },
    .{ .name = "backup", .kind = .wired, .help = "[dest_path] — hot copy of the vault database" },
    .{ .name = "help", .kind = .wired, .help = "This list" },
    .{ .name = "exit", .kind = .wired, .help = "Shutdown the daemon" },
    .{ .name = "journal", .kind = .stub, .help = "STUB — capture owner is external Clippers" },
    .{ .name = "rhythm", .kind = .stub, .help = "STUB — use alarm (live scheduler)" },
    .{ .name = "stoic", .kind = .stub, .help = "STUB — deferred" },
};

pub fn find(name: []const u8) ?Entry {
    for (modules) |m| {
        if (std.mem.eql(u8, m.name, name)) return m;
    }
    return null;
}

pub fn isWired(name: []const u8) bool {
    const e = find(name) orelse return false;
    return e.kind == .wired or e.kind == .alias;
}

pub fn isStub(name: []const u8) bool {
    const e = find(name) orelse return false;
    return e.kind == .stub;
}

/// Build host help from the table. Caller frees with allocator.
pub fn buildHostUsage(allocator: std.mem.Allocator) ![]u8 {
    var body: std.ArrayList(u8) = .empty;
    errdefer body.deinit(allocator);
    var aw: std.Io.Writer.Allocating = .fromArrayList(allocator, &body);

    try aw.writer.writeAll(
        \\==================================================
        \\           SESEFUS — Audio-First Growth Engine
        \\   Public lineage 0.1.0. Voice is external Clippers.
        \\==================================================
        \\
        \\Wired commands (real logic runs — docs/CANON.md section 2):
        \\
    );
    for (modules) |m| {
        if (m.kind != .wired and m.kind != .alias) continue;
        if (m.help) |h| {
            try aw.writer.print("  {s:<36} {s}\n", .{ m.name, h });
        }
    }
    try aw.writer.writeAll(
        \\
        \\Not wired yet (STUB — prints honesty, does NOTHING as a product loop):
        \\
    );
    for (modules) |m| {
        if (m.kind != .stub) continue;
        if (m.help) |h| {
            try aw.writer.print("  {s:<36} {s}\n", .{ m.name, h });
        }
    }
    try aw.writer.writeAll(
        \\
        \\  journal *                  -> STUB. Capture owner: C:\dev\journal-clippers\audio-journal-system
        \\                               Finish path: consume Clippers takes.jsonl schema=1
        \\                               (keep text; wav already destroyed). Not a recorder.
        \\                               Historical voice.bat / tools/voice.py are unsupported.
        \\  rhythm *                   -> STUB. Use alarm (the live scheduler). No fake ALIGNED state.
        \\  stoic *                    -> deferred (unfinished STUB)
        \\  lead mine|feed             -> deferred (only lead qualify is wired)
        \\  vault status|backup|audit  -> deferred (use host backup / --read-vault; vault set-key is wired)
        \\
        \\Global Flags:
        \\  --production     Strict safety mode
        \\  --dry-run, -n    Test without executing
        \\  --help, -h       Show this help
        \\
        \\Artifact Scanner cards are a finder / inventory face, not this host.
        \\
    );
    body = aw.toArrayList();
    return try body.toOwnedSlice(allocator);
}

test "router lists backup and dialogue as wired" {
    try std.testing.expect(isWired("backup"));
    try std.testing.expect(isWired("dialogue"));
    try std.testing.expect(isStub("journal"));
    try std.testing.expect(find("nope") == null);
}
