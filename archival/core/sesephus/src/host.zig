const std = @import("std");
const common = @import("common.zig");
const database = @import("database.zig");
const crypto = @import("crypto.zig");

const ClientConnection = struct {
    client_id: []const u8,
    friendly_name: []const u8,
    stream: std.Io.net.Stream,
    active: bool,
};

const Alarm = struct {
    alarm_id: []const u8,
    client_id: []const u8,
    trigger_time: i64, // Unix epoch ms
    action: []const u8,
    duration: f32,
    fired: bool,
};

var clients = std.ArrayList(*ClientConnection).empty;
var clients_mutex = std.Io.Mutex.init;

var alarms = std.ArrayList(*Alarm).empty;
var alarms_mutex = std.Io.Mutex.init;

var vault_key: [32]u8 = undefined;
var vault_path: []const u8 = "V:\\sesephus_vault.db";
var db_write_mutex = std.Io.Mutex.init;

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const args = try init.minimal.args.toSlice(init.arena.allocator());

    var read_mode = false;
    var extract_index: ?usize = null;
    var extract_out_path: ?[]const u8 = null;

    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        if (std.mem.eql(u8, args[i], "--read-vault")) {
            read_mode = true;
        } else if (std.mem.eql(u8, args[i], "--vault")) {
            if (i + 1 < args.len) {
                vault_path = args[i + 1];
                i += 1;
            }
        } else if (std.mem.eql(u8, args[i], "--extract")) {
            if (i + 2 >= args.len) {
                std.debug.print("Usage: host.exe --read-vault --extract <index> <out_path.wav>\n", .{});
                return;
            }
            extract_index = try std.fmt.parseInt(usize, args[i + 1], 10);
            extract_out_path = args[i + 2];
            read_mode = true;
            i += 2;
        }
    }

    if (read_mode) {
        try runReadVault(allocator, extract_index, extract_out_path, io);
        return;
    }

    // Interactive Server Mode
    std.debug.print("==================================================\n", .{});
    std.debug.print("      SESEPHUS HOST DAEMON & VAULT ENGINE         \n", .{});
    std.debug.print("==================================================\n", .{});

    // Setup vault database using static secure password to bypass interactive prompt
    const password = "sesephus_default_vault_secure_password_string_2026";

    // Initialize database if not exists
    const exists = if (std.fs.path.isAbsolute(vault_path)) blk: {
        const file = std.Io.Dir.openFileAbsolute(io, vault_path, .{ .mode = .read_only }) catch break :blk false;
        file.close(io);
        break :blk true;
    } else blk: {
        const cwd = std.Io.Dir.cwd();
        _ = cwd.access(io, vault_path, .{}) catch break :blk false;
        break :blk true;
    };

    if (!exists) {
        std.debug.print("[Vault] Database not found. Creating new encrypted database: {s}...\n", .{vault_path});
        try database.initNewDatabase(vault_path, password, io);
    }

    // Open/Validate database
    database.openDatabase(vault_path, password, &vault_key, io) catch |err| {
        std.debug.print("[Vault] Critical Error: Failed to open vault (invalid password or corrupt file). Error: {}\n", .{err});
        return;
    };
    std.debug.print("[Vault] Password verified. Encrypted vault loaded successfully.\n", .{});

    // Start TCP Listener Thread
    const thread = try std.Thread.spawn(.{}, startTcpListener, .{allocator, io});
    thread.detach();

    // Start HTTP Server Thread on port 3000
    const http_thread = try std.Thread.spawn(.{}, startHttpServer, .{allocator, io});
    http_thread.detach();

    // Start Timekeeper Thread
    const timer_thread = try std.Thread.spawn(.{}, startTimekeeper, .{io});
    timer_thread.detach();

    // Command Line Interface Loop
    const stdin_file = std.Io.File.stdin();
    var stdin_buf: [1024]u8 = undefined;
    var stdin_reader = stdin_file.reader(io, &stdin_buf);

    std.debug.print("\nCommands:\n", .{});
    std.debug.print("  status                       - Show status, connected clients, and pending alarms\n", .{});
    std.debug.print("  alarm <id> <sec> <act> <dur> - Schedule alarm (e.g. alarm client-1 5 record_audio 5.0)\n", .{});
    std.debug.print("  exit                         - Shutdown the daemon\n\n", .{});

    // Command Line Interface Loop
    while (true) {
        std.debug.print("sesephus> ", .{});
        if (try stdin_reader.interface.takeDelimiter('\n')) |line| {
            const trimmed = std.mem.trim(u8, line, "\r\n ");
            if (trimmed.len == 0) continue;

            if (std.mem.eql(u8, trimmed, "exit")) {
                std.debug.print("[Host] Shutting down...\n", .{});
                break;
            } else if (std.mem.eql(u8, trimmed, "status")) {
                printStatus(io);
            } else if (std.mem.startsWith(u8, trimmed, "alarm ")) {
                try scheduleAlarmCmd(trimmed, allocator, io);
            } else {
                std.debug.print("Unknown command: {s}\n", .{trimmed});
            }
        }
    }

    // Cleanup memory to prevent memory leaks on exit
    clients_mutex.lockUncancelable(io);
    for (clients.items) |c| {
        allocator.free(c.client_id);
        allocator.free(c.friendly_name);
        allocator.destroy(c);
    }
    clients.deinit(allocator);
    clients_mutex.unlock(io);

    alarms_mutex.lockUncancelable(io);
    for (alarms.items) |a| {
        allocator.free(a.alarm_id);
        allocator.free(a.client_id);
        allocator.free(a.action);
        allocator.destroy(a);
    }
    alarms.deinit(allocator);
    alarms_mutex.unlock(io);
}

