const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Compile Host executable
    const host = b.addExecutable(.{
        .name = "host",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/host.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(host);

    // Compile Client executable
    const client = b.addExecutable(.{
        .name = "client",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/client.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    
    const target_os = target.result.os.tag;
    if (target_os == .windows) {
        client.root_module.linkSystemLibrary("winmm", .{});
        client.root_module.link_libc = true;
    }
    
    b.installArtifact(client);
}
