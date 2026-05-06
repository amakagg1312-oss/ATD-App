"""Generate placeholder app icons (256x256 ICO for Windows, ICNS for macOS).

Usage: python scripts/make_icons.py <output-dir>

Skips creation if the icon file already exists (so real icons placed in
build-assets/ are never overwritten by the CI placeholder).
"""
import os
import struct
import sys
import zlib


R, G, B = 30, 50, 100  # placeholder color (dark blue)


def make_png(size):
    row = b"\x00" + bytes([R, G, B, 255]) * size
    idat = zlib.compress(row * size)

    def ch(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", ihdr) + ch(b"IDAT", idat) + ch(b"IEND", b"")


def make_ico(png_256):
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_256), 22)
    return header + entry + png_256


def make_icns(png_256, png_512):
    def entry(tag, data):
        return tag + struct.pack(">I", len(data) + 8) + data

    body = entry(b"ic08", png_256) + entry(b"ic09", png_512)
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "frontend/build-assets"
    os.makedirs(out_dir, exist_ok=True)

    ico_path = os.path.join(out_dir, "icon.ico")
    if not os.path.exists(ico_path):
        png256 = make_png(256)
        with open(ico_path, "wb") as f:
            f.write(make_ico(png256))
        print(f"Created {ico_path}")
    else:
        print(f"Skipped {ico_path} (already exists)")

    icns_path = os.path.join(out_dir, "icon.icns")
    if not os.path.exists(icns_path):
        png256 = make_png(256)
        png512 = make_png(512)
        with open(icns_path, "wb") as f:
            f.write(make_icns(png256, png512))
        print(f"Created {icns_path}")
    else:
        print(f"Skipped {icns_path} (already exists)")


if __name__ == "__main__":
    main()