fn promptPassword(allocator: std.mem.Allocator, prompt: []const u8, io: std.Io) ![]const u8 {
    const stdout = std.Io.File.stdout();
    try stdout.writeStreamingAll(io, prompt);
    
    const stdin_file = std.Io.File.stdin();
    var stdin_buf: [256]u8 = undefined;
    var stdin_reader = stdin_file.reader(io, &stdin_buf);
    if (try stdin_reader.interface.takeDelimiter('\n')) |line| {
        const password = std.mem.trim(u8, line, "\r\n ");
        return try allocator.dupe(u8, password);
    }
    return error.EmptyPassword;
}

fn runReadVault(allocator: std.mem.Allocator, extract_index: ?usize, extract_out_path: ?[]const u8, io: std.Io) !void {
    std.debug.print("==================================================\n", .{});
    std.debug.print("          SESEPHUS ENCRYPTED VAULT INSPECTOR      \n", .{});
    std.debug.print("==================================================\n", .{});

    const password = "sesephus_default_vault_secure_password_string_2026";

    var key: [32]u8 = undefined;
    database.openDatabase(vault_path, password, &key, io) catch |err| {
        std.debug.print("Failed to open vault: {}\n", .{err});
        return;
    };

    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const records = try database.readAllRecords(vault_path, key, arena.allocator(), io);
    std.debug.print("[Vault] Found {} journal entries.\n\n", .{records.len});

    if (extract_index) |idx| {
        if (idx >= records.len) {
            std.debug.print("Index out of bounds. Max index: {}\n", .{records.len - 1});
            return;
        }
        const record = records[idx];
        const out_path = extract_out_path.?;
        
        std.debug.print("Extracting record {} ({s}) to {s}...\n", .{idx, record.filename, out_path});
        
        // Decode base64 audio data
        const decoder = std.base64.standard.Decoder;
        const decoded_len = try decoder.calcSizeUpperBound(record.audio_data_base64.len);
        const decoded_buf = try allocator.alloc(u8, decoded_len);
        defer allocator.free(decoded_buf);
        
        try decoder.decode(decoded_buf, record.audio_data_base64);
        
        const cwd = std.Io.Dir.cwd();
        const file = try cwd.createFile(io, out_path, .{});
        defer file.close(io);
        try file.writeStreamingAll(io, decoded_buf);
        std.debug.print("WAV file extracted successfully!\n", .{});
    } else {
        for (records, 0..) |record, idx| {
            const time_sec = @divTrunc(record.timestamp, 1000);
            std.debug.print("[{}] Client: {s}\n", .{idx, record.client_id});
            std.debug.print("    Timestamp: {} (Unix Epoch Sec)\n", .{time_sec});
            std.debug.print("    Filename:  {s}\n", .{record.filename});
            if (record.local_path) |lp| {
                std.debug.print("    Local Path: {s}\n", .{lp});
            }
            std.debug.print("    Payload:   {} bytes of base64 data\n\n", .{record.audio_data_base64.len});
        }
    }
}

