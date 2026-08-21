const std = @import("std");
const database = @import("../database.zig");
const speech = @import("../speech.zig");
const common = @import("../common.zig");

// The covenant spine: one dialogic turn-taking loop over the encrypted vault,
// with I/O modality as a single swappable knob (the profile).
//   memoir    — typed dialogue in, calm text out (the maker's modality)
//   appliance — same loop, every line also spoken aloud; screen optional
// One prompt at a time. An empty reply is never punished — the same question
// simply stays open. Prose lands in the same encrypted vault as audio.

pub const Profile = enum { memoir, appliance };

const prompts = [_][]const u8{
    "What is on your mind right now?",
    "Tell me one small thing you remember from today.",
    "What would you like to keep, so it is not lost?",
    "Is there a person or a place you have been thinking about?",
    "What should tomorrow-you be reminded of?",
};

// Wrap at a ~62-char measure with breathing room — the DyslexiUI reading
// tokens (65ch measure, generous spacing) translated to the terminal.
fn renderCalm(text: []const u8) void {
    std.debug.print("\n  ", .{});
    var line_len: usize = 0;
    var words = std.mem.tokenizeAny(u8, text, " \n\r\t");
    while (words.next()) |w| {
        if (line_len != 0 and line_len + 1 + w.len > 62) {
            std.debug.print("\n  ", .{});
            line_len = 0;
        }
        if (line_len != 0) {
            std.debug.print(" ", .{});
            line_len += 1;
        }
        std.debug.print("{s}", .{w});
        line_len += w.len;
    }
    std.debug.print("\n\n", .{});
}

// Print, then offer aloud. A missing synth degrades to text, once, quietly.
fn offer(allocator: std.mem.Allocator, io: std.Io, profile: Profile, text: []const u8, warned: *bool) void {
    renderCalm(text);
    if (profile == .appliance) {
        speech.say(allocator, io, text) catch {
            if (!warned.*) {
                std.debug.print("  (no speech engine found — install espeak-ng for spoken output; continuing in text)\n\n", .{});
                warned.* = true;
            }
        };
    }
}

fn parseProfile(tokens: []const ?[]const u8) Profile {
    for (tokens) |maybe| {
        const tok = maybe orelse continue;
        if (std.mem.eql(u8, tok, "appliance")) return .appliance;
    }
    return .memoir;
}

fn runSession(
    allocator: std.mem.Allocator,
    io: std.Io,
    stdin: *std.Io.Reader,
    profile: Profile,
    vault_path: []const u8,
    vault_key: [32]u8,
) !void {
    const session_id = try std.fmt.allocPrint(allocator, "dlg-{d}", .{common.getMilliTimestamp()});
    defer allocator.free(session_id);

    var warned_no_speech = false;
    offer(allocator, io, profile, "This is your time. Say done whenever you want to stop. Nothing is lost.", &warned_no_speech);

    var prompt_idx: usize = 0;
    var kept: usize = 0;

    while (true) {
        const prompt = prompts[prompt_idx % prompts.len];
        offer(allocator, io, profile, prompt, &warned_no_speech);
        std.debug.print("  > ", .{});

        // Share the host REPL's reader — a second buffered reader on the same
        // fd would fight it for input.
        const line = stdin.takeDelimiter('\n') catch break orelse break;
        const reply = std.mem.trim(u8, line, "\r\n\t ");

        if (std.mem.eql(u8, reply, "done") or std.mem.eql(u8, reply, "exit")) break;

        if (reply.len == 0) {
            offer(allocator, io, profile, "No rush. The same question stays open.", &warned_no_speech);
            continue;
        }

        const entry = database.JournalEntry{
            .client_id = "dialogue",
            .timestamp = common.getMilliTimestamp(),
            .filename = "",
            .audio_data_base64 = "",
            .entry_kind = "prose",
            .text = reply,
            .prompt = prompt,
            .session_id = session_id,
        };
        database.appendRecord(vault_path, vault_key, entry, allocator, io) catch |err| {
            std.debug.print("  [Dialogue] Could not save to vault ({}). Your words:\n", .{err});
            renderCalm(reply);
            continue;
        };
        kept += 1;
        offer(allocator, io, profile, "Kept.", &warned_no_speech);
        prompt_idx += 1;
    }

    var closing_buf: [96]u8 = undefined;
    const closing = std.fmt.bufPrint(&closing_buf, "Session closed. {d} entr{s} kept in your vault.", .{
        kept,
        if (kept == 1) "y" else "ies",
    }) catch "Session closed.";
    offer(allocator, io, profile, closing, &warned_no_speech);
}

fn runReview(
    allocator: std.mem.Allocator,
    io: std.Io,
    profile: Profile,
    count: usize,
    vault_path: []const u8,
    vault_key: [32]u8,
) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try database.readAllRecords(vault_path, vault_key, arena.allocator(), io);

    var prose_total: usize = 0;
    for (records) |r| {
        if (r.entry_kind) |k| {
            if (std.mem.eql(u8, k, "prose")) prose_total += 1;
        }
    }

    var warned_no_speech = false;
    if (prose_total == 0) {
        offer(allocator, io, profile, "Nothing written yet. Start with: dialogue start", &warned_no_speech);
        return;
    }

    const show = @min(count, prose_total);
    var skip = prose_total - show;
    for (records) |r| {
        const kind = r.entry_kind orelse continue;
        if (!std.mem.eql(u8, kind, "prose")) continue;
        if (skip > 0) {
            skip -= 1;
            continue;
        }
        if (r.prompt) |p| std.debug.print("  ({s})\n", .{p});
        offer(allocator, io, profile, r.text orelse "", &warned_no_speech);
    }
}

pub fn handleDialogueCommand(
    it: *std.mem.TokenIterator(u8, .any),
    allocator: std.mem.Allocator,
    io: std.Io,
    stdin: *std.Io.Reader,
    vault_path: []const u8,
    vault_key: [32]u8,
) !bool {
    const action = it.next() orelse {
        std.debug.print("Usage: dialogue <start|review> [memoir|appliance] [n]\n", .{});
        return true;
    };

    const tok_a = it.next();
    const tok_b = it.next();
    const profile = parseProfile(&.{ tok_a, tok_b });

    if (std.mem.eql(u8, action, "start")) {
        runSession(allocator, io, stdin, profile, vault_path, vault_key) catch |err| {
            std.debug.print("[Dialogue] Session error: {}\n", .{err});
        };
    } else if (std.mem.eql(u8, action, "review")) {
        var count: usize = 3;
        for ([_]?[]const u8{ tok_a, tok_b }) |maybe| {
            const tok = maybe orelse continue;
            count = std.fmt.parseInt(usize, tok, 10) catch continue;
        }
        runReview(allocator, io, profile, count, vault_path, vault_key) catch |err| {
            std.debug.print("[Dialogue] Review error: {}\n", .{err});
        };
    } else {
        std.debug.print("Unknown dialogue command: {s}\n", .{action});
    }
    return true;
}
