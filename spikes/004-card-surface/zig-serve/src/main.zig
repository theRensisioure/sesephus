//! Spike 004a: one HTML page + POST /label -> one JSONL line. Zig 0.16 std only.
//! Binds 127.0.0.1 only. Single-threaded: one connection at a time, closed after each reply.
const std = @import("std");
const Io = std.Io;
const http = std.http;

const max_body: usize = 8 * 1024;

const page =
    \\<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
    \\<title>Card</title>
    \\<style>
    \\body{font:18px system-ui,sans-serif;background:#fafafa;color:#111;display:grid;place-items:center;min-height:100vh;margin:0}
    \\#c{width:min(90vw,26em);min-height:9em;padding:1.2em;border:2px solid #333;border-radius:12px;background:#fff;text-align:center;display:grid;place-items:center}
    \\#h,#s{font-size:.8em;color:#555;margin:.6em;text-align:center}
    \\button{font:inherit;margin:.2em;padding:.4em 1em}
    \\@media(prefers-color-scheme:dark){body{background:#111;color:#eee}#c{background:#1c1c1c;border-color:#aaa}#h,#s{color:#aaa}}
    \\</style>
    \\<main><div id=c></div><div id=h>Left = yes, Right = no, Up/Down = flip</div>
    \\<div><button id=n>No</button><button id=f>Flip</button><button id=y>Yes</button></div><div id=s></div></main>
    \\<script>
    \\var cards=[{id:"c1",q:"Is the sky blue?",a:"Usually, by day."},{id:"c2",q:"Is 7 prime?",a:"Yes."},{id:"c3",q:"Do cats bark?",a:"No."}];
    \\var i=0,back=false,busy=false,c=document.getElementById("c"),s=document.getElementById("s");
    \\function show(){if(i>=cards.length){c.textContent="Done.";return}
    \\c.textContent=back?cards[i].a:cards[i].q;s.textContent="card "+cards[i].id+(back?" (back)":" (front)")}
    \\function flip(){back=!back;show()}
    \\function post(l){if(busy||i>=cards.length)return;busy=true;
    \\fetch("/label",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({id:cards[i].id,label:l,t:Date.now()})})
    \\.then(function(r){s.textContent="saved "+cards[i].id+": "+r.status;i++;back=false;busy=false;show()})
    \\.catch(function(e){s.textContent="error "+e;busy=false})}
    \\document.getElementById("y").onclick=function(){post("yes")};
    \\document.getElementById("n").onclick=function(){post("no")};
    \\document.getElementById("f").onclick=flip;
    \\document.addEventListener("keydown",function(e){
    \\if(e.key=="ArrowLeft"){post("yes")}else if(e.key=="ArrowRight"){post("no")}
    \\else if(e.key=="ArrowUp"||e.key=="ArrowDown"){flip()}else return;e.preventDefault()});
    \\show();
    \\</script>
    \\
;

const Ctx = struct {
    io: Io,
    gpa: std.mem.Allocator,
    labels_path: []const u8,
    /// Card ids already written (keys owned by gpa).
    seen: std.StringHashMapUnmanaged(void) = .empty,
};

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const gpa = init.gpa;

    const labels_path = init.environ_map.get("CARD_LABELS") orelse ".\\labels.jsonl";
    const port: u16 = blk: {
        const s = init.environ_map.get("CARD_PORT") orelse break :blk 8765;
        break :blk std.fmt.parseInt(u16, s, 10) catch {
            std.debug.print("bad CARD_PORT: {s}\n", .{s});
            return error.BadPort;
        };
    };

    var ctx: Ctx = .{ .io = io, .gpa = gpa, .labels_path = labels_path };
    defer {
        var it = ctx.seen.keyIterator();
        while (it.next()) |k| gpa.free(k.*);
        ctx.seen.deinit(gpa);
    }
    try loadSeen(&ctx);

    const addr = try Io.net.IpAddress.parseIp4("127.0.0.1", port);
    var server = try addr.listen(io, .{});
    defer server.deinit(io);
    std.debug.print("listening on 127.0.0.1:{d} labels={s} known_ids={d}\n", .{ port, labels_path, ctx.seen.count() });

    while (true) {
        const stream = server.accept(io) catch |err| {
            std.debug.print("accept error: {s}\n", .{@errorName(err)});
            continue;
        };
        defer stream.close(io);
        handleConn(&ctx, stream) catch |err| {
            std.debug.print("conn error: {s}\n", .{@errorName(err)});
        };
    }
}

fn loadSeen(ctx: *Ctx) !void {
    const cwd = Io.Dir.cwd();
    const text = cwd.readFileAlloc(ctx.io, ctx.labels_path, ctx.gpa, .limited(64 << 20)) catch |err| switch (err) {
        error.FileNotFound => return,
        else => return err,
    };
    defer ctx.gpa.free(text);
    var lines = std.mem.splitScalar(u8, text, '\n');
    while (lines.next()) |line| {
        if (line.len == 0) continue;
        const parsed = std.json.parseFromSlice(std.json.Value, ctx.gpa, line, .{}) catch continue;
        defer parsed.deinit();
        if (parsed.value != .object) continue;
        const id = parsed.value.object.get("id") orelse continue;
        if (id != .string) continue;
        try remember(ctx, id.string);
    }
}

fn remember(ctx: *Ctx, id: []const u8) !void {
    if (ctx.seen.contains(id)) return;
    const key = try ctx.gpa.dupe(u8, id);
    errdefer ctx.gpa.free(key);
    try ctx.seen.put(ctx.gpa, key, {});
}

fn handleConn(ctx: *Ctx, stream: Io.net.Stream) !void {
    const io = ctx.io;
    var rbuf: [8192]u8 = undefined;
    var wbuf: [4096]u8 = undefined;
    var sr = stream.reader(io, &rbuf);
    var sw = stream.writer(io, &wbuf);
    var srv = http.Server.init(&sr.interface, &sw.interface);

    var req = srv.receiveHead() catch |err| switch (err) {
        error.HttpHeadersInvalid, error.HttpHeadersOversize => {
            try sw.interface.writeAll("HTTP/1.1 400 Bad Request\r\ncontent-length: 0\r\nconnection: close\r\n\r\n");
            try sw.interface.flush();
            return;
        },
        else => return err,
    };

    const target = req.head.target;
    const method = req.head.method;

    if (std.mem.eql(u8, target, "/")) {
        if (method != .GET and method != .HEAD) return reply(&req, .method_not_allowed, "text/plain", "method not allowed\n");
        return reply(&req, .ok, "text/html; charset=utf-8", page);
    }
    if (std.mem.eql(u8, target, "/label")) {
        if (method != .POST) return reply(&req, .method_not_allowed, "text/plain", "method not allowed\n");
        return postLabel(ctx, &req);
    }
    return reply(&req, .not_found, "text/plain", "not found\n");
}

fn reply(req: *http.Server.Request, status: http.Status, ctype: []const u8, body: []const u8) !void {
    try req.respond(body, .{
        .status = status,
        .keep_alive = false,
        .extra_headers = &.{.{ .name = "content-type", .value = ctype }},
    });
}

fn postLabel(ctx: *Ctx, req: *http.Server.Request) !void {
    // Refuse oversize bodies from the declared length before reading anything.
    if (req.head.content_length) |n| {
        if (n > max_body) return reply(req, .payload_too_large, "text/plain", "body over 8 KiB\n");
    }

    var bbuf: [1024]u8 = undefined;
    const body_reader = try req.readerExpectContinue(&bbuf);
    const body = body_reader.allocRemaining(ctx.gpa, .limited(max_body + 1)) catch |err| switch (err) {
        error.StreamTooLong => return reply(req, .payload_too_large, "text/plain", "body over 8 KiB\n"),
        error.OutOfMemory => return err,
        error.ReadFailed => return reply(req, .bad_request, "text/plain", "unreadable body\n"),
    };
    defer ctx.gpa.free(body);
    // limit is max_body + 1 so an exactly-8192-byte body is accepted; one more byte is refused.
    if (body.len > max_body) return reply(req, .payload_too_large, "text/plain", "body over 8 KiB\n");

    const parsed = std.json.parseFromSlice(std.json.Value, ctx.gpa, body, .{}) catch |err| switch (err) {
        error.OutOfMemory => return err,
        else => return reply(req, .bad_request, "text/plain", "malformed JSON\n"),
    };
    defer parsed.deinit();
    if (parsed.value != .object) return reply(req, .bad_request, "text/plain", "JSON must be an object\n");

    var id: ?[]const u8 = null;
    if (parsed.value.object.get("id")) |v| {
        if (v != .string or v.string.len == 0) return reply(req, .bad_request, "text/plain", "id must be a non-empty string\n");
        id = v.string;
    }
    if (id) |s| {
        if (ctx.seen.contains(s)) return reply(req, .conflict, "text/plain", "duplicate card id\n");
    }

    // Re-serialize compactly so the record is exactly one line whatever whitespace came in.
    const line = try std.json.Stringify.valueAlloc(ctx.gpa, parsed.value, .{});
    defer ctx.gpa.free(line);

    appendLine(ctx, line) catch |err| {
        std.debug.print("append failed: {s}\n", .{@errorName(err)});
        return reply(req, .internal_server_error, "text/plain", "could not write\n");
    };
    if (id) |s| try remember(ctx, s);
    return reply(req, .ok, "application/json", "{\"ok\":true}\n");
}

fn appendLine(ctx: *Ctx, line: []const u8) !void {
    const io = ctx.io;
    const cwd = Io.Dir.cwd();
    const file = try cwd.createFile(io, ctx.labels_path, .{ .truncate = false, .read = true });
    defer file.close(io);
    const end = try file.length(io);
    const out = try ctx.gpa.alloc(u8, line.len + 1);
    defer ctx.gpa.free(out);
    @memcpy(out[0..line.len], line);
    out[line.len] = '\n';
    try file.writePositionalAll(io, out, end);
}