fn startTcpListener(allocator: std.mem.Allocator, io: std.Io) !void {
    const port = 5000;
    const address = try std.Io.net.IpAddress.parseIp4("0.0.0.0", port);
    var server = try address.listen(io, .{ .reuse_address = true });
    defer server.deinit(io);

    std.debug.print("[Host] Listening for client devices on port {}...\n", .{port});

    while (true) {
        const stream = try server.accept(io);
        errdefer stream.close(io);

        // Spawn a thread to handle this connection
        const t = try std.Thread.spawn(.{}, handleClient, .{stream, allocator, io});
        t.detach();
    }
}

fn handleClient(stream: std.Io.net.Stream, allocator: std.mem.Allocator, io: std.Io) void {
    var client_conn: ?*ClientConnection = null;
    defer {
        if (client_conn) |c| {
            clients_mutex.lockUncancelable(io);
            c.active = false;
            clients_mutex.unlock(io);
            std.debug.print("\n[Host] Client disconnected: {s}\n", .{c.client_id});
        }
        stream.close(io);
    }

    // First, read registration message
    const register_msg = common.readMessage(stream, allocator, io) catch |err| {
        std.debug.print("Error registering client: {}\n", .{err});
        return;
    };
    
    {
        const msg = register_msg.parsed.value;
        if (!std.mem.eql(u8, msg.type, "RegisterClient")) {
            std.debug.print("Expected RegisterClient message, got: {s}\n", .{msg.type});
            register_msg.deinit();
            return;
        }

        const cid = msg.client_id orelse "unknown-client";
        const fname = msg.friendly_name orelse "Unknown Device";

        clients_mutex.lockUncancelable(io);
        defer clients_mutex.unlock(io);

        // Check if client is already in the list
        var found: ?*ClientConnection = null;
        for (clients.items) |c| {
            if (std.mem.eql(u8, c.client_id, cid)) {
                found = c;
                break;
            }
        }

        if (found) |c| {
            if (c.active) {
                c.stream.close(io); // Close old active stream
            }
            c.stream = stream;
            c.active = true;
            client_conn = c;
            std.debug.print("\n[Host] Client reconnected: {s} ({s})\n", .{c.friendly_name, c.client_id});
        } else {
            const new_c = allocator.create(ClientConnection) catch return;
            new_c.* = ClientConnection{
                .client_id = allocator.dupe(u8, cid) catch return,
                .friendly_name = allocator.dupe(u8, fname) catch return,
                .stream = stream,
                .active = true,
            };
            clients.append(allocator, new_c) catch return;
            client_conn = new_c;
            std.debug.print("\n[Host] Client registered: {s} ({s})\n", .{new_c.friendly_name, new_c.client_id});
        }
    }
    register_msg.deinit();

    // Send initial time sync
    const sync_msg = common.Message{
        .type = "TimeSync",
        .server_time = common.getMilliTimestamp(),
        .client_offset = 0,
    };
    common.writeMessage(stream, sync_msg, allocator, io) catch |err| {
        std.debug.print("Failed to write time sync: {}\n", .{err});
        return;
    };

    // Client connection read loop
    while (true) {
        const msg_parsed = common.readMessage(stream, allocator, io) catch |err| {
            if (err == error.EndOfStream) break;
            std.debug.print("\n[Host] Read error on client {s}: {}\n", .{client_conn.?.client_id, err});
            break;
        };
        defer msg_parsed.deinit();

        const msg = msg_parsed.parsed.value;
        if (std.mem.eql(u8, msg.type, "AudioUpload")) {
            const cid = client_conn.?.client_id;
            const filename = msg.filename orelse "audio.wav";
            const timestamp = msg.timestamp orelse common.getMilliTimestamp();
            const b64 = msg.audio_data_base64 orelse "";

            std.debug.print("\n[Host] Ingesting audio from {s}: {s} ({} base64 bytes)...\n", .{cid, filename, b64.len});
            
            db_write_mutex.lockUncancelable(io);
            defer db_write_mutex.unlock(io);

            const entry = database.JournalEntry{
                .client_id = cid,
                .timestamp = timestamp,
                .filename = filename,
                .audio_data_base64 = b64,
            };

            database.appendRecord(vault_path, vault_key, entry, allocator, io) catch |db_err| {
                std.debug.print("[Host] Database write failed: {}\n", .{db_err});
                _ = common.writeMessage(stream, .{
                    .type = "StatusResponse",
                    .success = false,
                    .message = "Database write failed",
                }, allocator, io) catch {};
                continue;
            };

            std.debug.print("[Host] Audio ingested successfully into {s}.\n", .{vault_path});
            
            common.writeMessage(stream, .{
                .type = "StatusResponse",
                .success = true,
                .message = "Audio successfully ingested into vault",
            }, allocator, io) catch {};
        } else if (std.mem.eql(u8, msg.type, "LocalRecordStatus")) {
            const cid = client_conn.?.client_id;
            const filename = msg.filename orelse "journal.wav";
            const timestamp = msg.timestamp orelse common.getMilliTimestamp();
            const local_path = msg.local_path orelse "";

            std.debug.print("\n[Host] Logged local recording from {s}: {s} at {s}\n", .{cid, filename, local_path});
            
            db_write_mutex.lockUncancelable(io);
            defer db_write_mutex.unlock(io);

            const entry = database.JournalEntry{
                .client_id = cid,
                .timestamp = timestamp,
                .filename = filename,
                .audio_data_base64 = "",
                .local_path = local_path,
            };

            database.appendRecord(vault_path, vault_key, entry, allocator, io) catch |db_err| {
                std.debug.print("[Host] Database write failed: {}\n", .{db_err});
                _ = common.writeMessage(stream, .{
                    .type = "StatusResponse",
                    .success = false,
                    .message = "Database write failed",
                }, allocator, io) catch {};
                continue;
            };

            std.debug.print("[Host] Local journal metadata ingested successfully into {s}.\n", .{vault_path});
            
            // Trigger background transcription sidecar call
            triggerTranscription(cid, local_path, io);

            common.writeMessage(stream, .{
                .type = "StatusResponse",
                .success = true,
                .message = "Local journal metadata logged in host vault",
            }, allocator, io) catch {};
        }
    }
}

