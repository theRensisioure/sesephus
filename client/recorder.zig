// client/recorder.zig
// Simple command‑line recorder that uses the WinMM waveIn API to capture
// audio into a WAV file (or directly streams to the host). The client
// decides when recording starts via CLI arguments.

const std = @import("std");
const winmm = @cImport({ @cInclude("windows.h"); @cInclude("mmsystem.h"); });
const net = std.net;

pub const Config = struct {
    server_host: []const u8 = "127.0.0.1",
    server_port: u16 = 9000,
    client_id: []const u8 = "default",
    duration_sec: u32 = 5, // default record length
    tags: []const u8 = "",
};

fn writeWavHeader(file: std.fs.File, data_len: u32) !void {
    // Minimal WAV header (PCM 16‑bit mono, 44.1 kHz)
    const sample_rate = 44100;
    const bits_per_sample = 16;
    const num_channels = 1;
    const byte_rate = sample_rate * num_channels * bits_per_sample / 8;
    const block_align = num_channels * bits_per_sample / 8;
    const fmt_chunk_size = 16;
    const audio_format: u16 = 1; // PCM
    var writer = file.writer();
    try writer.writeAll("RIFF");
    try writer.writeInt(u32, 36 + data_len, .little);
    try writer.writeAll("WAVE");
    // fmt sub‑chunk
    try writer.writeAll("fmt ");
    try writer.writeInt(u32, fmt_chunk_size, .little);
    try writer.writeInt(u16, audio_format, .little);
    try writer.writeInt(u16, @intCast(u16, num_channels), .little);
    try writer.writeInt(u32, @intCast(u32, sample_rate), .little);
    try writer.writeInt(u32, @intCast(u32, byte_rate), .little);
    try writer.writeInt(u16, @intCast(u16, block_align), .little);
    try writer.writeInt(u16, @intCast(u16, bits_per_sample), .little);
    // data sub‑chunk
    try writer.writeAll("data");
    try writer.writeInt(u32, data_len, .little);
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    const allocator = &gpa.allocator;
    defer _ = gpa.deinit();

    var args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);
    var cfg = Config{};
    // Simple arg parsing: --host <IP> --port <N> --id <ID> --dur <seconds> --tags <string>
    var i: usize = 1;
    while (i < args.len) : (i += 1) {
        const a = args[i];
        if (std.mem.eql(u8, a, "--host")) { cfg.server_host = args[i+1]; i += 1; }
        else if (std.mem.eql(u8, a, "--port")) { cfg.server_port = @intFromString(u16, args[i+1]) catch 9000; i += 1; }
        else if (std.mem.eql(u8, a, "--id")) { cfg.client_id = args[i+1]; i += 1; }
        else if (std.mem.eql(u8, a, "--dur")) { cfg.duration_sec = @intFromString(u32, args[i+1]) catch 5; i += 1; }
        else if (std.mem.eql(u8, a, "--tags")) { cfg.tags = args[i+1]; i += 1; }
    }

    // Open waveIn device (default)
    var wave_in: winmm.HWAVEIN = undefined;
    var wave_format = winmm.WAVEFORMATEX{
        .wFormatTag = winmm.WAVE_FORMAT_PCM,
        .nChannels = 1,
        .nSamplesPerSec = 44100,
        .nAvgBytesPerSec = 44100 * 2,
        .nBlockAlign = 2,
        .wBitsPerSample = 16,
        .cbSize = 0,
    };
    if (winmm.waveInOpen(&wave_in, winmm.WAVE_MAPPER, &wave_format, 0, 0, winmm.CALLBACK_NULL) != winmm.MMSYSERR_NOERROR) {
        return error.WaveInOpenFailed;
    }
    defer winmm.waveInClose(wave_in);

    const buffer_len = cfg.duration_sec * 44100 * 2; // bytes (16‑bit mono)
    var buffer = try allocator.alloc(u8, buffer_len);
    defer allocator.free(buffer);
    var header = winmm.WAVEHDR{
        .lpData = @ptrCast([*]u8, buffer),
        .dwBufferLength = @intCast(u32, buffer_len),
        .dwBytesRecorded = 0,
        .dwUser = 0,
        .dwFlags = 0,
        .dwLoops = 0,
        .lpNext = null,
        .reserved = 0,
    };
    if (winmm.waveInPrepareHeader(wave_in, &header, @sizeOf(winmm.WAVEHDR)) != winmm.MMSYSERR_NOERROR) {
        return error.PrepareHeaderFailed;
    }
    defer winmm.waveInUnprepareHeader(wave_in, &header, @sizeOf(winmm.WAVEHDR));
    if (winmm.waveInAddBuffer(wave_in, &header, @sizeOf(winmm.WAVEHDR)) != winmm.MMSYSERR_NOERROR) {
        return error.AddBufferFailed;
    }
    if (winmm.waveInStart(wave_in) != winmm.MMSYSERR_NOERROR) {
        return error.StartFailed;
    }
    // Wait until buffer is filled
    while ((header.dwFlags & winmm.WHDR_DONE) == 0) {
        std.time.sleep(100 * std.time.ns_per_ms);
    }
    // Stop device
    _ = winmm.waveInStop(wave_in);

    // Connect to host
    const address = try net.Address.parseIp(cfg.server_host, cfg.server_port);
    var conn = try net.Stream.connect(address);
    defer conn.close();

    // Build protocol header (big‑endian for consistency)
    const client_id_bytes = cfg.client_id;
    const tags_bytes = cfg.tags;
    const header_buf = try std.ArrayList(u8).initCapacity(allocator, 2 + client_id_bytes.len + 8 + 8 + 2 + tags_bytes.len);
    defer header_buf.deinit();
    // client_id_len
    try header_buf.appendSlice(&std.mem.toBytes(@intCast(u16, client_id_bytes.len)).*);
    // client_id
    try header_buf.appendSlice(client_id_bytes);
    // start_time_ms (Unix epoch ms)
    const start_ts = std.time.milliTimestamp();
    try header_buf.appendSlice(&std.mem.toBytes(start_ts).*);
    // wav_len
    try header_buf.appendSlice(&std.mem.toBytes(@intCast(u64, buffer_len)).*);
    // tags_len
    try header_buf.appendSlice(&std.mem.toBytes(@intCast(u16, tags_bytes.len)).*);
    // tags
    if (tags_bytes.len > 0) try header_buf.appendSlice(tags_bytes);

    // Send header then raw wav data
    var writer = conn.writer();
    try writer.writeAll(header_buf.items);
    try writer.writeAll(buffer);
    std.debug.print("Sent {d} bytes of WAV to {s}:{d}\n", .{ buffer_len, cfg.server_host, cfg.server_port });
}
