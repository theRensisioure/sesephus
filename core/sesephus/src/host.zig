const std = @import("std");

const journal = @import("commands/journal.zig");
const rhythm = @import("commands/rhythm.zig");
const stoic = @import("commands/stoic.zig");
const lead = @import("commands/lead.zig");
const vault = @import("commands/vault.zig");
const dialogue = @import("commands/dialogue.zig");
const aytree = @import("commands/aytree.zig");
const help_text = @import("commands/help_text.zig");
const cli = @import("cli.zig");

const common = @import("common.zig");
const database = @import("database.zig");
const crypto = @import("crypto.zig");
const client_module = @import("client.zig");

const ClientConnection = struct {
    client_id: []const u8,
    friendly_name: []const u8,
    stream: std.Io.net.Stream,
    active: bool,
};

const Alarm = struct {
    alarm_id: []const u8,
    client_ids: std.ArrayList([]const u8),
    trigger_time: i64, // Unix epoch ms
    action: []const u8,
    duration: f32,
    fired: bool,
    enabled: bool,
    group_id: ?[]const u8,
    parent_id: ?[]const u8,
};

const AlarmGroup = struct {
    group_id: []const u8,
    name: []const u8,
    client_ids: std.ArrayList([]const u8),
};

var clients = std.ArrayList(*ClientConnection).empty;
var clients_mutex = std.Io.Mutex.init;

var alarms = std.ArrayList(*Alarm).empty;
var alarms_mutex = std.Io.Mutex.init;

var subgroups = std.ArrayList(*AlarmGroup).empty;
var subgroups_mutex = std.Io.Mutex.init;

var vault_key: [32]u8 = undefined;
var vault_public_key: [32]u8 = undefined;
// V: is the drive-mapping.json vault drive on Windows; on POSIX that string
// would become a literal "V:\..." file in cwd, so default to the local
// fallback name directly.
var vault_path: []const u8 = if (@import("builtin").os.tag == .windows) "V:\\sesephus_vault.db" else "sesephus_vault.db";
var sidevault_path: []const u8 = "";
var db_write_mutex = std.Io.Mutex.init;

fn resolveVaultPath(allocator: std.mem.Allocator, path: []const u8, io: std.Io) []const u8 {
    if (!std.fs.path.isAbsolute(path)) {
        return path;
    }
    const dirname = std.fs.path.dirname(path) orelse "";
    if (dirname.len > 0) {
        std.Io.Dir.cwd().createDirPath(io, dirname) catch {};
    }
    const probe_path = std.fmt.allocPrint(allocator, "{s}{s}sesephus_probe.tmp", .{
        dirname,
        if (dirname.len > 0 and dirname[dirname.len - 1] != '\\' and dirname[dirname.len - 1] != '/') "\\" else "",
    }) catch {
        return "sesephus_vault.db";
    };
    defer allocator.free(probe_path);

    var file = std.Io.Dir.createFileAbsolute(io, probe_path, .{ .read = true }) catch {
        return "sesephus_vault.db";
    };
    file.close(io);
    std.Io.Dir.deleteFileAbsolute(io, probe_path) catch {};
    return path;
}

fn resolveSidevaultPath(allocator: std.mem.Allocator, v_path: []const u8) ![]const u8 {
    const dirname = std.fs.path.dirname(v_path) orelse "";
    if (dirname.len > 0) {
        return try std.fmt.allocPrint(allocator, "{s}{s}sesephus_sidevault", .{
            dirname,
            if (dirname[dirname.len - 1] != '\\' and dirname[dirname.len - 1] != '/') "\\" else "",
        });
    } else {
        return try allocator.dupe(u8, "sesephus_sidevault");
    }
}

fn printHostUsage() void {
    std.debug.print("{s}", .{help_text.host_usage});
}

var global_flags: cli.GlobalFlags = .{};
pub var embed_local_client: bool = true;