fn startTimekeeper(io: std.Io) void {
    while (true) {
        common.sleepMs(1000); // Check every second

        const now = common.getMilliTimestamp();
        alarms_mutex.lockUncancelable(io);
        
        for (alarms.items) |alarm| {
            if (now >= alarm.trigger_time and !alarm.fired) {
                alarm.fired = true;
                
                // Dispatch to client
                clients_mutex.lockUncancelable(io);
                var dispatched = false;
                for (clients.items) |client| {
                    if (client.active and std.mem.eql(u8, client.client_id, alarm.client_id)) {
                        std.debug.print("\n[Host] Triggering alarm {s} on client {s} for action: {s}...\n", .{alarm.alarm_id, client.client_id, alarm.action});
                        const trigger_msg = common.Message{
                            .type = "AlarmTrigger",
                            .alarm_id = alarm.alarm_id,
                            .action = alarm.action,
                            .duration = alarm.duration,
                        };
                        common.writeMessage(client.stream, trigger_msg, std.heap.page_allocator, io) catch |err| {
                            std.debug.print("Failed to dispatch alarm to client: {}\n", .{err});
                        };
                        dispatched = true;
                        break;
                    }
                }
                clients_mutex.unlock(io);

                if (!dispatched) {
                    std.debug.print("\n[Host] Failed to trigger alarm {s}: Client {s} is offline.\n", .{alarm.alarm_id, alarm.client_id});
                }
            }
        }
        alarms_mutex.unlock(io);
    }
}

