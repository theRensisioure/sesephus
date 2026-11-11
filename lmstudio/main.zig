const std = @import("std");

// A refused local port is a down LM Studio, not a programmer bug.
// Zig 0.16's Windows connect reports that as error.Unexpected and, in Debug,
// prints a stack trace before the error returns.
pub const std_options: std.Options = .{
    .unexpected_error_tracing = false,
};

const chat_url = "http://127.0.0.1:1234/v1/chat/completions";

const UserMessage = struct {
    role: []const u8,
    content: []const u8,
};

const ChatBody = struct {
    model: []const u8,
    messages: []const UserMessage,
    stream: bool,
};

const AssistantMessage = struct {
    content: ?[]const u8 = null,
};

const Choice = struct {
    message: ?AssistantMessage = null,
};

const ChatPayload = struct {
    choices: []Choice = &.{},
};

/// JSON body for one chat completion. One model id, the prompt, no second model.
pub fn chatRequestBody(allocator: std.mem.Allocator, model: []const u8, prompt: []const u8) ![]u8 {
    const messages = [_]UserMessage{
        .{ .role = "user", .content = prompt },
    };
    return std.json.Stringify.valueAlloc(allocator, ChatBody{
        .model = model,
        .messages = &messages,
        .stream = false,
    }, .{});
}

/// Assistant string from an OpenAI-style chat payload. Caller owns the result.
pub fn extractAssistant(allocator: std.mem.Allocator, payload: []const u8) error{ NoAssistantText, OutOfMemory }![]u8 {
    const parsed = std.json.parseFromSlice(ChatPayload, allocator, payload, .{
        .ignore_unknown_fields = true,
    }) catch return error.NoAssistantText;
    defer parsed.deinit();
    if (parsed.value.choices.len == 0) return error.NoAssistantText;
    const message = parsed.value.choices[0].message orelse return error.NoAssistantText;
    const content = message.content orelse return error.NoAssistantText;
    if (content.len == 0) return error.NoAssistantText;
    return allocator.dupe(u8, content);
}

fn postChat(allocator: std.mem.Allocator, io: std.Io, body: []const u8) ![]u8 {
    var client: std.http.Client = .{ .allocator = allocator, .io = io };
    defer client.deinit();

    var response: std.Io.Writer.Allocating = .init(allocator);
    defer response.deinit();

    const headers = [_]std.http.Header{
        .{ .name = "content-type", .value = "application/json" },
    };
    const fetched = client.fetch(.{
        .location = .{ .url = chat_url },
        .method = .POST,
        .payload = body,
        .extra_headers = &headers,
        .response_writer = &response.writer,
    }) catch return error.ServerUnreachable;

    if (fetched.status != .ok) return error.NoAssistantText;
    return extractAssistant(allocator, response.written());
}

fn fail(io: std.Io, message: []const u8) noreturn {
    std.Io.File.stderr().writeStreamingAll(io, message) catch {};
    std.process.exit(1);
}

const usage = "usage: lmstudio --model <id> --prompt <text>\n";

fn flagValue(args: []const []const u8, i: *usize) ?[]const u8 {
    const next = i.* + 1;
    if (next >= args.len or args[next].len == 0) return null;
    i.* = next;
    return args[next];
}

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);

    var model: ?[]const u8 = null;
    var prompt: ?[]const u8 = null;
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        if (std.mem.eql(u8, args[i], "--model")) {
            const value = flagValue(args, &i) orelse fail(io, usage);
            if (model != null) fail(io, "one model id\n");
            model = value;
        } else if (std.mem.eql(u8, args[i], "--prompt")) {
            const value = flagValue(args, &i) orelse fail(io, usage);
            if (prompt != null) fail(io, "one prompt\n");
            prompt = value;
        } else {
            fail(io, usage);
        }
    }
    const model_id = model orelse fail(io, usage);
    const prompt_text = prompt orelse fail(io, usage);

    const body = try chatRequestBody(allocator, model_id, prompt_text);
    const text = postChat(allocator, io, body) catch |err| switch (err) {
        error.ServerUnreachable => fail(io, "LM Studio server is unreachable\n"),
        error.NoAssistantText => fail(io, "no assistant text\n"),
        else => fail(io, "LM Studio server is unreachable\n"),
    };

    try std.Io.File.stdout().writeStreamingAll(io, text);
}

test "chat request names one model and the prompt" {
    const allocator = std.testing.allocator;
    const model = "caller-model";
    const prompt = "hello from the prompt";
    const body = try chatRequestBody(allocator, model, prompt);
    defer allocator.free(body);

    try std.testing.expectEqual(@as(usize, 1), std.mem.count(u8, body, model));
    try std.testing.expect(std.mem.find(u8, body, prompt) != null);
    try std.testing.expect(std.mem.find(u8, body, "other-model") == null);
    try std.testing.expect(std.mem.find(u8, body, "llama3.2") == null);
    try std.testing.expect(std.mem.find(u8, body, "phi3") == null);
}

test "extract assistant text or fail with none" {
    const allocator = std.testing.allocator;
    const ok_payload =
        \\{"id":"chatcmpl-1","model":"caller-model","choices":[{"index":0,"message":{"role":"assistant","content":"the reply"},"finish_reason":"stop"}]}
    ;
    const text = try extractAssistant(allocator, ok_payload);
    defer allocator.free(text);
    try std.testing.expectEqualStrings("the reply", text);

    const empty_payload = "{\"choices\":[]}";
    try std.testing.expectError(error.NoAssistantText, extractAssistant(allocator, empty_payload));

    const missing_content = "{\"choices\":[{\"message\":{\"role\":\"assistant\"}}]}";
    try std.testing.expectError(error.NoAssistantText, extractAssistant(allocator, missing_content));
}
