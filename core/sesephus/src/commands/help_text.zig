const std = @import("std");

/// Shared host help. `host.zig` prints this; tests assert the same bytes.
/// WIRED vs STUB vs external Clippers must match docs/CANON.md §2 and §5.
pub const clippers_root = "C:\\dev\\journal-clippers\\audio-journal-system";

pub const host_usage =
    \\==================================================
    \\           SESEFUS — Audio-First Growth Engine
    \\   Public lineage 0.1.0. Voice is external Clippers.
    \\==================================================
    \\
    \\Wired commands (real logic runs — docs/CANON.md section 2):
    \\
    \\  status                                     Show state, clients, subgroups, pending alarms
    \\
    \\  dialogue start [appliance]                 Turn-taking capture into the vault (appliance = spoken aloud)
    \\  dialogue review [n] [appliance]            Read (or hear) your last n written entries
    \\
    \\  alarm schedule <client_id> <sec> <action> <duration>
    \\  alarm group <group_id> <sec> <action> <duration>
    \\  alarm list | toggle <true|false> | bulk ... | interval ... | adjust ...
    \\
    \\  group create <name> <client_ids_comma_sep>
    \\  group list | rename | edit | delete
    \\
    \\  lead qualify <post_text> [--handle <h>]    Score a post (spawns tools/qualify_post.py)
    \\  vault ingest-archive [--dry-run] [--limit n]   Ingest memos (spawns tools/ingress_memos.py)
    \\  aytree open|map|tree|serve|status          Suite derivation map (spawns tools/aytree_launch.py)
    \\
    \\  backup [dest_path]                         Hot backup copy of the vault database
    \\  help | exit
    \\
    \\Not wired yet (STUB — prints honesty, does NOTHING as a product loop):
    \\
    \\  journal *                  -> STUB. Capture owner: C:\dev\journal-clippers\audio-journal-system
    \\                               Finish path: consume Clippers takes.jsonl schema=1
    \\                               (keep text; wav already destroyed). Not a recorder.
    \\                               Historical voice.bat / tools/voice.py are unsupported.
    \\  rhythm *                   -> STUB. Use alarm (the live scheduler). No fake ALIGNED state.
    \\  stoic *                    -> deferred (unfinished STUB)
    \\  lead mine|feed             -> deferred (only lead qualify is wired)
    \\  vault status|backup|audit  -> deferred (use --read-vault to inspect)
    \\
    \\Global Flags:
    \\  --production     Strict safety mode
    \\  --dry-run, -n    Test without executing
    \\  --help, -h       Show this help
    \\
    \\Artifact Scanner cards are a finder / inventory face, not this host.
    \\
;

fn contains(haystack: []const u8, needle: []const u8) bool {
    if (needle.len == 0 or needle.len > haystack.len) return false;
    var i: usize = 0;
    while (i + needle.len <= haystack.len) : (i += 1) {
        if (std.mem.eql(u8, haystack[i .. i + needle.len], needle)) return true;
    }
    return false;
}

test "host help names Clippers, STUB journal, and 0.1.0" {
    try std.testing.expect(contains(host_usage, clippers_root));
    try std.testing.expect(contains(host_usage, "STUB"));
    try std.testing.expect(contains(host_usage, "0.1.0"));
    try std.testing.expect(contains(host_usage, "takes.jsonl"));
    try std.testing.expect(contains(host_usage, "schema=1"));
    try std.testing.expect(contains(host_usage, "finder"));
}

test "host help does not sell voice.bat as the live journal loop" {
    const sold_as_loop = "use voice.bat" ++ " (the real journal loop)";
    const canned_start = "Starting audio" ++ " journaling session";
    try std.testing.expect(!contains(host_usage, sold_as_loop));
    try std.testing.expect(!contains(host_usage, canned_start));
    try std.testing.expect(contains(host_usage, "Historical voice.bat"));
    try std.testing.expect(contains(host_usage, "unsupported"));
}