fn printStatus(io: std.Io) void {
    clients_mutex.lockUncancelable(io);
    defer clients_mutex.unlock(io);
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);

    std.debug.print("\n--- Sesephus Host Status ---\n", .{});
    std.debug.print("Connected Clients:\n", .{});
    var active_count: usize = 0;
    for (clients.items) |c| {
        if (c.active) {
            std.debug.print("  - {s} ({s}) [ONLINE]\n", .{c.friendly_name, c.client_id});
            active_count += 1;
        } else {
            std.debug.print("  - {s} ({s}) [OFFLINE]\n", .{c.friendly_name, c.client_id});
        }
    }
    if (clients.items.len == 0) {
        std.debug.print("  None\n", .{});
    }

    std.debug.print("Scheduled Alarms:\n", .{});
    const now = common.getMilliTimestamp();
    for (alarms.items) |a| {
        const time_diff = @divTrunc(a.trigger_time - now, 1000);
        const status_str = if (a.fired) "FIRED" else if (time_diff < 0) "PENDING (OVERDUE)" else "PENDING";
        std.debug.print("  - ID: {s} | Client: {s} | Action: {s} | Duration: {d:.1}s | Status: {s} (due in {}s)\n", .{
            a.alarm_id, a.client_id, a.action, a.duration, status_str, time_diff,
        });
    }
    if (alarms.items.len == 0) {
        std.debug.print("  None\n", .{});
    }
    std.debug.print("----------------------------\n\n", .{});
}

fn scheduleAlarmCmd(cmd: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    // Expected format: alarm <client_id> <seconds_from_now> <action> <duration>
    // e.g. alarm client-1 5 record_audio 5.0
    var it = std.mem.tokenizeAny(u8, cmd, " ");
    _ = it.next(); // skip "alarm"
    
    const client_id = it.next() orelse {
        std.debug.print("Usage: alarm <client_id> <sec_from_now> <action> <duration>\n", .{});
        return;
    };
    
    const sec_str = it.next() orelse {
        std.debug.print("Usage: alarm <client_id> <sec_from_now> <action> <duration>\n", .{});
        return;
    };
    
    const action = it.next() orelse {
        std.debug.print("Usage: alarm <client_id> <sec_from_now> <action> <duration>\n", .{});
        return;
    };
    
    const dur_str = it.next() orelse "5.0";

    const seconds = std.fmt.parseInt(i64, sec_str, 10) catch {
        std.debug.print("Invalid seconds format: {s}\n", .{sec_str});
        return;
    };
    const duration = std.fmt.parseFloat(f32, dur_str) catch {
        std.debug.print("Invalid duration format: {s}\n", .{dur_str});
        return;
    };

    var id_bytes: [16]u8 = undefined;
    crypto.getRandomBytes(&id_bytes);
    const id_hex = std.fmt.bytesToHex(id_bytes, .lower);

    const alarm = try allocator.create(Alarm);
    alarm.* = Alarm{
        .alarm_id = try allocator.dupe(u8, id_hex[0..8]),
        .client_id = try allocator.dupe(u8, client_id),
        .trigger_time = common.getMilliTimestamp() + (seconds * 1000),
        .action = try allocator.dupe(u8, action),
        .duration = duration,
        .fired = false,
    };

    alarms_mutex.lockUncancelable(io);
    try alarms.append(allocator, alarm);
    alarms_mutex.unlock(io);

    std.debug.print("Scheduled alarm {s} for client {s} in {} seconds.\n", .{alarm.alarm_id, client_id, seconds});
}

fn startHttpServer(allocator: std.mem.Allocator, io: std.Io) !void {
    const port = 3000;
    const address = try std.Io.net.IpAddress.parseIp4("0.0.0.0", port);
    var server = try address.listen(io, .{ .reuse_address = true });
    defer server.deinit(io);
    
    std.debug.print("[HTTP] Dashboard Web UI listening at http://localhost:{}/\n", .{port});
    
    while (true) {
        const stream = try server.accept(io);
        const t = try std.Thread.spawn(.{}, handleHttpRequest, .{stream, allocator, io});
        t.detach();
    }
}

