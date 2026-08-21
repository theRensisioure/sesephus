const std = @import("std");
const builtin = @import("builtin");

// Windows Multimedia API Types & Functions
const HWAVEIN = *anyopaque;

const WAVEFORMATEX = extern struct {
    wFormatTag: u16,
    nChannels: u16,
    nSamplesPerSec: u32,
    nAvgBytesPerSec: u32,
    nBlockAlign: u16,
    wBitsPerSample: u16,
    cbSize: u16,
};

const WAVEHDR = extern struct {
    lpData: [*]u8,
    dwBufferLength: u32,
    dwBytesRecorded: u32,
    dwUser: usize,
    dwFlags: u32,
    dwLoops: u32,
    lpNext: ?*WAVEHDR,
    reserved: usize,
};

pub extern "winmm" fn waveInOpen(
    phwi: *?HWAVEIN,
    uDeviceID: u32,
    pwfx: *const WAVEFORMATEX,
    dwCallback: usize,
    dwInstance: usize,
    fdwOpen: u32,
) callconv(.winapi) u32;

pub extern "winmm" fn waveInPrepareHeader(hwi: HWAVEIN, pwh: *WAVEHDR, cbwh: u32) callconv(.winapi) u32;
pub extern "winmm" fn waveInAddBuffer(hwi: HWAVEIN, pwh: *WAVEHDR, cbwh: u32) callconv(.winapi) u32;
pub extern "winmm" fn waveInStart(hwi: HWAVEIN) callconv(.winapi) u32;
pub extern "winmm" fn waveInStop(hwi: HWAVEIN) callconv(.winapi) u32;
pub extern "winmm" fn waveInReset(hwi: HWAVEIN) callconv(.winapi) u32;
pub extern "winmm" fn waveInClose(hwi: HWAVEIN) callconv(.winapi) u32;

pub extern "kernel32" fn Sleep(dwMilliseconds: u32) callconv(.winapi) void;

fn writeWavHeader(writer: *std.Io.Writer, data_size: u32, sample_rate: u32, channels: u16, bits_per_sample: u16) !void {
    try writer.writeAll("RIFF");
    try writer.writeInt(u32, data_size + 36, .little);
    try writer.writeAll("WAVEfmt ");
    try writer.writeInt(u32, 16, .little); // Subchunk1Size
    try writer.writeInt(u16, 1, .little);  // AudioFormat (1 = PCM)
    try writer.writeInt(u16, channels, .little);
    try writer.writeInt(u32, sample_rate, .little);
    const byte_rate = (sample_rate * channels * bits_per_sample) / 8;
    try writer.writeInt(u32, byte_rate, .little);
    const block_align = (channels * bits_per_sample) / 8;
    try writer.writeInt(u16, block_align, .little);
    try writer.writeInt(u16, bits_per_sample, .little);
    try writer.writeAll("data");
    try writer.writeInt(u32, data_size, .little);
}

/// Generates a synthesized 440Hz sine wave WAV file (Mock fallback)
pub fn generateMockWav(file_path: []const u8, duration_seconds: f32, io: std.Io) !void {
    const cwd = std.Io.Dir.cwd();
    const file = try cwd.createFile(io, file_path, .{});
    defer file.close(io);
    
    const sample_rate = 16000;
    const channels = 1;
    const bits_per_sample = 16;
    
    const num_samples = @as(u32, @intFromFloat(duration_seconds * @as(f32, @floatFromInt(sample_rate))));
    const data_size = num_samples * 2; // 16-bit mono = 2 bytes per sample
    
    var write_buf: [1024]u8 = undefined;
    var file_writer = file.writer(io, &write_buf);
    const writer = &file_writer.interface;
    try writeWavHeader(writer, data_size, sample_rate, channels, bits_per_sample);
    
    const freq = 440.0;
    const two_pi = 2.0 * std.math.pi;
    
    var i: u32 = 0;
    while (i < num_samples) : (i += 1) {
        const t = @as(f64, @floatFromInt(i)) / @as(f64, @floatFromInt(sample_rate));
        const angle = two_pi * freq * t;
        const val_f = std.math.sin(angle);
        const val_i = @as(i16, @intFromFloat(val_f * 32767.0));
        try writer.writeInt(i16, val_i, .little);
    }
    try file_writer.flush();
}

