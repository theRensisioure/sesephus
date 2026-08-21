// tools/compress_archive.zig
// Utility that invokes PowerShell's Compress-Archive to zip the project,
// excluding common unnecessary folders (build, tmp, .git, *.obj, *.exe).
// Usage: zig build run -Dtarget=x86_64-windows-gnu -- <output_zip_path>

const std = @import("std");

pub fn main() !void {
    const allocator = std.heap.page_allocator;
    // Determine project root (assume current working directory)
    const cwd = try std.fs.cwd().realpathAlloc(allocator, ".");
    defer allocator.free(cwd);
    // Destination zip path - hard‑coded per requirement
    const zipPath = "C:/Users/bardw/archive/project_archive.zip";
    // Build include pattern list
    var includePaths = std.ArrayList([]const u8).init(allocator);
    defer includePaths.deinit();
    // Include everything under cwd except ignored patterns
    // We'll use PowerShell's -Exclude parameter for simple patterns.
    try includePaths.append(cwd);

    const psCmd = try std.fmt.allocPrint(allocator,
        "Compress-Archive -Path \"{s}\*\" -DestinationPath \"{s}\" -Exclude \"build\*\", \"tmp\*\", \"*.obj\", \"*.exe\", \"*.log\", \"*.git\*\"",
        .{ cwd, zipPath });
    defer allocator.free(psCmd);

    var proc = std.ChildProcess.init(&[_][]const u8{"powershell", "-Command", psCmd}, allocator);
    proc.cwd = cwd;
    proc.stdout_behavior = .Pipe;
    proc.stderr_behavior = .Pipe;
    try proc.spawn();
    const stdout = try proc.stdout.?.readToEndAlloc(allocator, 10_000_000);
    defer allocator.free(stdout);
    const stderr = try proc.stderr.?.readToEndAlloc(allocator, 10_000_000);
    defer allocator.free(stderr);
    const term = try proc.wait();
    if (term != .Exited or term.Exited != 0) {
        std.debug.print("Compress-Archive failed: {s}\n", .{stderr});
        return error.CompressFailed;
    }
    std.debug.print("Archive created at {s}\n", .{zipPath});
}