fn handleHttpRequest(stream: std.Io.net.Stream, allocator: std.mem.Allocator, io: std.Io) void {
    defer stream.close(io);
    
    var buf: [4096]u8 = undefined;
    var bytes_read: usize = 0;
    
    var read_buf: [1024]u8 = undefined;
    var stream_reader = stream.reader(io, &read_buf);
    
    while (true) {
        var byte_buf: [1]u8 = undefined;
        stream_reader.interface.readSliceAll(&byte_buf) catch return;
        buf[bytes_read] = byte_buf[0];
        bytes_read += 1;
        if (std.mem.indexOf(u8, buf[0..bytes_read], "\r\n\r\n") != null) break;
        if (bytes_read >= buf.len) break;
    }
    
    const request = buf[0..bytes_read];
    var it = std.mem.tokenizeAny(u8, request, "\r\n");
    const first_line = it.next() orelse return;
    var req_it = std.mem.tokenizeAny(u8, first_line, " ");
    const method = req_it.next() orelse return;
    const path = req_it.next() orelse return;
    
    if (std.mem.eql(u8, method, "GET") and std.mem.eql(u8, path, "/")) {
        sendHtmlResponse(stream, getDashboardHtml(), io) catch {};
    } else if (std.mem.eql(u8, method, "GET") and std.mem.eql(u8, path, "/api/status")) {
        sendStatusJsonResponse(stream, allocator, io) catch {};
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm")) {
        handlePostAlarm(stream, request, allocator, io) catch {};
    } else {
        const reply = 
            "HTTP/1.1 404 Not Found\r\n" ++
            "Content-Length: 9\r\n" ++
            "Connection: close\r\n\r\n" ++
            "Not Found";
        var write_buf: [256]u8 = undefined;
        var stream_writer = stream.writer(io, &write_buf);
        stream_writer.interface.writeAll(reply) catch {};
        stream_writer.interface.flush() catch {};
    }
}

fn sendHtmlResponse(stream: std.Io.net.Stream, html: []const u8, io: std.Io) !void {
    var header_buf: [256]u8 = undefined;
    const header = try std.fmt.bufPrint(&header_buf, 
        "HTTP/1.1 200 OK\r\n" ++
        "Content-Type: text/html\r\n" ++
        "Content-Length: {}\r\n" ++
        "Connection: close\r\n\r\n", .{html.len});
    
    var write_buf: [1024]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    try stream_writer.interface.writeAll(header);
    try stream_writer.interface.writeAll(html);
    try stream_writer.interface.flush();
}

fn sendStatusJsonResponse(stream: std.Io.net.Stream, allocator: std.mem.Allocator, io: std.Io) !void {
    clients_mutex.lockUncancelable(io);
    defer clients_mutex.unlock(io);
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    var string = std.ArrayList(u8).empty;
    defer string.deinit(allocator);
    
    var aw: std.Io.Writer.Allocating = .fromArrayList(allocator, &string);
    const writer = &aw.writer;
    
    try writer.writeAll("{\"clients\":[");
    for (clients.items, 0..) |c, idx| {
        if (idx > 0) try writer.writeAll(",");
        try std.json.Stringify.value(struct {
            client_id: []const u8,
            friendly_name: []const u8,
            active: bool,
        }{
            .client_id = c.client_id,
            .friendly_name = c.friendly_name,
            .active = c.active,
        }, .{}, writer);
    }
    try writer.writeAll("],\"alarms\":[");
    for (alarms.items, 0..) |a, idx| {
        if (idx > 0) try writer.writeAll(",");
        try std.json.Stringify.value(struct {
            alarm_id: []const u8,
            client_id: []const u8,
            trigger_time: i64,
            action: []const u8,
            duration: f32,
            fired: bool,
        }{
            .alarm_id = a.alarm_id,
            .client_id = a.client_id,
            .trigger_time = a.trigger_time,
            .action = a.action,
            .duration = a.duration,
            .fired = a.fired,
        }, .{}, writer);
    }
    try writer.writeAll("]}");
    
    string = aw.toArrayList();
    
    var header_buf: [256]u8 = undefined;
    const header = try std.fmt.bufPrint(&header_buf, 
        "HTTP/1.1 200 OK\r\n" ++
        "Content-Type: application/json\r\n" ++
        "Content-Length: {}\r\n" ++
        "Access-Control-Allow-Origin: *\r\n" ++
        "Connection: close\r\n\r\n", .{string.items.len});
        
    var write_buf: [1024]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    try stream_writer.interface.writeAll(header);
    try stream_writer.interface.writeAll(string.items);
    try stream_writer.interface.flush();
}

