const std = @import("std");
const builtin = @import("builtin");
const common = @import("common.zig");
const audio_record = @import("audio_record.zig");

// Windows API imports
pub extern "kernel32" fn Beep(dwFreq: u32, dwDuration: u32) callconv(.winapi) i32;
pub extern "kernel32" fn GetComputerNameA(lpBuffer: [*]u8, lpnSize: *u32) callconv(.winapi) i32;

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    const args = try init.minimal.args.toSlice(init.arena.allocator());

    var client_id: []const u8 = "";
    var host_ip: []const u8 = "127.0.0.1";
    var host_port: u16 = 5000;
    var non_interactive = false;
    var allow_record = true;

    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        if (std.mem.eql(u8, args[i], "--name")) {
            if (i + 1 < args.len) {
                client_id = args[i + 1];
                i += 1;
            }
        } else if (std.mem.eql(u8, args[i], "--host")) {
            if (i + 1 < args.len) {
                host_ip = args[i + 1];
                i += 1;
            }
        } else if (std.mem.eql(u8, args[i], "--port")) {
            if (i + 1 < args.len) {
                host_port = try std.fmt.parseInt(u16, args[i + 1], 10);
                i += 1;
            }
        } else if (std.mem.eql(u8, args[i], "--non-interactive")) {
            non_interactive = true;
        } else if (std.mem.eql(u8, args[i], "--no-record")) {
            allow_record = false;
        }
    }

    if (client_id.len == 0) {
        // Look up computer name if on Windows
        if (builtin.os.tag == .windows) {
            var name_buf: [128]u8 = undefined;
            var size: u32 = name_buf.len;
            if (GetComputerNameA(&name_buf, &size) != 0) {
                client_id = try allocator.dupe(u8, name_buf[0..size]);
            } else {
                client_id = "windows-device";
            }
        } else {
            // Check environment
            if (init.environ_map.get("HOSTNAME")) |hn| {
                client_id = try allocator.dupe(u8, hn);
            } else if (init.environ_map.get("USER")) |u| {
                client_id = try allocator.dupe(u8, u);
            } else {
                client_id = "unknown-device";
            }
        }
    }

    const friendly_name = try std.fmt.allocPrint(allocator, "Sesephus Client: {s}", .{client_id});
    defer allocator.free(friendly_name);

    std.debug.print("==================================================\n", .{});
    std.debug.print("      SESEPHUS CLIENT DEVICE (CIRCADIA/ARCADIUM)  \n", .{});
    std.debug.print("==================================================\n", .{});
    std.debug.print("[Client] Name: {s}\n", .{client_id});
    std.debug.print("[Client] Host: {s}:{}\n", .{host_ip, host_port});

    // Connect to host
    const address = try std.Io.net.IpAddress.parseIp4(host_ip, host_port);
    std.debug.print("[Client] Connecting to host...\n", .{});
    
    const stream = address.connect(io, .{ .mode = .stream }) catch |err| {
        std.debug.print("[Client] Connection failed: {}\n", .{err});
        return;
    };
    defer stream.close(io);
    std.debug.print("[Client] Connected to host!\n", .{});

    // Register with host
    const reg_msg = common.Message{
        .type = "RegisterClient",
        .client_id = client_id,
        .friendly_name = friendly_name,
    };
    try common.writeMessage(stream, reg_msg, allocator, io);
    std.debug.print("[Client] Registered with host.\n", .{});

    // Receive and process messages
    while (true) {
        const msg_parsed = common.readMessage(stream, allocator, io) catch |err| {
            if (err == error.EndOfStream) {
                std.debug.print("[Client] Connection closed by host.\n", .{});
                break;
            }
            std.debug.print("[Client] Socket read error: {}\n", .{err});
            break;
        };
        defer msg_parsed.deinit();

        const msg = msg_parsed.parsed.value;
        if (std.mem.eql(u8, msg.type, "TimeSync")) {
            const server_time = msg.server_time orelse 0;
            const now = common.getMilliTimestamp();
            const offset = server_time - now;
            std.debug.print("[Client] Time sync: server_time = {}, local_time = {}, offset = {} ms\n", .{ server_time, now, offset });
        } else if (std.mem.eql(u8, msg.type, "AlarmTrigger")) {
            const alarm_id = msg.alarm_id orelse "unknown";
            const action = msg.action orelse "beep";
            const duration = msg.duration orelse 5.0;

            std.debug.print("\n[Client] *** ALARM TRIGGERED! *** (ID: {s})\n", .{alarm_id});
            std.debug.print("[Client] Definable Action requested: {s}\n", .{action});

            // Perform definable action
            if (std.mem.eql(u8, action, "play_sound") or std.mem.eql(u8, action, "beep")) {
                std.debug.print("[Client] Sound action: Playing beep...\n", .{});
                if (builtin.os.tag == .windows) {
                    _ = Beep(880, 500); // 880 Hz for 500 ms
                    _ = Beep(1200, 300);
                } else {
                    std.debug.print("\x07", .{}); // system bell beep
                }
            } else if (std.mem.eql(u8, action, "run_command")) {
                std.debug.print("[Client] Command action: Executing defined task alert...\n", .{});
                const argv = if (builtin.os.tag == .windows)
                    &[_][]const u8{ "cmd.exe", "/c", "echo SESEPHUS TASK ALERT!" }
                else
                    &[_][]const u8{ "echo", "SESEPHUS TASK ALERT!" };
                var child = try std.process.spawn(io, .{ .argv = argv });
                _ = try child.wait(io);
            } else if (std.mem.eql(u8, action, "record_audio")) {
                // Play alert sound first
                std.debug.print("[Client] Sound action: Playing beep...\n", .{});
                if (builtin.os.tag == .windows) {
                    _ = Beep(880, 500); // 880 Hz for 500 ms
                    _ = Beep(1200, 300);
                } else {
                    std.debug.print("\x07", .{}); // system bell beep
                }

                if (!allow_record) {
                    std.debug.print("[Client] Alarm dismissed. Recording is disabled on this device.\n", .{});
                    continue;
                }

                var want_record = non_interactive;
                if (!want_record) {
                    std.debug.print("\n[Client] Do you want to record a voice journal? (y/N): ", .{});
                    const stdin_file = std.Io.File.stdin();
                    var stdin_buf: [256]u8 = undefined;
                    var stdin_reader = stdin_file.reader(io, &stdin_buf);
                    if (try stdin_reader.interface.takeDelimiter('\n')) |line| {
                        const trimmed = std.mem.trim(u8, line, "\r\n ");
                        if (std.mem.eql(u8, trimmed, "y") or std.mem.eql(u8, trimmed, "yes") or std.mem.eql(u8, trimmed, "Y")) {
                            want_record = true;
                        }
                    }
                }

                if (!want_record) {
                    std.debug.print("[Client] Alarm dismissed. No recording captured.\n", .{});
                    continue;
                }

                std.debug.print("[Client] Audio action: Capturing journal entry...\n", .{});
                
                // Create recordings folder if missing
                const cwd = std.Io.Dir.cwd();
                cwd.createDirPath(io, "recordings") catch {};

                const timestamp = common.getMilliTimestamp();
                var filename_buf: [64]u8 = undefined;
                const filename = std.fmt.bufPrint(&filename_buf, "journal_{}.wav", .{timestamp}) catch "journal.wav";
                
                var local_path_buf: [256]u8 = undefined;
                const local_path = std.fmt.bufPrint(&local_path_buf, "recordings/{s}", .{filename}) catch "recordings/journal.wav";

                std.debug.print("[Client] Recording WAV locally to: {s}...\n", .{local_path});
                
                // Record WAV file directly to local recordings folder
                audio_record.recordAudio(local_path, duration, allocator, io) catch |rec_err| {
                    std.debug.print("[Client] Recording failed: {}\n", .{rec_err});
                    continue;
                };

                // Send LocalRecordStatus message to host
                std.debug.print("[Client] Syncing metadata with host...\n", .{});
                const status_msg = common.Message{
                    .type = "LocalRecordStatus",
                    .client_id = client_id,
                    .filename = filename,
                    .timestamp = timestamp,
                    .local_path = local_path,
                };
                try common.writeMessage(stream, status_msg, allocator, io);
                std.debug.print("[Client] Metadata synced. Local file preserved at {s}.\n", .{local_path});
            } else {
                std.debug.print("[Client] Warning: Action '{s}' is undefined.\n", .{action});
            }
        } else if (std.mem.eql(u8, msg.type, "StatusResponse")) {
            const success = msg.success orelse false;
            const detail = msg.message orelse "";
            std.debug.print("[Client] Host status reply: success={}, msg='{s}'\n", .{ success, detail });
        }
    }
}
