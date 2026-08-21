const std = @import("std");
const builtin = @import("builtin");

const qualify_rel: []const u8 = "prompts/qualify-post.md";
const qualify_script_rel: []const u8 = "tools/qualify_post.py";

fn resolveRepoPromptPath(allocator: std.mem.Allocator, io: std.Io) ![:0]u8 {
    const prefixes = [_][]const u8{ "", "../", "../../", "../../../", "../../../../" };
    const cwd = std.Io.Dir.cwd();

    for (prefixes) |prefix| {
        var buf: [512]u8 = undefined;
        const candidate = if (prefix.len == 0)
            qualify_rel
        else
            std.fmt.bufPrint(&buf, "{s}{s}", .{ prefix, qualify_rel }) catch continue;

        cwd.access(io, candidate, .{}) catch continue;
        return cwd.realPathFileAlloc(io, candidate, allocator);
    }

    return error.PromptNotFound;
}

fn findQualifyScript(allocator: std.mem.Allocator, io: std.Io) ![]const u8 {
    const prefixes = [_][]const u8{ "", "../", "../../", "../../../", "../../../../" };
    const cwd = std.Io.Dir.cwd();
    for (prefixes) |prefix| {
        var buf: [320]u8 = undefined;
        const candidate = if (prefix.len == 0)
            qualify_script_rel
        else
            std.fmt.bufPrint(&buf, "{s}{s}", .{ prefix, qualify_script_rel }) catch continue;
        cwd.access(io, candidate, .{}) catch continue;
        return try allocator.dupe(u8, candidate);
    }
    return error.QualifyScriptNotFound;
}

fn spawnQualify(
    allocator: std.mem.Allocator,
    io: std.Io,
    prompt_path: []const u8,
    post_text: []const u8,
    handle: ?[]const u8,
) !void {
    const script = try findQualifyScript(allocator, io);
    defer allocator.free(script);

    const py: []const u8 = if (builtin.os.tag == .windows) "python" else "python3";

    const post_copy = try allocator.dupe(u8, post_text);
    defer allocator.free(post_copy);

    var handle_copy: ?[]const u8 = null;
    if (handle) |h| {
        handle_copy = try allocator.dupe(u8, h);
    }
    defer if (handle_copy) |hc| allocator.free(hc);

    var args = std.ArrayList([]const u8).empty;
    defer args.deinit(allocator);

    try args.append(allocator, py);
    try args.append(allocator, script);
    try args.append(allocator, "--prompt-path");
    try args.append(allocator, prompt_path);
    try args.append(allocator, "--post");
    try args.append(allocator, post_copy);
    if (handle_copy) |h| {
        try args.append(allocator, "--handle");
        try args.append(allocator, h);
    }

    std.debug.print("[LeadLogic] qualify: spawning Systems Peer subprocess (vLLM)\n", .{});

    var child = try std.process.spawn(io, .{
        .argv = args.items,
        .stdin = .inherit,
        .stdout = .inherit,
        .stderr = .inherit,
    });
    _ = try child.wait(io);
}

pub fn handleLeadCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const action = it.next() orelse {
        std.debug.print("Usage: lead <mine|qualify|feed>\n", .{});
        return true;
    };

    if (std.mem.eql(u8, action, "mine")) {
        const source = it.next() orelse "stoic";
        std.debug.print("[LeadLogic] mine: source={s} → CPU triage ingress (stub)\n", .{source});
    } else if (std.mem.eql(u8, action, "qualify")) {
        const input = it.next() orelse "unknown";
        const prompt_path = resolveRepoPromptPath(allocator, io) catch |err| {
            std.debug.print("[LeadLogic] qualify: could not resolve {s} from repo root: {}\n", .{ qualify_rel, err });
            return true;
        };
        defer allocator.free(prompt_path);

        var handle: ?[]const u8 = null;
        while (it.next()) |tok| {
            if (std.mem.eql(u8, tok, "--handle")) {
                handle = it.next();
            }
        }

        std.debug.print("[LeadLogic] qualify: input='{s}' prompt={s}\n", .{ input, prompt_path });
        spawnQualify(allocator, io, prompt_path, input, handle) catch |err| {
            std.debug.print("[LeadLogic] qualify subprocess failed: {}\n", .{err});
        };
    } else if (std.mem.eql(u8, action, "feed")) {
        const target = it.next() orelse "journal";
        std.debug.print("[LeadLogic] feed: target={s} ← qualified leads (stub)\n", .{target});
    } else {
        std.debug.print("Unknown lead command: {s}\n", .{action});
    }
    return true;
}