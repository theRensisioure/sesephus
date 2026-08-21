const std = @import("std");
const builtin = @import("builtin");

// Covenant spoken output. Speech is additive: callers always print the text
// first, then offer it aloud, so a missing synth never blocks the loop.
// Only OS-shipped, fully offline synthesizers are used — SAPI via PowerShell
// on Windows, espeak-ng/espeak on POSIX, `say` on macOS. No network, no new
// runtime dependencies; the user-facing path must never require either.

pub const SpeechError = error{NoSpeechEngine};

fn runArgv(io: std.Io, argv: []const []const u8) !void {
    var child = try std.process.spawn(io, .{
        .argv = argv,
        .stdin = .inherit,
        .stdout = .inherit,
        .stderr = .inherit,
    });
    _ = try child.wait(io);
}

pub fn say(allocator: std.mem.Allocator, io: std.Io, text: []const u8) SpeechError!void {
    if (text.len == 0) return;

    if (builtin.os.tag == .windows) {
        // Single-quoted PowerShell string: the only escape needed is ' -> ''.
        var escaped = std.ArrayList(u8).empty;
        defer escaped.deinit(allocator);
        for (text) |c| {
            if (c == '\'') {
                escaped.appendSlice(allocator, "''") catch return SpeechError.NoSpeechEngine;
            } else {
                escaped.append(allocator, c) catch return SpeechError.NoSpeechEngine;
            }
        }
        const cmd = std.fmt.allocPrint(
            allocator,
            "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{s}')",
            .{escaped.items},
        ) catch return SpeechError.NoSpeechEngine;
        defer allocator.free(cmd);

        const argv = [_][]const u8{ "powershell", "-NoProfile", "-Command", cmd };
        runArgv(io, &argv) catch return SpeechError.NoSpeechEngine;
        return;
    }

    // POSIX: first engine that runs wins. -s 150 keeps espeak at a calm pace.
    const espeak_engines = [_][]const u8{ "espeak-ng", "espeak" };
    for (espeak_engines) |engine| {
        const argv = [_][]const u8{ engine, "-s", "150", text };
        if (runArgv(io, &argv)) |_| return else |_| continue;
    }
    const say_argv = [_][]const u8{ "say", text };
    if (runArgv(io, &say_argv)) |_| return else |_| {}

    return SpeechError.NoSpeechEngine;
}