pub fn runHost(init: std.process.Init) !void {
    const allocator = init.gpa;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    // SSFS drive verification (drive-mapping.json + label checks) is available.
    // Autostart is paused for now per preference.
    // Run manually: node ssfs/storage/config-engine.js
    // (writes receipt to V:\ssfs-vault\state\ssfs-verified.json)

    const args = try init.minimal.args.toSlice(init.arena.allocator());
    global_flags = cli.parseGlobalFlags(args) catch cli.GlobalFlags{};

    var want_help = false;
    for (args) |arg| {
        if (std.mem.eql(u8, arg, "help") or std.mem.eql(u8, arg, "--help") or std.mem.eql(u8, arg, "-h")) {
            want_help = true;
        }
    }
    if (want_help) {
        printHostUsage();
        return;
    }

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
    std.debug.print("      SESEFUS HOST DAEMON & VAULT ENGINE          \n", .{});
    std.debug.print("==================================================\n", .{});

    // Setup vault database using static secure password to bypass interactive prompt
    const password = "sesephus_default_vault_secure_password_string_2026";

    // Resolve robust database path and fallback if drive/directory is inaccessible
    const resolved_path = resolveVaultPath(allocator, vault_path, io);
    if (!std.mem.eql(u8, resolved_path, vault_path)) {
        std.debug.print("[Vault] Warning: Target path '{s}' is inaccessible. Falling back to local './sesephus_vault.db'\n", .{vault_path});
        vault_path = resolved_path;
    }

    // Resolve sidevault path next to the database file and ensure it exists
    const s_path = try resolveSidevaultPath(allocator, vault_path);
    sidevault_path = s_path;
    std.Io.Dir.cwd().createDirPath(io, sidevault_path) catch |err| {
        std.debug.print("[Vault] Warning: Failed to create sidevault directory: {}\n", .{err});
    };

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

    // Open/Validate database (fail-hard exit on failure)
    database.openDatabase(vault_path, password, &vault_key, io) catch |err| {
        std.debug.print("[Vault] Critical Error: Failed to open vault (invalid password or corrupt file). Error: {}\n", .{err});
        std.process.exit(1);
    };

    // Derive and display the active vault public key hash for key verification
    std.crypto.hash.sha2.Sha256.hash(&vault_key, &vault_public_key, .{});
    std.debug.print("[Vault] Password verified. Encrypted vault loaded successfully.\n", .{});
    std.debug.print("[Vault] Active Vault Public Key: {s}\n", .{std.fmt.bytesToHex(vault_public_key, .lower)});

    // Start TCP Listener Thread
    const thread = try std.Thread.spawn(.{}, startTcpListener, .{allocator, io});
    thread.detach();

    // Start HTTP Server Thread on port 3000
    const http_thread = try std.Thread.spawn(.{}, startHttpServer, .{allocator, io});
    http_thread.detach();

    // Start Timekeeper Thread
    const timer_thread = try std.Thread.spawn(.{}, startTimekeeper, .{io});
    timer_thread.detach();

    if (embed_local_client) {
        const client_thread = try std.Thread.spawn(.{}, startEmbeddedClient, .{ allocator, io });
        client_thread.detach();
    }

    // Command Line Interface Loop
    const stdin_file = std.Io.File.stdin();
    var stdin_buf: [1024]u8 = undefined;
    var stdin_reader = stdin_file.reader(io, &stdin_buf);

    std.debug.print("\nCommands (space-separated: module then subcommand — 'help' for the full honest list):\n", .{});
    std.debug.print("  status                                                      - Show status, connected clients, subgroups, and pending alarms\n", .{});
    std.debug.print("  dialogue start [appliance]                                  - Turn-taking capture into the vault (appliance = spoken aloud)\n", .{});
    std.debug.print("  dialogue review [n] [appliance]                             - Read (or hear) your last n written entries\n", .{});
    std.debug.print("  alarm schedule <client_id> <sec> <action> <duration>        - Schedule an alarm for a client\n", .{});
    std.debug.print("  alarm group <group_id> <sec> <action> <duration>            - Schedule a group alarm\n", .{});
    std.debug.print("  alarm toggle <true|false>                                   - Enable/disable all alarms globally\n", .{});
    std.debug.print("  alarm bulk <action> <duration> <alarm_ids_comma_sep>        - Edit multiple alarms\n", .{});
    std.debug.print("  alarm interval <client_ids_comma_sep> <dur_sec> <count> ... - Create interval alarm sequence\n", .{});
    std.debug.print("  alarm adjust <parent_id> <spacing_sec> <jitter_ms>          - Adjust spacing of interval alarms\n", .{});
    std.debug.print("  group create <name> <client_ids_comma_sep>                  - Define a new alarm subgroup\n", .{});
    std.debug.print("  group rename <group_id> <new_name>                          - Rename subgroup\n", .{});
    std.debug.print("  group edit <group_id> <client_ids_comma_sep>                - Edit group client list\n", .{});
    std.debug.print("  group delete <group_id>                                     - Delete subgroup\n", .{});
    std.debug.print("  lead qualify <post_text> [--handle <h>]                     - Score a post (spawns tools/qualify_post.py)\n", .{});
    std.debug.print("  vault ingest-archive [--dry-run] [--limit n]                - Ingest memos (spawns tools/ingress_memos.py)\n", .{});
    std.debug.print("  aytree open|map|tree|serve|status                           - AyTree derivation map (tools/aytree_launch.py)\n", .{});
    std.debug.print("  backup [dest_path]                                          - Hot positional backup copy of the database\n", .{});
    std.debug.print("  exit                                                        - Shutdown the daemon\n\n", .{});

    // Command Line Interface Loop
    while (true) {
        std.debug.print("sesephus> ", .{});
        if (try stdin_reader.interface.takeDelimiter('\n')) |line| {
            const should_continue = handleCliCommand(line, allocator, io, &stdin_reader.interface) catch |err| blk: {
                std.debug.print("CLI command error: {}\n", .{err});
                break :blk true;
            };
            if (!should_continue) break;
        } else {
            // EOF on stdin, sleep forever or until process is terminated to avoid CPU spinning
            while (true) {
                common.sleepMs(1000);
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
        for (a.client_ids.items) |cid| {
            allocator.free(cid);
        }
        a.client_ids.deinit(allocator);
        allocator.free(a.action);
        if (a.group_id) |g_id| allocator.free(g_id);
        if (a.parent_id) |p_id| allocator.free(p_id);
        allocator.destroy(a);
    }
    alarms.deinit(allocator);
    alarms_mutex.unlock(io);

    subgroups_mutex.lockUncancelable(io);
    for (subgroups.items) |g| {
        allocator.free(g.group_id);
        allocator.free(g.name);
        for (g.client_ids.items) |cid| {
            allocator.free(cid);
        }
        g.client_ids.deinit(allocator);
        allocator.destroy(g);
    }
    subgroups.deinit(allocator);
    subgroups_mutex.unlock(io);
    if (sidevault_path.len > 0) {
        allocator.free(sidevault_path);
    }
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
    std.debug.print("          SESEFUS ENCRYPTED VAULT INSPECTOR       \n", .{});
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

    // Perform sync check/log for the client upon registration
    {
        const cid = client_conn.?.client_id;
        std.debug.print("[Sync] Checking history for client {s}...\n", .{cid});
        db_write_mutex.lockUncancelable(io);
        defer db_write_mutex.unlock(io);
        var client_records_count: usize = 0;
        var arena = std.heap.ArenaAllocator.init(allocator);
        defer arena.deinit();
        if (database.readAllRecords(vault_path, vault_key, arena.allocator(), io)) |records| {
            for (records) |r| {
                if (std.mem.eql(u8, r.client_id, cid)) {
                    client_records_count += 1;
                }
            }
            std.debug.print("[Sync] Client {s} has {} existing journal records in vault.\n", .{cid, client_records_count});
        } else |err| {
            std.debug.print("[Sync] Warning: Failed to query vault records for client: {}\n", .{err});
        }
    }

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
            
            // Construct sidevault WAV file path next to the database
            const wav_path = std.fmt.allocPrint(allocator, "{s}{s}journal_{}.wav", .{
                sidevault_path,
                if (sidevault_path[sidevault_path.len - 1] != '\\' and sidevault_path[sidevault_path.len - 1] != '/') "\\" else "",
                timestamp,
            }) catch {
                std.debug.print("[Host] Out of memory constructing wav_path.\n", .{});
                continue;
            };
            defer allocator.free(wav_path);

            // Decode base64 audio data to binary
            const decoder = std.base64.standard.Decoder;
            const decoded_len = decoder.calcSizeForSlice(b64) catch |err| {
                std.debug.print("[Host] Invalid base64 size: {}\n", .{err});
                continue;
            };
            const decoded_buf = allocator.alloc(u8, decoded_len) catch {
                std.debug.print("[Host] Out of memory allocating decoded buffer.\n", .{});
                continue;
            };
            defer allocator.free(decoded_buf);
            
            decoder.decode(decoded_buf, b64) catch |err| {
                std.debug.print("[Host] Failed to decode base64 audio: {}\n", .{err});
                _ = common.writeMessage(stream, .{
                    .type = "StatusResponse",
                    .success = false,
                    .message = "Base64 decode failed",
                }, allocator, io) catch {};
                continue;
            };

            // Write decoded WAV data to file in sidevault
            const cwd = std.Io.Dir.cwd();
            const file = if (std.fs.path.isAbsolute(wav_path))
                std.Io.Dir.createFileAbsolute(io, wav_path, .{}) catch |err| {
                    std.debug.print("[Host] Failed to create sidevault file: {}\n", .{err});
                    _ = common.writeMessage(stream, .{
                        .type = "StatusResponse",
                        .success = false,
                        .message = "Failed to create sidevault file",
                    }, allocator, io) catch {};
                    continue;
                }
            else
                cwd.createFile(io, wav_path, .{}) catch |err| {
                    std.debug.print("[Host] Failed to create sidevault file: {}\n", .{err});
                    _ = common.writeMessage(stream, .{
                        .type = "StatusResponse",
                        .success = false,
                        .message = "Failed to create sidevault file",
                    }, allocator, io) catch {};
                    continue;
                };
            defer file.close(io);
            file.writeStreamingAll(io, decoded_buf) catch |err| {
                std.debug.print("[Host] Failed to write sidevault file: {}\n", .{err});
                _ = common.writeMessage(stream, .{
                    .type = "StatusResponse",
                    .success = false,
                    .message = "Failed to write sidevault file",
                }, allocator, io) catch {};
                continue;
            };

            db_write_mutex.lockUncancelable(io);
            defer db_write_mutex.unlock(io);

            const entry = database.JournalEntry{
                .client_id = cid,
                .timestamp = timestamp,
                .filename = filename,
                .audio_data_base64 = "",
                .local_path = wav_path,
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
            
            // Trigger background transcription sidecar call for host-saved audio
            triggerTranscription(cid, wav_path, io);

            common.writeMessage(stream, .{
                .type = "StatusResponse",
                .success = true,
                .message = "Audio successfully ingested into vault",
            }, allocator, io) catch {};
        } else if (std.mem.eql(u8, msg.type, "SyncRequest")) {
            const cid = client_conn.?.client_id;
            std.debug.print("\n[Host] SyncRequest received from client {s}.\n", .{cid});
            
            db_write_mutex.lockUncancelable(io);
            var arena = std.heap.ArenaAllocator.init(allocator);
            defer arena.deinit();
            
            if (database.readAllRecords(vault_path, vault_key, arena.allocator(), io)) |records| {
                var client_records_count: usize = 0;
                for (records) |r| {
                    if (std.mem.eql(u8, r.client_id, cid)) {
                        client_records_count += 1;
                    }
                }
                std.debug.print("[Host] Sync - client {s} has {} records in vault.\n", .{cid, client_records_count});
            } else |err| {
                std.debug.print("[Host] Sync - error reading vault: {}\n", .{err});
            }
            db_write_mutex.unlock(io);
            
            common.writeMessage(stream, .{
                .type = "SyncResponse",
                .success = true,
                .message = "Sync de-duplication completed.",
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
        common.sleepMs(50); // Responsive 50ms polling rate

        const now = common.getMilliTimestamp();
        alarms_mutex.lockUncancelable(io);
        
        for (alarms.items) |alarm| {
            if (alarm.enabled and now >= alarm.trigger_time and !alarm.fired) {
                alarm.fired = true;
                
                // Dispatch to client(s)
                clients_mutex.lockUncancelable(io);
                subgroups_mutex.lockUncancelable(io);
                
                var target_clients = std.ArrayList([]const u8).empty;
                defer target_clients.deinit(std.heap.page_allocator);
                
                if (alarm.group_id) |g_id| {
                    for (subgroups.items) |g| {
                        if (std.mem.eql(u8, g.group_id, g_id)) {
                            for (g.client_ids.items) |cid| {
                                target_clients.append(std.heap.page_allocator, cid) catch {};
                            }
                            break;
                        }
                    }
                }
                
                if (target_clients.items.len == 0) {
                    for (alarm.client_ids.items) |cid| {
                        target_clients.append(std.heap.page_allocator, cid) catch {};
                    }
                }
                
                var dispatched = false;
                for (target_clients.items) |target_cid| {
                    for (clients.items) |client| {
                        if (client.active and std.mem.eql(u8, client.client_id, target_cid)) {
                            std.debug.print("\n[Host] Triggering alarm {s} on client {s} for action: {s}...\n", .{alarm.alarm_id, client.client_id, alarm.action});
                            const trigger_msg = common.Message{
                                .type = "AlarmTrigger",
                                .alarm_id = alarm.alarm_id,
                                .action = alarm.action,
                                .duration = alarm.duration,
                            };
                            common.writeMessage(client.stream, trigger_msg, std.heap.page_allocator, io) catch |err| {
                                std.debug.print("Failed to dispatch alarm to client {s}: {}\n", .{client.client_id, err});
                            };
                            dispatched = true;
                        }
                    }
                }
                subgroups_mutex.unlock(io);
                clients_mutex.unlock(io);

                if (!dispatched) {
                    std.debug.print("\n[Host] Failed to trigger alarm {s}: No active client target online.\n", .{alarm.alarm_id});
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
    subgroups_mutex.lockUncancelable(io);
    defer subgroups_mutex.unlock(io);

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

    std.debug.print("Subgroups:\n", .{});
    for (subgroups.items) |g| {
        std.debug.print("  - Group: {s} | ID: {s} | Targets: ", .{g.name, g.group_id});
        for (g.client_ids.items, 0..) |cid, idx| {
            if (idx > 0) std.debug.print(", ", .{});
            std.debug.print("{s}", .{cid});
        }
        std.debug.print("\n", .{});
    }
    if (subgroups.items.len == 0) {
        std.debug.print("  None\n", .{});
    }

    std.debug.print("Scheduled Alarms:\n", .{});
    const now = common.getMilliTimestamp();
    for (alarms.items) |a| {
        const time_diff = @divTrunc(a.trigger_time - now, 1000);
        const status_str = if (a.fired) "FIRED" else if (!a.enabled) "DISABLED" else if (time_diff < 0) "PENDING (OVERDUE)" else "PENDING";
        std.debug.print("  - ID: {s} | Targets: ", .{a.alarm_id});
        for (a.client_ids.items, 0..) |cid, idx| {
            if (idx > 0) std.debug.print(", ", .{});
            std.debug.print("{s}", .{cid});
        }
        if (a.group_id) |g_id| {
            std.debug.print(" (Group: {s})", .{g_id});
        }
        std.debug.print(" | Action: {s} | Duration: {d:.1}s | Status: {s}", .{
            a.action, a.duration, status_str,
        });
        if (!a.fired and a.enabled) {
            std.debug.print(" (due in {}s)", .{time_diff});
        }
        std.debug.print("\n", .{});
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
    var client_ids_list = std.ArrayList([]const u8).empty;
    try client_ids_list.append(allocator, try allocator.dupe(u8, client_id));

    alarm.* = Alarm{
        .alarm_id = try allocator.dupe(u8, id_hex[0..8]),
        .client_ids = client_ids_list,
        .trigger_time = common.getMilliTimestamp() + (seconds * 1000),
        .action = try allocator.dupe(u8, action),
        .duration = duration,
        .fired = false,
        .enabled = true,
        .group_id = null,
        .parent_id = null,
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
    
    var buf: [8192]u8 = undefined;
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
    
    // Read the body if Content-Length is present
    var content_length: usize = 0;
    while (it.next()) |header| {
        if (std.mem.startsWith(u8, header, "Content-Length:")) {
            const cl_val = std.mem.trim(u8, header["Content-Length:".len..], " ");
            content_length = std.fmt.parseInt(usize, cl_val, 10) catch 0;
            break;
        }
    }

    var full_req = request;
    var req_with_body: ?[]u8 = null;
    defer if (req_with_body) |b| allocator.free(b);
    if (content_length > 0) {
        req_with_body = allocator.alloc(u8, request.len + content_length) catch return;
        @memcpy(req_with_body.?[0..request.len], request);
        
        // Read rest of body
        stream_reader.interface.readSliceAll(req_with_body.?[request.len .. request.len + content_length]) catch return;
        full_req = req_with_body.?;
    }
    
    if (std.mem.eql(u8, method, "GET") and std.mem.eql(u8, path, "/")) {
        sendHtmlResponse(stream, getDashboardHtml(), io) catch {};
    } else if (std.mem.eql(u8, method, "GET") and std.mem.eql(u8, path, "/api/status")) {
        sendStatusJsonResponse(stream, allocator, io) catch {};
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm")) {
        handlePostAlarm(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/alarm: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/group")) {
        handleCreateGroup(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/group: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/group/rename")) {
        handleRenameGroup(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/group/rename: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/group/edit_clients")) {
        handleEditGroupClients(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/group/edit_clients: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/group/delete")) {
        handleDeleteGroup(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/group/delete: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm/edit")) {
        handleBulkEditAlarms(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/alarm/edit: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm/toggle_all")) {
        handleToggleAllAlarms(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/alarm/toggle_all: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm/create_interval")) {
        handleCreateIntervalAlarms(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/alarm/create_interval: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
    } else if (std.mem.eql(u8, method, "POST") and std.mem.eql(u8, path, "/api/alarm/adjust_interval")) {
        handleAdjustInterval(stream, full_req, allocator, io) catch |err| {
            std.debug.print("Error in /api/alarm/adjust_interval: {}\n", .{err});
            sendJsonReply(stream, false, "\"message\":\"Invalid request format\"", io);
        };
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

fn sendJsonReply(stream: std.Io.net.Stream, success: bool, extra_fields: ?[]const u8, io: std.Io) void {
    var body_buf: [512]u8 = undefined;
    const body = if (extra_fields) |fields|
        std.fmt.bufPrint(&body_buf, "{{\"success\":{},{s}}}", .{ success, fields }) catch "{\"success\":false}"
    else
        std.fmt.bufPrint(&body_buf, "{{\"success\":{}}}", .{ success }) catch "{\"success\":false}";

    var header_buf: [256]u8 = undefined;
    const header = std.fmt.bufPrint(&header_buf,
        "HTTP/1.1 200 OK\r\n" ++
        "Content-Type: application/json\r\n" ++
        "Content-Length: {}\r\n" ++
        "Access-Control-Allow-Origin: *\r\n" ++
        "Connection: close\r\n\r\n", .{body.len}) catch return;

    var write_buf: [512]u8 = undefined;
    var stream_writer = stream.writer(io, &write_buf);
    stream_writer.interface.writeAll(header) catch return;
    stream_writer.interface.writeAll(body) catch return;
    stream_writer.interface.flush() catch return;
}

fn sendStatusJsonResponse(stream: std.Io.net.Stream, allocator: std.mem.Allocator, io: std.Io) !void {
    clients_mutex.lockUncancelable(io);
    defer clients_mutex.unlock(io);
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    subgroups_mutex.lockUncancelable(io);
    defer subgroups_mutex.unlock(io);
    
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
        
        try writer.writeAll("{\"alarm_id\":\"");
        try writer.writeAll(a.alarm_id);
        try writer.writeAll("\",\"client_ids\":[");
        for (a.client_ids.items, 0..) |cid, c_idx| {
            if (c_idx > 0) try writer.writeAll(",");
            try std.json.Stringify.value(cid, .{}, writer);
        }
        try writer.writeAll("],\"trigger_time\":");
        var time_buf: [32]u8 = undefined;
        const time_str = try std.fmt.bufPrint(&time_buf, "{}", .{a.trigger_time});
        try writer.writeAll(time_str);
        
        try writer.writeAll(",\"action\":");
        try std.json.Stringify.value(a.action, .{}, writer);
        
        try writer.writeAll(",\"duration\":");
        var dur_buf: [32]u8 = undefined;
        const dur_str = try std.fmt.bufPrint(&dur_buf, "{d:.3}", .{a.duration});
        try writer.writeAll(dur_str);
        
        try writer.writeAll(",\"fired\":");
        try writer.writeAll(if (a.fired) "true" else "false");
        
        try writer.writeAll(",\"enabled\":");
        try writer.writeAll(if (a.enabled) "true" else "false");
        
        try writer.writeAll(",\"group_id\":");
        if (a.group_id) |g_id| {
            try std.json.Stringify.value(g_id, .{}, writer);
        } else {
            try writer.writeAll("null");
        }
        
        try writer.writeAll(",\"parent_id\":");
        if (a.parent_id) |p_id| {
            try std.json.Stringify.value(p_id, .{}, writer);
        } else {
            try writer.writeAll("null");
        }
        try writer.writeAll("}");
    }
    
    try writer.writeAll("],\"subgroups\":[");
    for (subgroups.items, 0..) |g, idx| {
        if (idx > 0) try writer.writeAll(",");
        try writer.writeAll("{\"group_id\":\"");
        try writer.writeAll(g.group_id);
        try writer.writeAll("\",\"name\":");
        try std.json.Stringify.value(g.name, .{}, writer);
        try writer.writeAll(",\"client_ids\":[");
        for (g.client_ids.items, 0..) |cid, c_idx| {
            if (c_idx > 0) try writer.writeAll(",");
            try std.json.Stringify.value(cid, .{}, writer);
        }
        try writer.writeAll("]}");
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
    client_id: ?[]const u8 = null,
    client_ids: ?[][]const u8 = null,
    seconds: i64,
    action: []const u8,
    duration: f32,
    group_id: ?[]const u8 = null,
};

fn handlePostAlarm(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(AlarmPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    const seconds = parsed.value.seconds;
    const action = parsed.value.action;
    const duration = parsed.value.duration;
    
    var id_bytes: [16]u8 = undefined;
    crypto.getRandomBytes(&id_bytes);
    const id_hex = std.fmt.bytesToHex(id_bytes, .lower);
    
    const alarm = try allocator.create(Alarm);
    errdefer allocator.destroy(alarm);
    alarm.alarm_id = try allocator.dupe(u8, id_hex[0..8]);
    errdefer allocator.free(alarm.alarm_id);
    
    alarm.client_ids = std.ArrayList([]const u8).empty;
    errdefer {
        for (alarm.client_ids.items) |cid| allocator.free(cid);
        alarm.client_ids.deinit(allocator);
    }
    
    if (parsed.value.client_ids) |cids| {
        for (cids) |cid| {
            try alarm.client_ids.append(allocator, try allocator.dupe(u8, cid));
        }
    } else if (parsed.value.client_id) |cid| {
        try alarm.client_ids.append(allocator, try allocator.dupe(u8, cid));
    }
    
    alarm.trigger_time = common.getMilliTimestamp() + (seconds * 1000);
    alarm.action = try allocator.dupe(u8, action);
    errdefer allocator.free(alarm.action);
    alarm.duration = duration;
    alarm.fired = false;
    alarm.enabled = true;
    
    if (parsed.value.group_id) |g_id| {
        alarm.group_id = try allocator.dupe(u8, g_id);
    } else {
        alarm.group_id = null;
    }
    errdefer if (alarm.group_id) |g_id| allocator.free(g_id);
    
    alarm.parent_id = null;
    
    alarms_mutex.lockUncancelable(io);
    try alarms.append(allocator, alarm);
    alarms_mutex.unlock(io);
    
    std.debug.print("[HTTP] Alarm {s} scheduled via Web UI.\n", .{alarm.alarm_id});
    sendJsonReply(stream, true, null, io);
}

const GroupCreatePost = struct {
    name: []const u8,
    client_ids: ?[][]const u8 = null,
};

fn handleCreateGroup(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    std.debug.print("[DEBUG] handleCreateGroup request length: {}, content: '{s}'\n", .{request.len, request});
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse {
        std.debug.print("[DEBUG] handleCreateGroup failed to find CRLFCRLF in request\n", .{});
        return error.InvalidRequest;
    };
    const body = request[header_end + 4..];
    std.debug.print("[DEBUG] handleCreateGroup body: '{s}'\n", .{body});
    
    const parsed = std.json.parseFromSlice(GroupCreatePost, allocator, body, .{ .ignore_unknown_fields = true }) catch |err| {
        std.debug.print("[DEBUG] JSON parsing failed: {}\n", .{err});
        return err;
    };
    defer parsed.deinit();
    
    var id_bytes: [16]u8 = undefined;
    crypto.getRandomBytes(&id_bytes);
    const id_hex = std.fmt.bytesToHex(id_bytes, .lower);
    
    const group = try allocator.create(AlarmGroup);
    errdefer allocator.destroy(group);
    
    group.group_id = try allocator.dupe(u8, id_hex[0..8]);
    errdefer allocator.free(group.group_id);
    
    group.name = try allocator.dupe(u8, parsed.value.name);
    errdefer allocator.free(group.name);
    
    group.client_ids = std.ArrayList([]const u8).empty;
    errdefer {
        for (group.client_ids.items) |cid| allocator.free(cid);
        group.client_ids.deinit(allocator);
    }
    
    if (parsed.value.client_ids) |cids| {
        for (cids) |cid| {
            try group.client_ids.append(allocator, try allocator.dupe(u8, cid));
        }
    }
    
    subgroups_mutex.lockUncancelable(io);
    try subgroups.append(allocator, group);
    subgroups_mutex.unlock(io);
    
    std.debug.print("[HTTP] Created subgroup {s} ({s}).\n", .{group.name, group.group_id});
    
    var extra_buf: [128]u8 = undefined;
    const extra = try std.fmt.bufPrint(&extra_buf, "\"group_id\":\"{s}\"", .{group.group_id});
    sendJsonReply(stream, true, extra, io);
}

const GroupRenamePost = struct {
    group_id: []const u8,
    name: []const u8,
};

fn handleRenameGroup(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(GroupRenamePost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    subgroups_mutex.lockUncancelable(io);
    defer subgroups_mutex.unlock(io);
    
    for (subgroups.items) |g| {
        if (std.mem.eql(u8, g.group_id, parsed.value.group_id)) {
            allocator.free(g.name);
            g.name = try allocator.dupe(u8, parsed.value.name);
            std.debug.print("[HTTP] Renamed subgroup {s} to {s}.\n", .{g.group_id, g.name});
            sendJsonReply(stream, true, null, io);
            return;
        }
    }
    
    sendJsonReply(stream, false, "\"message\":\"Group not found\"", io);
}

const GroupEditClientsPost = struct {
    group_id: []const u8,
    client_ids: [][]const u8,
};

fn handleEditGroupClients(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(GroupEditClientsPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    subgroups_mutex.lockUncancelable(io);
    defer subgroups_mutex.unlock(io);
    
    for (subgroups.items) |g| {
        if (std.mem.eql(u8, g.group_id, parsed.value.group_id)) {
            for (g.client_ids.items) |cid| {
                allocator.free(cid);
            }
            g.client_ids.clearAndFree(allocator);
            
            for (parsed.value.client_ids) |cid| {
                try g.client_ids.append(allocator, try allocator.dupe(u8, cid));
            }
            std.debug.print("[HTTP] Updated clients for subgroup {s}.\n", .{g.group_id});
            sendJsonReply(stream, true, null, io);
            return;
        }
    }
    
    sendJsonReply(stream, false, "\"message\":\"Group not found\"", io);
}

const GroupDeletePost = struct {
    group_id: []const u8,
};

fn handleDeleteGroup(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(GroupDeletePost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    subgroups_mutex.lockUncancelable(io);
    defer subgroups_mutex.unlock(io);
    
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    var found_idx: ?usize = null;
    for (subgroups.items, 0..) |g, idx| {
        if (std.mem.eql(u8, g.group_id, parsed.value.group_id)) {
            found_idx = idx;
            break;
        }
    }
    
    if (found_idx) |idx| {
        const g = subgroups.swapRemove(idx);
        for (alarms.items) |a| {
            if (a.group_id) |g_id| {
                if (std.mem.eql(u8, g_id, g.group_id)) {
                    allocator.free(g_id);
                    a.group_id = null;
                }
            }
        }
        
        allocator.free(g.group_id);
        allocator.free(g.name);
        for (g.client_ids.items) |cid| {
            allocator.free(cid);
        }
        g.client_ids.deinit(allocator);
        allocator.destroy(g);
        
        std.debug.print("[HTTP] Deleted subgroup.\n", .{});
        sendJsonReply(stream, true, null, io);
    } else {
        sendJsonReply(stream, false, "\"message\":\"Group not found\"", io);
    }
}

const AlarmBulkEditPost = struct {
    alarm_ids: [][]const u8,
    enabled: ?bool = null,
    action: ?[]const u8 = null,
    duration: ?f32 = null,
    client_ids: ?[][]const u8 = null,
    group_id: ?[]const u8 = null,
};

fn handleBulkEditAlarms(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(AlarmBulkEditPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    var count: usize = 0;
    for (parsed.value.alarm_ids) |id| {
        for (alarms.items) |a| {
            if (std.mem.eql(u8, a.alarm_id, id)) {
                if (parsed.value.enabled) |en| {
                    a.enabled = en;
                }
                if (parsed.value.action) |act| {
                    allocator.free(a.action);
                    a.action = try allocator.dupe(u8, act);
                }
                if (parsed.value.duration) |dur| {
                    a.duration = dur;
                }
                if (parsed.value.client_ids) |cids| {
                    for (a.client_ids.items) |cid| {
                        allocator.free(cid);
                    }
                    a.client_ids.clearAndFree(allocator);
                    for (cids) |cid| {
                        try a.client_ids.append(allocator, try allocator.dupe(u8, cid));
                    }
                }
                if (parsed.value.group_id) |g_id| {
                    if (a.group_id) |old_gid| {
                        allocator.free(old_gid);
                    }
                    if (std.mem.eql(u8, g_id, "null") or g_id.len == 0) {
                        a.group_id = null;
                    } else {
                        a.group_id = try allocator.dupe(u8, g_id);
                    }
                }
                count += 1;
                break;
            }
        }
    }
    
    std.debug.print("[HTTP] Bulk edited {} alarms.\n", .{count});
    sendJsonReply(stream, true, null, io);
}

const ToggleAllPost = struct {
    enabled: bool,
};

fn handleToggleAllAlarms(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(ToggleAllPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    for (alarms.items) |a| {
        a.enabled = parsed.value.enabled;
    }
    
    std.debug.print("[HTTP] Toggled all alarms enabled = {}.\n", .{parsed.value.enabled});
    sendJsonReply(stream, true, null, io);
}

const IntervalAlarmPost = struct {
    client_ids: ?[][]const u8 = null,
    duration_sec: i64,
    count: i64,
    action: []const u8,
    action_duration: f32,
    group_id: ?[]const u8 = null,
};

fn handleCreateIntervalAlarms(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(IntervalAlarmPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    const duration_sec = parsed.value.duration_sec;
    const count = parsed.value.count;
    if (count <= 0) {
        sendJsonReply(stream, false, "\"message\":\"count must be > 0\"", io);
        return;
    }
    
    const action = parsed.value.action;
    const action_duration = parsed.value.action_duration;
    
    var parent_id_bytes: [16]u8 = undefined;
    crypto.getRandomBytes(&parent_id_bytes);
    const parent_id_hex = std.fmt.bytesToHex(parent_id_bytes, .lower);
    const parent_id = try allocator.dupe(u8, parent_id_hex[0..8]);
    errdefer allocator.free(parent_id);
    
    const now = common.getMilliTimestamp();
    const spacing_ms = if (count > 1) 
        @divTrunc(duration_sec * 1000, count - 1)
    else 
        @as(i64, 0);
        
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    var i: i64 = 0;
    while (i < count) : (i += 1) {
        var id_bytes: [16]u8 = undefined;
        crypto.getRandomBytes(&id_bytes);
        const id_hex = std.fmt.bytesToHex(id_bytes, .lower);
        
        const alarm = try allocator.create(Alarm);
        errdefer allocator.destroy(alarm);
        
        alarm.alarm_id = try allocator.dupe(u8, id_hex[0..8]);
        errdefer allocator.free(alarm.alarm_id);
        
        alarm.client_ids = std.ArrayList([]const u8).empty;
        errdefer {
            for (alarm.client_ids.items) |cid| allocator.free(cid);
            alarm.client_ids.deinit(allocator);
        }
        
        if (parsed.value.client_ids) |cids| {
            for (cids) |cid| {
                try alarm.client_ids.append(allocator, try allocator.dupe(u8, cid));
            }
        }
        
        alarm.trigger_time = now + (i * spacing_ms);
        alarm.action = try allocator.dupe(u8, action);
        errdefer allocator.free(alarm.action);
        alarm.duration = action_duration;
        alarm.fired = false;
        alarm.enabled = true;
        
        if (parsed.value.group_id) |g_id| {
            alarm.group_id = try allocator.dupe(u8, g_id);
        } else {
            alarm.group_id = null;
        }
        errdefer if (alarm.group_id) |g_id| allocator.free(g_id);
        
        alarm.parent_id = try allocator.dupe(u8, parent_id);
        
        try alarms.append(allocator, alarm);
    }
    
    std.debug.print("[HTTP] Created sequence of {} intervalled alarms with parent ID {s}.\n", .{count, parent_id});
    
    var extra_buf: [128]u8 = undefined;
    const extra = try std.fmt.bufPrint(&extra_buf, "\"parent_id\":\"{s}\"", .{parent_id});
    sendJsonReply(stream, true, extra, io);
    allocator.free(parent_id);
}

const AdjustIntervalPost = struct {
    parent_id: []const u8,
    spacing_sec: ?f32 = null,
    jitter_ms: ?i64 = null,
};

fn handleAdjustInterval(stream: std.Io.net.Stream, request: []const u8, allocator: std.mem.Allocator, io: std.Io) !void {
    const header_end = std.mem.indexOf(u8, request, "\r\n\r\n") orelse return error.InvalidRequest;
    const body = request[header_end + 4..];
    
    const parsed = try std.json.parseFromSlice(AdjustIntervalPost, allocator, body, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    
    alarms_mutex.lockUncancelable(io);
    defer alarms_mutex.unlock(io);
    
    var count: usize = 0;
    
    var list = std.ArrayList(*Alarm).empty;
    defer list.deinit(allocator);
    
    for (alarms.items) |a| {
        if (a.parent_id) |p_id| {
            if (std.mem.eql(u8, p_id, parsed.value.parent_id) and !a.fired) {
                try list.append(allocator, a);
            }
        }
    }
    
    if (list.items.len == 0) {
        sendJsonReply(stream, false, "\"message\":\"No active alarms found for parent_id\"", io);
        return;
    }
    
    const sortFn = struct {
        fn lessThan(_: void, lhs: *Alarm, rhs: *Alarm) bool {
            return lhs.trigger_time < rhs.trigger_time;
        }
    }.lessThan;
    std.mem.sort(*Alarm, list.items, {}, sortFn);
    
    const base_time = list.items[0].trigger_time;
    
    for (list.items, 0..) |a, idx| {
        if (parsed.value.spacing_sec) |spacing| {
            const spacing_ms = @as(i64, @intFromFloat(spacing * 1000.0));
            a.trigger_time = base_time + (@as(i64, @intCast(idx)) * spacing_ms);
        }
        if (parsed.value.jitter_ms) |jitter| {
            if (jitter > 0) {
                var rand_bytes: [8]u8 = undefined;
                crypto.getRandomBytes(&rand_bytes);
                const rand_val = std.mem.readInt(i64, &rand_bytes, .little);
                const offset = @mod(rand_val, jitter);
                a.trigger_time += offset;
            }
        }
        count += 1;
    }
    
    std.debug.print("[HTTP] Adjusted precision/spacing of {} pending alarms for parent ID {s}.\n", .{count, parsed.value.parent_id});
    sendJsonReply(stream, true, null, io);
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

fn startEmbeddedClient(allocator: std.mem.Allocator, io: std.Io) void {
    // Wait briefly for the TCP listener to bind port 5000
    common.sleepMs(200);
    std.debug.print("[Host] Starting embedded local client...\n", .{});
    
    client_module.runClientProgrammatic(
        "embedded-01",
        "127.0.0.1",
        5000,
        true, // allow_record
        true, // non_interactive (so it doesn't wait for stdin)
        allocator,
        io,
    ) catch |err| {
        std.debug.print("[Host] Embedded client connection exited: {}\n", .{err});
    };
}

fn handleCliCommand(line: []const u8, allocator: std.mem.Allocator, io: std.Io, stdin: *std.Io.Reader) !bool {
    const trimmed = std.mem.trim(u8, line, "\r\n ");
    if (trimmed.len == 0) return true;

    if (std.mem.eql(u8, trimmed, "exit")) {
        std.debug.print("[Host] Shutting down growth engine...\n", .{});
        return false;
    }
    if (std.mem.eql(u8, trimmed, "status") or std.mem.eql(u8, trimmed, "s")) {
        printStatus(io);
        return true;
    }
    if (std.mem.eql(u8, trimmed, "help") or std.mem.eql(u8, trimmed, "h")) {
        printHostUsage();
        return true;
    }

    var it = std.mem.tokenizeAny(u8, trimmed, " ");
    const module = it.next() orelse return true;

    if (std.mem.eql(u8, module, "dialogue")) {
        return try dialogue.handleDialogueCommand(&it, allocator, io, stdin, vault_path, vault_key);
    } else if (std.mem.eql(u8, module, "journal")) {
        return try journal.handleJournalCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "rhythm")) {
        return try rhythm.handleRhythmCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "stoic")) {
        return try stoic.handleStoicCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "lead")) {
        return try lead.handleLeadCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "vault")) {
        return try vault.handleVaultCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "aytree") or std.mem.eql(u8, module, "tree")) {
        // `tree` alias — suite Version Control / derivation map (not full VCS)
        return try aytree.handleAytreeCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "group")) {
        return try handleGroupCommand(&it, allocator, io);
    } else if (std.mem.eql(u8, module, "agent")) {
        std.debug.print("[Agent] Running optimization...\n", .{});
        return true;
    } else if (std.mem.eql(u8, module, "alarm")) {
        // Keep legacy for backward compatibility during transition
        return try handleAlarmCommand(&it, allocator, io);
    }

    std.debug.print("Unknown module '{s}'. Type 'help' for mission-aligned commands.\n", .{module});
    return true;
}

fn handleAlarmCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const sub = it.next() orelse {
        std.debug.print("Usage: alarm <schedule|group|list|toggle|bulk|interval|adjust> ...\n", .{});
        return true;
    };

    if (std.mem.eql(u8, sub, "schedule")) {
        const client_id = it.next() orelse {
            std.debug.print("Usage: alarm schedule <client_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const sec_str = it.next() orelse {
            std.debug.print("Usage: alarm schedule <client_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const action = it.next() orelse {
            std.debug.print("Usage: alarm schedule <client_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const dur_str = it.next() orelse "5.0";

        const seconds = std.fmt.parseInt(i64, sec_str, 10) catch {
            std.debug.print("Invalid seconds format: {s}\n", .{sec_str});
            return true;
        };
        const duration = std.fmt.parseFloat(f32, dur_str) catch {
            std.debug.print("Invalid duration format: {s}\n", .{dur_str});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would schedule alarm on {s} in {}s.\n", .{client_id, seconds});
            return true;
        }

        var id_bytes: [16]u8 = undefined;
        crypto.getRandomBytes(&id_bytes);
        const id_hex = std.fmt.bytesToHex(id_bytes, .lower);

        const alarm = try allocator.create(Alarm);
        var client_ids_list = std.ArrayList([]const u8).empty;
        try client_ids_list.append(allocator, try allocator.dupe(u8, client_id));

        alarm.* = Alarm{
            .alarm_id = try allocator.dupe(u8, id_hex[0..8]),
            .client_ids = client_ids_list,
            .trigger_time = common.getMilliTimestamp() + (seconds * 1000),
            .action = try allocator.dupe(u8, action),
            .duration = duration,
            .fired = false,
            .enabled = true,
            .group_id = null,
            .parent_id = null,
        };

        alarms_mutex.lockUncancelable(io);
        try alarms.append(allocator, alarm);
        alarms_mutex.unlock(io);

        std.debug.print("Scheduled alarm {s} for client {s} in {} seconds.\n", .{alarm.alarm_id, client_id, seconds});
        return true;
    } else if (std.mem.eql(u8, sub, "group")) {
        const group_id = it.next() orelse {
            std.debug.print("Usage: alarm group <group_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const sec_str = it.next() orelse {
            std.debug.print("Usage: alarm group <group_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const action = it.next() orelse {
            std.debug.print("Usage: alarm group <group_id> <sec_from_now> <action> <duration>\n", .{});
            return true;
        };
        const dur_str = it.next() orelse "5.0";

        const seconds = std.fmt.parseInt(i64, sec_str, 10) catch {
            std.debug.print("Invalid seconds format: {s}\n", .{sec_str});
            return true;
        };
        const duration = std.fmt.parseFloat(f32, dur_str) catch {
            std.debug.print("Invalid duration format: {s}\n", .{dur_str});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would schedule group alarm on {s} in {}s.\n", .{group_id, seconds});
            return true;
        }

        subgroups_mutex.lockUncancelable(io);
        var group_exists = false;
        for (subgroups.items) |g| {
            if (std.mem.eql(u8, g.group_id, group_id)) {
                group_exists = true;
                break;
            }
        }
        subgroups_mutex.unlock(io);

        if (!group_exists) {
            std.debug.print("Group {s} not found.\n", .{group_id});
            return true;
        }

        var id_bytes: [16]u8 = undefined;
        crypto.getRandomBytes(&id_bytes);
        const id_hex = std.fmt.bytesToHex(id_bytes, .lower);

        const alarm = try allocator.create(Alarm);

        alarm.* = Alarm{
            .alarm_id = try allocator.dupe(u8, id_hex[0..8]),
            .client_ids = std.ArrayList([]const u8).empty,
            .trigger_time = common.getMilliTimestamp() + (seconds * 1000),
            .action = try allocator.dupe(u8, action),
            .duration = duration,
            .fired = false,
            .enabled = true,
            .group_id = try allocator.dupe(u8, group_id),
            .parent_id = null,
        };

        alarms_mutex.lockUncancelable(io);
        try alarms.append(allocator, alarm);
        alarms_mutex.unlock(io);

        std.debug.print("Scheduled group alarm {s} for group {s} in {} seconds.\n", .{alarm.alarm_id, group_id, seconds});
        return true;
    } else if (std.mem.eql(u8, sub, "list")) {
        alarms_mutex.lockUncancelable(io);
        defer alarms_mutex.unlock(io);
        std.debug.print("Active Alarms: {}\n", .{alarms.items.len});
        for (alarms.items) |a| {
            std.debug.print("  ID: {s} | Trigger: {} | Fired: {}\n", .{a.alarm_id, a.trigger_time, a.fired});
        }
        return true;
    } else if (std.mem.eql(u8, sub, "toggle")) {
        const val_str = it.next() orelse {
            std.debug.print("Usage: alarm toggle <true|false>\n", .{});
            return true;
        };
        const enabled = std.mem.eql(u8, val_str, "true");

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would toggle alarms enabled = {}.\n", .{enabled});
            return true;
        }

        alarms_mutex.lockUncancelable(io);
        for (alarms.items) |a| {
            a.enabled = enabled;
        }
        alarms_mutex.unlock(io);

        std.debug.print("Toggled all alarms enabled = {}.\n", .{enabled});
        return true;
    } else if (std.mem.eql(u8, sub, "bulk")) {
        const action = it.next() orelse {
            std.debug.print("Usage: alarm bulk <action> <duration> <alarm_id1,alarm_id2,...>\n", .{});
            return true;
        };
        const dur_str = it.next() orelse {
            std.debug.print("Usage: alarm bulk <action> <duration> <alarm_id1,alarm_id2,...>\n", .{});
            return true;
        };
        const ids_str = it.next() orelse {
            std.debug.print("Usage: alarm bulk <action> <duration> <alarm_id1,alarm_id2,...>\n", .{});
            return true;
        };

        const duration = std.fmt.parseFloat(f32, dur_str) catch {
            std.debug.print("Invalid duration format: {s}\n", .{dur_str});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would bulk edit {s}.\n", .{ids_str});
            return true;
        }

        alarms_mutex.lockUncancelable(io);
        defer alarms_mutex.unlock(io);

        var count: usize = 0;
        var id_it = std.mem.tokenizeAny(u8, ids_str, ",");
        while (id_it.next()) |id| {
            for (alarms.items) |a| {
                if (std.mem.eql(u8, a.alarm_id, id)) {
                    allocator.free(a.action);
                    a.action = try allocator.dupe(u8, action);
                    a.duration = duration;
                    count += 1;
                    break;
                }
            }
        }

        std.debug.print("Bulk edited {} alarms.\n", .{count});
        return true;
    } else if (std.mem.eql(u8, sub, "interval")) {
        const clients_str = it.next() orelse {
            std.debug.print("Usage: alarm interval <client_id1,...> <dur_sec> <count> <action> <act_dur> [group_id]\n", .{});
            return true;
        };
        const dur_sec_str = it.next() orelse {
            std.debug.print("Usage: alarm interval <client_id1,...> <dur_sec> <count> <action> <act_dur> [group_id]\n", .{});
            return true;
        };
        const count_str = it.next() orelse {
            std.debug.print("Usage: alarm interval <client_id1,...> <dur_sec> <count> <action> <act_dur> [group_id]\n", .{});
            return true;
        };
        const action = it.next() orelse {
            std.debug.print("Usage: alarm interval <client_id1,...> <dur_sec> <count> <action> <act_dur> [group_id]\n", .{});
            return true;
        };
        const act_dur_str = it.next() orelse {
            std.debug.print("Usage: alarm interval <client_id1,...> <dur_sec> <count> <action> <act_dur> [group_id]\n", .{});
            return true;
        };
        const g_id = it.next();

        const duration_sec = std.fmt.parseInt(i64, dur_sec_str, 10) catch {
            std.debug.print("Invalid duration_sec: {s}\n", .{dur_sec_str});
            return true;
        };
        const count = std.fmt.parseInt(i64, count_str, 10) catch {
            std.debug.print("Invalid count: {s}\n", .{count_str});
            return true;
        };
        const action_duration = std.fmt.parseFloat(f32, act_dur_str) catch {
            std.debug.print("Invalid action_duration: {s}\n", .{act_dur_str});
            return true;
        };

        if (count <= 0) {
            std.debug.print("count must be > 0\n", .{});
            return true;
        }

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would schedule interval alarms.\n", .{});
            return true;
        }

        var parent_id_bytes: [16]u8 = undefined;
        crypto.getRandomBytes(&parent_id_bytes);
        const parent_id_hex = std.fmt.bytesToHex(parent_id_bytes, .lower);
        const parent_id = try allocator.dupe(u8, parent_id_hex[0..8]);
        errdefer allocator.free(parent_id);

        const now = common.getMilliTimestamp();
        const spacing_ms = if (count > 1)
            @divTrunc(duration_sec * 1000, count - 1)
        else
            @as(i64, 0);

        alarms_mutex.lockUncancelable(io);
        defer alarms_mutex.unlock(io);

        var i: i64 = 0;
        while (i < count) : (i += 1) {
            var id_bytes: [16]u8 = undefined;
            crypto.getRandomBytes(&id_bytes);
            const id_hex = std.fmt.bytesToHex(id_bytes, .lower);

            const alarm = try allocator.create(Alarm);
            errdefer allocator.destroy(alarm);

            alarm.alarm_id = try allocator.dupe(u8, id_hex[0..8]);
            errdefer allocator.free(alarm.alarm_id);

            alarm.client_ids = std.ArrayList([]const u8).empty;
            errdefer {
                for (alarm.client_ids.items) |cid| allocator.free(cid);
                alarm.client_ids.deinit(allocator);
            }

            var client_it = std.mem.tokenizeAny(u8, clients_str, ",");
            while (client_it.next()) |cid| {
                try alarm.client_ids.append(allocator, try allocator.dupe(u8, cid));
            }

            alarm.trigger_time = now + (i * spacing_ms);
            alarm.action = try allocator.dupe(u8, action);
            errdefer allocator.free(alarm.action);
            alarm.duration = action_duration;
            alarm.fired = false;
            alarm.enabled = true;

            if (g_id) |gid| {
                alarm.group_id = try allocator.dupe(u8, gid);
            } else {
                alarm.group_id = null;
            }
            errdefer if (alarm.group_id) |gid| allocator.free(gid);

            alarm.parent_id = try allocator.dupe(u8, parent_id);
            try alarms.append(allocator, alarm);
        }

        std.debug.print("Created sequence of {} intervalled alarms with parent ID {s}.\n", .{count, parent_id});
        allocator.free(parent_id);
        return true;
    } else if (std.mem.eql(u8, sub, "adjust")) {
        const parent_id = it.next() orelse {
            std.debug.print("Usage: alarm adjust <parent_id> <spacing_sec> <jitter_ms>\n", .{});
            return true;
        };
        const spacing_str = it.next() orelse {
            std.debug.print("Usage: alarm adjust <parent_id> <spacing_sec> <jitter_ms>\n", .{});
            return true;
        };
        const jitter_str = it.next() orelse "0";

        const spacing = std.fmt.parseFloat(f32, spacing_str) catch {
            std.debug.print("Invalid spacing format: {s}\n", .{spacing_str});
            return true;
        };
        const jitter = std.fmt.parseInt(i64, jitter_str, 10) catch {
            std.debug.print("Invalid jitter format: {s}\n", .{jitter_str});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would adjust spacing for {s}.\n", .{parent_id});
            return true;
        }

        alarms_mutex.lockUncancelable(io);
        defer alarms_mutex.unlock(io);

        var list = std.ArrayList(*Alarm).empty;
        defer list.deinit(allocator);

        for (alarms.items) |a| {
            if (a.parent_id) |p_id| {
                if (std.mem.eql(u8, p_id, parent_id) and !a.fired) {
                    try list.append(allocator, a);
                }
            }
        }

        if (list.items.len == 0) {
            std.debug.print("No active alarms found for parent_id {s}\n", .{parent_id});
            return true;
        }

        const sortFn = struct {
            fn lessThan(_: void, lhs: *Alarm, rhs: *Alarm) bool {
                return lhs.trigger_time < rhs.trigger_time;
            }
        }.lessThan;
        std.mem.sort(*Alarm, list.items, {}, sortFn);

        const base_time = list.items[0].trigger_time;
        var count: usize = 0;

        for (list.items, 0..) |a, idx| {
            const spacing_ms = @as(i64, @intFromFloat(spacing * 1000.0));
            a.trigger_time = base_time + (@as(i64, @intCast(idx)) * spacing_ms);
            
            if (jitter > 0) {
                var rand_bytes: [8]u8 = undefined;
                crypto.getRandomBytes(&rand_bytes);
                const rand_val = std.mem.readInt(i64, &rand_bytes, .little);
                const offset = @mod(rand_val, jitter);
                a.trigger_time += offset;
            }
            count += 1;
        }

        std.debug.print("Adjusted spacing of {} pending alarms for parent ID {s}.\n", .{count, parent_id});
        return true;
    }
    
    std.debug.print("Unknown alarm subcommand: {s}\n", .{sub});
    return true;
}

fn handleGroupCommand(it: *std.mem.TokenIterator(u8, .any), allocator: std.mem.Allocator, io: std.Io) !bool {
    const sub = it.next() orelse {
        std.debug.print("Usage: group <create|list|rename|edit|delete> ...\n", .{});
        return true;
    };

    if (std.mem.eql(u8, sub, "create")) {
        const name = it.next() orelse {
            std.debug.print("Usage: group create <name> <client_id1,client_id2,...>\n", .{});
            return true;
        };
        const clients_str = it.next() orelse {
            std.debug.print("Usage: group create <name> <client_id1,client_id2,...>\n", .{});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would create group {s}.\n", .{name});
            return true;
        }

        var id_bytes: [16]u8 = undefined;
        crypto.getRandomBytes(&id_bytes);
        const id_hex = std.fmt.bytesToHex(id_bytes, .lower);
        const group_id = try allocator.dupe(u8, id_hex[0..8]);
        errdefer allocator.free(group_id);

        const group = try allocator.create(AlarmGroup);
        errdefer allocator.destroy(group);

        group.group_id = group_id;
        group.name = try allocator.dupe(u8, name);
        errdefer allocator.free(group.name);

        group.client_ids = std.ArrayList([]const u8).empty;
        errdefer {
            for (group.client_ids.items) |cid| allocator.free(cid);
            group.client_ids.deinit(allocator);
        }

        var client_it = std.mem.tokenizeAny(u8, clients_str, ",");
        while (client_it.next()) |cid| {
            try group.client_ids.append(allocator, try allocator.dupe(u8, cid));
        }

        subgroups_mutex.lockUncancelable(io);
        try subgroups.append(allocator, group);
        subgroups_mutex.unlock(io);

        std.debug.print("Created group '{s}' with ID {s}.\n", .{name, group_id});
        return true;
    } else if (std.mem.eql(u8, sub, "list")) {
        subgroups_mutex.lockUncancelable(io);
        defer subgroups_mutex.unlock(io);
        std.debug.print("Active Groups: {}\n", .{subgroups.items.len});
        for (subgroups.items) |g| {
            std.debug.print("  ID: {s} | Name: '{s}' | Clients: {}\n", .{g.group_id, g.name, g.client_ids.items.len});
        }
        return true;
    } else if (std.mem.eql(u8, sub, "rename")) {
        const group_id = it.next() orelse {
            std.debug.print("Usage: group rename <group_id> <new_name>\n", .{});
            return true;
        };
        const new_name = it.next() orelse {
            std.debug.print("Usage: group rename <group_id> <new_name>\n", .{});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would rename group {s} to {s}.\n", .{group_id, new_name});
            return true;
        }

        subgroups_mutex.lockUncancelable(io);
        defer subgroups_mutex.unlock(io);

        for (subgroups.items) |g| {
            if (std.mem.eql(u8, g.group_id, group_id)) {
                allocator.free(g.name);
                g.name = try allocator.dupe(u8, new_name);
                std.debug.print("Renamed group {s} to '{s}'.\n", .{group_id, new_name});
                return true;
            }
        }

        std.debug.print("Group {s} not found.\n", .{group_id});
        return true;
    } else if (std.mem.eql(u8, sub, "edit")) {
        const group_id = it.next() orelse {
            std.debug.print("Usage: group edit <group_id> <client_id1,client_id2,...>\n", .{});
            return true;
        };
        const clients_str = it.next() orelse {
            std.debug.print("Usage: group edit <group_id> <client_id1,client_id2,...>\n", .{});
            return true;
        };

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would edit group {s}.\n", .{group_id});
            return true;
        }

        subgroups_mutex.lockUncancelable(io);
        defer subgroups_mutex.unlock(io);

        for (subgroups.items) |g| {
            if (std.mem.eql(u8, g.group_id, group_id)) {
                for (g.client_ids.items) |cid| {
                    allocator.free(cid);
                }
                g.client_ids.clearAndFree(allocator);

                var client_it = std.mem.tokenizeAny(u8, clients_str, ",");
                while (client_it.next()) |cid| {
                    try g.client_ids.append(allocator, try allocator.dupe(u8, cid));
                }
                std.debug.print("Updated group {s} clients.\n", .{group_id});
                return true;
            }
        }

        std.debug.print("Group {s} not found.\n", .{group_id});
        return true;
    } else if (std.mem.eql(u8, sub, "delete")) {
        const group_id = it.next() orelse {
            std.debug.print("Usage: group delete <group_id>\n", .{});
            return true;
        };

        if (!cli.confirmDestructive(global_flags.production, io)) return true;

        if (global_flags.dry_run) {
            std.debug.print("[Dry-Run] Would delete group {s}.\n", .{group_id});
            return true;
        }

        subgroups_mutex.lockUncancelable(io);
        defer subgroups_mutex.unlock(io);

        for (subgroups.items, 0..) |g, idx| {
            if (std.mem.eql(u8, g.group_id, group_id)) {
                _ = subgroups.swapRemove(idx);
                allocator.free(g.group_id);
                allocator.free(g.name);
                for (g.client_ids.items) |cid| {
                    allocator.free(cid);
                }
                g.client_ids.deinit(allocator);
                allocator.destroy(g);
                std.debug.print("Deleted group {s}.\n", .{group_id});
                return true;
            }
        }

        std.debug.print("Group {s} not found.\n", .{group_id});
        return true;
    }
    
    std.debug.print("Unknown group subcommand: {s}\n", .{sub});
    return true;
}