/// Records a WAV file from the default recording device (waveIn).
/// If Windows multimedia device is not available, or not on Windows, falls back to generating a mock sine wave.
pub fn recordAudio(file_path: []const u8, duration_seconds: f32, allocator: std.mem.Allocator, io: std.Io) !void {
    if (builtin.os.tag != .windows) {
        std.debug.print("[Audio] Platform is not Windows. Creating mock synthesized journal clip...\n", .{});
        return generateMockWav(file_path, duration_seconds, io);
    }
    
    const sample_rate = 16000;
    const channels = 1;
    const bits_per_sample = 16;
    
    const num_samples = @as(u32, @intFromFloat(duration_seconds * @as(f32, @floatFromInt(sample_rate))));
    const data_size = num_samples * 2;
    
    const buffer = try allocator.alloc(u8, data_size);
    defer allocator.free(buffer);
    @memset(buffer, 0);
    
    const wfx = WAVEFORMATEX{
        .wFormatTag = 1, // WAVE_FORMAT_PCM
        .nChannels = channels,
        .nSamplesPerSec = sample_rate,
        .nAvgBytesPerSec = sample_rate * channels * (bits_per_sample / 8),
        .nBlockAlign = channels * (bits_per_sample / 8),
        .wBitsPerSample = bits_per_sample,
        .cbSize = 0,
    };
    
    var hwi: ?HWAVEIN = null;
    // Open the default input device (0)
    const open_res = waveInOpen(&hwi, 0, &wfx, 0, 0, 0);
    if (open_res != 0) {
        std.debug.print("[Audio] waveInOpen failed (code: {}). No mic connected or access blocked. Falling back to synthetic WAV...\n", .{open_res});
        return generateMockWav(file_path, duration_seconds, io);
    }
    
    const h = hwi.?;
    defer _ = waveInClose(h);
    
    var whdr = WAVEHDR{
        .lpData = buffer.ptr,
        .dwBufferLength = data_size,
        .dwBytesRecorded = 0,
        .dwUser = 0,
        .dwFlags = 0,
        .dwLoops = 0,
        .lpNext = null,
        .reserved = 0,
    };
    
    const prep_res = waveInPrepareHeader(h, &whdr, @sizeOf(WAVEHDR));
    if (prep_res != 0) {
        std.debug.print("[Audio] waveInPrepareHeader failed (code: {}). Falling back to mock audio...\n", .{prep_res});
        return generateMockWav(file_path, duration_seconds, io);
    }
    
    const add_res = waveInAddBuffer(h, &whdr, @sizeOf(WAVEHDR));
    if (add_res != 0) {
        std.debug.print("[Audio] waveInAddBuffer failed (code: {}). Falling back to mock audio...\n", .{add_res});
        return generateMockWav(file_path, duration_seconds, io);
    }
    
    const start_res = waveInStart(h);
    if (start_res != 0) {
        std.debug.print("[Audio] waveInStart failed (code: {}). Falling back to mock audio...\n", .{start_res});
        return generateMockWav(file_path, duration_seconds, io);
    }
    
    std.debug.print("[Audio] Recording native WAV for {d:.2} seconds. Please speak...\n", .{duration_seconds});
    
    const ms_to_sleep = @as(u64, @intFromFloat(duration_seconds * 1000.0));
    if (builtin.os.tag == .windows) {
        Sleep(@intCast(ms_to_sleep));
    } else {
        const timespec = std.posix.timespec{
            .sec = @intCast(ms_to_sleep / 1000),
            .nsec = @intCast((ms_to_sleep % 1000) * 1_000_000),
        };
        _ = std.posix.system.nanosleep(&timespec, null);
    }
    
    _ = waveInStop(h);
    _ = waveInReset(h);
    
    // Save buffer output
    const cwd = std.Io.Dir.cwd();
    const file = try cwd.createFile(io, file_path, .{});
    defer file.close(io);
    
    var write_buf: [1024]u8 = undefined;
    var file_writer = file.writer(io, &write_buf);
    const writer = &file_writer.interface;
    try writeWavHeader(writer, whdr.dwBytesRecorded, sample_rate, channels, bits_per_sample);
    try writer.writeAll(buffer[0..whdr.dwBytesRecorded]);
    try file_writer.flush();
    
    std.debug.print("[Audio] Native WAV successfully recorded ({} bytes) and saved to {s}\n", .{whdr.dwBytesRecorded, file_path});
}
