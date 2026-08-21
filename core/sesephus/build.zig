const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const sesefus = b.addExecutable(.{
        .name = "sesefus",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });

    const target_os = target.result.os.tag;
    if (target_os == .windows) {
        sesefus.root_module.linkSystemLibrary("winmm", .{});
        sesefus.root_module.link_libc = true;
    }

    b.installArtifact(sesefus);
}