const std = @import("std");
const builtin = @import("builtin");
const common = @import("common.zig");
const audio_record = @import("audio_record.zig");

// Windows API imports
pub extern "kernel32" fn Beep(dwFreq: u32, dwDuration: u32) callconv(.winapi) i32;
pub extern "kernel32" fn GetComputerNameA(lpBuffer: [*]u8, lpnSize: *u32) callconv(.winapi) i32;

// Win32 Logging types and externs
const HANDLE = *anyopaque;
const DWORD = u32;
const LPCSTR = [*:0]const u8;

pub extern "kernel32" fn CreateFileA(
    lpFileName: LPCSTR,
    dwDesiredAccess: DWORD,
    dwShareMode: DWORD,
    lpSecurityAttributes: ?*anyopaque,
    dwCreationDisposition: DWORD,
    dwFlagsAndAttributes: DWORD,
    hTemplateFile: ?HANDLE,
) callconv(.winapi) HANDLE;

pub extern "kernel32" fn SetFilePointer(
    hFile: HANDLE,
    lDistanceToMove: i32,
    lpDistanceToMoveHigh: ?*i32,
    dwMoveMethod: DWORD,
) callconv(.winapi) DWORD;

pub extern "kernel32" fn WriteFile(
    hFile: HANDLE,
    lpBuffer: [*]const u8,
    nNumberOfBytesToWrite: DWORD,
    lpNumberOfBytesWritten: ?*DWORD,
    lpOverlapped: ?*anyopaque,
) callconv(.winapi) i32;

pub extern "kernel32" fn CloseHandle(hObject: HANDLE) callconv(.winapi) i32;

const INVALID_HANDLE_VALUE = @as(HANDLE, @ptrFromInt(std.math.maxInt(usize)));
const GENERIC_WRITE = 0x40000000;
const FILE_SHARE_READ = 1;
const OPEN_ALWAYS = 4;
const FILE_ATTRIBUTE_NORMAL = 128;
const FILE_END = 2;

const SYSTEMTIME = struct {
    wYear: u16,
    wMonth: u16,
    wDayOfWeek: u16,
    wDay: u16,
    wHour: u16,
    wMinute: u16,
    wSecond: u16,
    wMilliseconds: u16,
};
pub extern "kernel32" fn GetLocalTime(lpSystemTime: *SYSTEMTIME) callconv(.winapi) void;

// Format local time into a buffer. Returns the slice containing the string.
fn getFormattedTime(buf: []u8) []const u8 {
    if (builtin.os.tag == .windows) {
        var st: SYSTEMTIME = undefined;
        GetLocalTime(&st);
        return std.fmt.bufPrint(buf, "{d:0>4}-{d:0>2}-{d:0>2} {d:0>2}:{d:0>2}:{d:0>2}.{d:0>3}", .{
            st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
        }) catch "0000-00-00 00:00:00.000";
    } else {
        const millis = common.getMilliTimestamp();
        const secs = @divTrunc(millis, 1000);
        const ms_part = @mod(millis, 1000);
        return std.fmt.bufPrint(buf, "Unix Epoch: {}s {}ms", .{ secs, ms_part }) catch "0000-00-00 00:00:00.000";
    }
}

// Synchronous file logger
fn writeLogSync(bytes: []const u8) void {
    if (builtin.os.tag == .windows) {
        const handle = CreateFileA(
            "client.log",
            GENERIC_WRITE,
            FILE_SHARE_READ,
            null,
            OPEN_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            null,
        );
        if (handle == INVALID_HANDLE_VALUE) return;
        defer _ = CloseHandle(handle);

        _ = SetFilePointer(handle, 0, null, FILE_END);
        var written: DWORD = 0;
        _ = WriteFile(handle, bytes.ptr, @intCast(bytes.len), &written, null);
    } else {
        // Fallback for non-Windows (write to stderr/stdout or standard print)
        std.debug.print("{s}", .{bytes});
    }
}