const AlarmPost = struct {
    client_id: []const u8,
    seconds: i64,
    action: []const u8,
    duration: f32,
};

fn handlePostAlarm(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(AlarmPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    const client_id = parsed.value.client_id;
    const seconds = parsed.value.seconds;
    const action = parsed.value.action;
    const duration = parsed.value.duration;
    
    var id_bytes: [16]u8 = undefined;
    crypto.getRandomBytes(&id_bytes);
    const id_hex = std.fmt.bytesToHex(id_bytes, .lower);
    
    const alarm = try allocator.create(Alarm);
    alarm.* = Alarm{
        .alarm_id = try allocator.dupe(u8, id_hex[0..8]),
        .client_id = try allocator.dupe(u8, client_id),
        .trigger_time = common.getMilliTimestamp() + (seconds * 1000),
        .action = try allocator.dupe(u8, action),
        .duration = duration,
        .fired = false,
    };
    
    alarms_mutex.lockUncancelable(io);
    try alarms.append(allocator, alarm);
    alarms_mutex.unlock(io);
    
    std.debug.print("[HTTP] Alarm {s} scheduled for client {s} via Web UI.\n", .{alarm.alarm_id, client_id});
    
    const reply = 
        "HTTP/1.1 200 OK\r\n" ++
        "Content-Type: application/json\r\n" ++
        "Content-Length: 16\r\n" ++
        "Access-Control-Allow-Origin: *\r\n" ++
        "Connection: close\r\n\r\n" ++
        "{\"success\":true}";
        
    var write_buf: [256]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    try stream_writer.interface.writeAll(reply);
    try stream_writer.interface.flush();
}

fn getDashboardHtml() []const u8 {
    return @embedFile("dashboard.html");
}

fn triggerTranscription(client_id: []const u8, wav_path: []const u8, io: std.Io) void {
    const port = 3001;
    const address = std.Io.net.IpAddress.parseIp4("127.0.0.1", port) catch {
        std.debug.print("[Host] Invalid sidecar IP/port.\n", .{});
        return;
    };
    var stream = address.connect(io, .{ .mode = .stream }) catch |err| {
        std.debug.print("[Host] Failed to connect to transcription sidecar: {}\n", .{err});
        return;
    };
    defer stream.close(io);

    // Sanitize path separators from Windows '\\' to '/' for clean JSON mapping
    var path_clean_buf: [260]u8 = undefined;
    const path_len = @min(wav_path.len, 259);
    @memcpy(path_clean_buf[0..path_len], wav_path[0..path_len]);
    for (path_clean_buf[0..path_len]) |*char| {
        if (char.* == '\\') char.* = '/';
    }
    const clean_path = path_clean_buf[0..path_len];

    var payload_buf: [1024]u8 = undefined;
    const final_payload = std.fmt.bufPrint(&payload_buf, "{{\"wav_path\":\"{s}\",\"client_id\":\"{s}\"}}", .{clean_path, client_id}) catch return;

    var header_buf: [1024]u8 = undefined;
    const headers = std.fmt.bufPrint(&header_buf, 
        "POST /api/transcribe HTTP/1.1\r\n" ++
        "Host: localhost:3001\r\n" ++
        "Content-Type: application/json\r\n" ++
        "Content-Length: {}\r\n" ++
        "Connection: close\r\n\r\n", .{final_payload.len}) catch return;

    var write_buf: [1024]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    stream_writer.interface.writeAll(headers) catch return;
    stream_writer.interface.writeAll(final_payload) catch return;
    stream_writer.interface.flush() catch return;

    std.debug.print("[Host] Triggered transcription request to sidecar for {s}.\n", .{clean_path});
}
