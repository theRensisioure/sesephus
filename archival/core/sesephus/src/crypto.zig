const std = @import("std");
const builtin = @import("builtin");
const HmacSha256 = std.crypto.auth.hmac.sha2.HmacSha256;
const ChaCha20Poly1305 = std.crypto.aead.chacha_poly.ChaCha20Poly1305;

pub extern "kernel32" fn GetSystemTimeAsFileTime(lpSystemTimeAsFileTime: *u64) callconv(.winapi) void;

threadlocal var prng: ?std.Random.DefaultPrng = null;

/// Generates pseudo-random bytes seeded using precise system time
pub fn getRandomBytes(buffer: []u8) void {
    if (prng == null) {
        var seed: u64 = 0;
        if (builtin.os.tag == .windows) {
            GetSystemTimeAsFileTime(&seed);
        } else {
            var ts: std.posix.timespec = undefined;
            _ = std.posix.system.clock_gettime(std.posix.CLOCK.REALTIME, &ts);
            seed = @as(u64, @intCast(ts.sec)) * std.time.ns_per_s + @as(u64, @intCast(ts.nsec));
        }
        prng = std.Random.DefaultPrng.init(seed);
    }
    prng.?.random().bytes(buffer);
}

/// Derives a 32-byte key from a password and salt using PBKDF2-HMAC-SHA256
pub fn deriveKey(password: []const u8, salt: []const u8, key_out: *[32]u8) !void {
    try std.crypto.pwhash.pbkdf2(key_out, password, salt, 10000, HmacSha256);
}

/// Encrypts plaintext using ChaCha20-Poly1305
pub fn encrypt(allocator: std.mem.Allocator, plaintext: []const u8, key: [32]u8, nonce: [12]u8, tag_out: *[16]u8) ![]u8 {
    const ciphertext = try allocator.alloc(u8, plaintext.len);
    errdefer allocator.free(ciphertext);
    
    ChaCha20Poly1305.encrypt(ciphertext, tag_out, plaintext, "", nonce, key);
    return ciphertext;
}

/// Decrypts ciphertext using ChaCha20-Poly1305
pub fn decrypt(allocator: std.mem.Allocator, ciphertext: []const u8, key: [32]u8, nonce: [12]u8, tag: [16]u8) ![]u8 {
    const plaintext = try allocator.alloc(u8, ciphertext.len);
    errdefer allocator.free(plaintext);
    
    try ChaCha20Poly1305.decrypt(plaintext, ciphertext, tag, "", nonce, key);
    return plaintext;
}

test "derive key and encrypt/decrypt roundtrip" {
    const allocator = std.testing.allocator;
    const password = "my_super_secret_password";
    
    var salt: [16]u8 = undefined;
    getRandomBytes(&salt);
    
    var key: [32]u8 = undefined;
    try deriveKey(password, &salt, &key);
    
    const plaintext = "Hello, Sesephus! Secure local-first journal.";
    
    var nonce: [12]u8 = undefined;
    getRandomBytes(&nonce);
    
    var tag: [16]u8 = undefined;
    const ciphertext = try encrypt(allocator, plaintext, key, nonce, &tag);
    defer allocator.free(ciphertext);
    
    const decrypted = try decrypt(allocator, ciphertext, key, nonce, tag);
    defer allocator.free(decrypted);
    
    try std.testing.expectEqualStrings(plaintext, decrypted);
}