// Log telemetry event to client.log in append mode.
fn logEvent(event_type: []const u8, comptime format: []const u8, args: anytype) void {
    var time_buf: [64]u8 = undefined;
    const time_str = getFormattedTime(&time_buf);

    var msg_buf: [1024]u8 = undefined;
    const msg_str = std.fmt.bufPrint(&msg_buf, format, args) catch return;

    var log_buf: [1200]u8 = undefined;
    const log_line = std.fmt.bufPrint(&log_buf, "[{s}] [{s}] {s}\n", .{ time_str, event_type, msg_str }) catch return;

    writeLogSync(log_line);
}

// Custom panic handler to dump crash details to client.log and default panic
pub const panic = std.debug.FullPanic(myPanic);

fn myPanic(msg: []const u8, ret_addr: ?usize) noreturn {
    var time_buf: [64]u8 = undefined;
    var time_str: []const u8 = "0000-00-00 00:00:00.000";
    if (builtin.os.tag == .windows) {
        var st: SYSTEMTIME = undefined;
        GetLocalTime(&st);
        time_str = std.fmt.bufPrint(&time_buf, "{d:0>4}-{d:0>2}-{d:0>2} {d:0>2}:{d:0>2}:{d:0>2}.{d:0>3}", .{
            st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
        }) catch "0000-00-00 00:00:00.000";
    } else {
        const millis = common.getMilliTimestamp();
        const secs = @divTrunc(millis, 1000);
        const ms_part = @mod(millis, 1000);
        time_str = std.fmt.bufPrint(&time_buf, "Unix Epoch: {}s {}ms", .{ secs, ms_part }) catch "0000-00-00 00:00:00.000";
    }

    var log_buf: [1200]u8 = undefined;
    const log_line = std.fmt.bufPrint(&log_buf, "[{s}] [Crash/Panic] PANIC: {s}\n", .{ time_str, msg }) catch "PANIC occurred\n";

    writeLogSync(log_line);

    std.debug.defaultPanic(msg, ret_addr);
}

pub fn runClient(init: std.process.Init, host_ip_override: []const u8, host_port_override: u16) !void {
    const allocator = init.gpa;
    var threaded = std.Io.Threaded.init(allocator, .{});
    defer threaded.deinit();
    const io = threaded.io();

    logEvent("Online", "Sesephus Client brought online.", .{});

    runClientWithOverrides(init, allocator, io, host_ip_override, host_port_override) catch |err| {
        logEvent("Crash", "Client crashed with fatal error: {s}", .{@errorName(err)});
        return err;
    };

    logEvent("Offline", "Sesephus Client terminated normally.", .{});
}

fn runClientWithOverrides(
    init: std.process.Init,
    allocator: std.mem.Allocator,
    io: std.Io,
    host_ip_override: []const u8,
    host_port_override: u16,
) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());

    var client_id: []const u8 = "";
    var host_ip: []const u8 = host_ip_override;
    var host_port: u16 = host_port_override;
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

    try runClientProgrammatic(client_id, host_ip, host_port, allow_record, non_interactive, allocator, io);
}

