#!/usr/bin/env bash
set -e

# Patch Obsidian's ProcessSingleton to use KEEP_WHITESPACE instead of
# TRIM_WHITESPACE when parsing IPC messages. Without this, binary data
# (V8-serialized additional_data) gets corrupted when it contains bytes
# that match ASCII whitespace (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20).
# See: https://github.com/electron/electron/issues/49801

BINARY="/opt/obsidian/obsidian"

python3 - "$BINARY" << 'PYEOF'
import struct, sys

binary_path = sys.argv[1]

with open(binary_path, "rb") as f:
    data = f.read()

anchor = data.find(b"Wrong message format:")
if anchor < 0:
    print("[patch] WARNING: anchor string not found, skipping")
    sys.exit(0)

# Search for the SplitString call pattern with EITHER value in r9d.
# Pattern prefix (before the r9d immediate):
#   41 b8 01 00 00 00   mov r8d, 1
#   4c 89 f1            mov rcx, r14
#   41 b9               mov r9d, <imm32>
PREFIX = bytes([
    0x41, 0xb8, 0x01, 0x00, 0x00, 0x00,
    0x4c, 0x89, 0xf1,
    0x41, 0xb9,
])
# After prefix: 4 bytes imm32, then 0xe8 (call opcode)

hits = []
pos = 0
while True:
    pos = data.find(PREFIX, pos)
    if pos < 0:
        break
    # Check that byte after imm32 is 0xe8 (call)
    call_byte = pos + len(PREFIX) + 4
    if call_byte < len(data) and data[call_byte] == 0xe8:
        imm = data[pos + len(PREFIX)]  # first byte of imm32
        hits.append((pos, imm))
    pos += 1

if not hits:
    print("[patch] WARNING: SplitString pattern not found, skipping")
    sys.exit(0)

# Find the hit near "Wrong message format:" anchor
target = None
target_imm = None
for hit, imm in hits:
    if len(hits) == 1:
        target, target_imm = hit, imm
        break
    pattern_len = len(PREFIX) + 5  # prefix + imm32 + call opcode
    for off in range(0, 300):
        check = hit + pattern_len + 4 + off
        if check + 7 > len(data):
            break
        if data[check] in (0x48, 0x4c) and data[check+1] == 0x8d:
            if (data[check+2] & 0xc7) == 0x05:
                disp = struct.unpack_from('<i', data, check + 3)[0]
                if check + 7 + disp == anchor:
                    target, target_imm = hit, imm
                    break
    if target is not None:
        break

if target is None:
    if len(hits) == 1:
        target, target_imm = hits[0]
    else:
        print("[patch] WARNING: could not locate correct call site, skipping")
        sys.exit(0)

patch_off = target + len(PREFIX)  # points to first byte of imm32

if target_imm == 0x00:
    print("[patch] Already patched (KEEP_WHITESPACE)")
    sys.exit(0)

if target_imm != 0x01:
    print(f"[patch] WARNING: unexpected value 0x{target_imm:02x}, skipping")
    sys.exit(0)

patched = bytearray(data)
patched[patch_off] = 0x00
with open(binary_path, "wb") as f:
    f.write(patched)

print(f"[patch] Patched TRIM_WHITESPACE -> KEEP_WHITESPACE at offset 0x{patch_off:x}")
PYEOF

echo "[patch] Obsidian binary patch check complete"
