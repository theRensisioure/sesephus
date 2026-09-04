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

    const test_step = b.step("test", "Run journal/rhythm/help unit tests");
    const test_files = [_][]const u8{
        "src/commands/journal.zig",
        "src/commands/rhythm.zig",
        "src/commands/help_text.zig",
    };
    for (test_files) |src| {
        const unit = b.addTest(.{
            .root_module = b.createModule(.{
                .root_source_file = b.path(src),
                .target = target,
                .optimize = optimize,
            }),
        });
        const run_unit = b.addRunArtifact(unit);
        test_step.dependOn(&run_unit.step);
    }
}