pub fn runClientProgrammatic(client_id: []const u8, host_ip: []const u8, host_port: u16, allow_record: bool, non_interactive: bool, allocator: std.mem.Allocator, io: std.Io) !void {
    const friendly_name = try std.fmt.allocPrint(allocator, "Sesephus Client: {s}", .{client_id});
    defer allocator.free(friendly_name);

    std.debug.print("==================================================\n", .{});
    std.debug.print("      SESEFUS CLIENT DEVICE (CIRCADIA/ARCADIUM)   \n", .{});
    std.debug.print("==================================================\n", .{});
    std.debug.print("[Client] Name: {s}\n", .{client_id});
    std.debug.print("[Client] Host: {s}:{}\n", .{host_ip, host_port});

    logEvent("Online", "Configuration - Client Name: '{s}', Host: {s}:{d}", .{ client_id, host_ip, host_port });

    // Connect to host
    const address = try std.Io.net.IpAddress.parseIp4(host_ip, host_port);
    std.debug.print("[Client] Connecting to host...\n", .{});
    logEvent("Connection", "Connecting to Sesephus host at {s}:{d}...", .{ host_ip, host_port });
    
    // Connect retry loop (host might take a moment to bind port 5000)
    var stream: std.Io.net.Stream = undefined;
    var retries: usize = 10;
    while (retries > 0) : (retries -= 1) {
        stream = address.connect(io, .{ .mode = .stream }) catch |err| {
            if (retries == 1) {
                std.debug.print("[Client] Connection failed after retries: {}\n", .{err});
                logEvent("ConnectionError", "Failed to connect to host: {s}", .{@errorName(err)});
                return err;
            }
            common.sleepMs(500);
            continue;
        };
        break;
    }
    defer stream.close(io);
    std.debug.print("[Client] Connected to host!\n", .{});
    logEvent("Connection", "Connected to host successfully.", .{});

    // Register with host
    const reg_msg = common.Message{
        .type = "RegisterClient",
        .client_id = client_id,
        .friendly_name = friendly_name,
    };
    try common.writeMessage(stream, reg_msg, allocator, io);
    std.debug.print("[Client] Registered with host.\n", .{});
    logEvent("Registration", "Registered client '{s}' with host.", .{client_id});

    // Receive and process messages
    while (true) {
        const msg_parsed = common.readMessage(stream, allocator, io) catch |err| {
            if (err == error.EndOfStream) {
                std.debug.print("[Client] Connection closed by host.\n", .{});
                logEvent("Connection", "Connection closed by host.", .{});
                break;
            }
            std.debug.print("[Client] Socket read error: {}\n", .{err});
            logEvent("SocketError", "Socket read error: {s}", .{@errorName(err)});
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
            logEvent("AlarmTriggered", "Alarm ID: {s}, Action requested: {s}, Duration: {d:.1}s", .{ alarm_id, action, duration });

            // Perform definable action
            if (std.mem.eql(u8, action, "play_sound") or std.mem.eql(u8, action, "beep")) {
                std.debug.print("[Client] Sound action: Playing beep...\n", .{});
                logEvent("ActionStart", "Executing sound action (beep).", .{});
                if (builtin.os.tag == .windows) {
                    _ = Beep(880, 500); // 880 Hz for 500 ms
                    _ = Beep(1200, 300);
                } else {
                    std.debug.print("\x07", .{}); // system bell beep
                }
                logEvent("ActionEnd", "Sound action (beep) completed.", .{});
            } else if (std.mem.eql(u8, action, "run_command")) {
                std.debug.print("[Client] Command action: Executing defined task alert...\n", .{});
                logEvent("ActionStart", "Executing command: echo SESEPHUS TASK ALERT!", .{});
                const argv = if (builtin.os.tag == .windows)
                    &[_][]const u8{ "cmd.exe", "/c", "echo SESEPHUS TASK ALERT!" }
                else
                    &[_][]const u8{ "echo", "SESEPHUS TASK ALERT!" };
                var child = try std.process.spawn(io, .{ .argv = argv });
                _ = try child.wait(io);
                logEvent("ActionEnd", "Command action completed.", .{});
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
                    logEvent("ActionDismissed", "Audio recording action dismissed (no-record flag active).", .{});
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
                    logEvent("ActionDismissed", "Audio recording action dismissed by user input.", .{});
                    continue;
                }

                std.debug.print("[Client] Audio action: Capturing journal entry...\n", .{});
                logEvent("ActionStart", "Capturing audio recording for {d:.1} seconds...", .{duration});
                
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
                    logEvent("ActionError", "Audio recording failed: {s}", .{@errorName(rec_err)});
                    continue;
                };
                logEvent("ActionEnd", "Audio recording saved locally to {s}.", .{local_path});

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
                logEvent("Telemetry", "Synced metadata for {s} with host.", .{filename});
            } else {
                std.debug.print("[Client] Warning: Action '{s}' is undefined.\n", .{action});
                logEvent("Telemetry", "Warning: Action '{s}' is undefined.", .{action});
            }
        } else if (std.mem.eql(u8, msg.type, "StatusResponse")) {
            const success = msg.success orelse false;
            const detail = msg.message orelse "";
            std.debug.print("[Client] Host status reply: success={}, msg='{s}'\n", .{ success, detail });
            logEvent("Telemetry", "Host status reply: success={}, message='{s}'", .{ success, detail });
        }
    }
}
