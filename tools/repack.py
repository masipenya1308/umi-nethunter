#!/usr/bin/env python3
"""Repack an Android boot image, replacing only what you name.

    repack.py <base.img> <out.img> [--dtb FILE] [--ramdisk FILE] [--cmdline STR]

Kernel, addresses, header version and everything else are copied byte for byte
from the base image, so a test image differs from a known one in exactly one
variable. That is the whole point: with no console on this phone, the only way
to learn anything is to change one thing at a time.

Header v2 (as used by umi), no mkbootimg, no mkvendorimg: the header is a flat
little-endian struct and the payloads are page aligned.
"""
import argparse
import hashlib
import os
import struct

MAGIC = b"ANDROID!"
DTB_MAGIC = b"\xd0\x0d\xfe\xed"

# Offsets inside the v2 header (boot_img_hdr_v2).
OFF_KERNEL_SIZE, OFF_RAMDISK_SIZE, OFF_SECOND_SIZE = 8, 16, 24
OFF_PAGE_SIZE, OFF_HEADER_VERSION = 36, 40
OFF_CMDLINE = 64
CMDLINE_LEN = 512
OFF_ID = 576
OFF_RECOVERY_DTBO_SIZE, OFF_HEADER_SIZE = 1632, 1644
OFF_DTB_SIZE = 1648


def align(n, page):
    return (n + page - 1) // page * page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--dtb")
    ap.add_argument("--ramdisk")
    ap.add_argument("--cmdline")
    args = ap.parse_args()

    with open(args.base, "rb") as f:
        base = f.read()
    if base[:8] != MAGIC:
        raise SystemExit("not an Android boot image: %s" % args.base)

    kernel_size = struct.unpack_from("<I", base, OFF_KERNEL_SIZE)[0]
    ramdisk_size = struct.unpack_from("<I", base, OFF_RAMDISK_SIZE)[0]
    second_size = struct.unpack_from("<I", base, OFF_SECOND_SIZE)[0]
    page = struct.unpack_from("<I", base, OFF_PAGE_SIZE)[0]
    version = struct.unpack_from("<I", base, OFF_HEADER_VERSION)[0]
    if version != 2:
        raise SystemExit("base is header v%d, this tool only handles v2" % version)

    rdtbo_size = struct.unpack_from("<I", base, OFF_RECOVERY_DTBO_SIZE)[0]
    header_size = struct.unpack_from("<I", base, OFF_HEADER_SIZE)[0]

    off = page
    kernel = base[off:off + kernel_size]
    off += align(kernel_size, page)
    ramdisk = base[off:off + ramdisk_size]
    off += align(ramdisk_size, page)
    second = base[off:off + second_size]
    off += align(second_size, page)
    rdtbo = base[off:off + rdtbo_size]
    off += align(rdtbo_size, page)
    dtb = base[off:off + struct.unpack_from("<I", base, OFF_DTB_SIZE)[0]]

    if args.ramdisk:
        with open(args.ramdisk, "rb") as f:
            ramdisk = f.read()
        if ramdisk[:2] != b"\x1f\x8b":
            raise SystemExit("%s is not gzip" % args.ramdisk)
    if args.dtb:
        with open(args.dtb, "rb") as f:
            dtb = f.read()
        if dtb[:4] != DTB_MAGIC:
            raise SystemExit("%s is not a DTB" % args.dtb)

    header = bytearray(base[:header_size])
    if args.cmdline:
        raw = args.cmdline.encode()
        if len(raw) >= CMDLINE_LEN:
            raise SystemExit("cmdline too long")
        header[OFF_CMDLINE:OFF_CMDLINE + CMDLINE_LEN] = raw.ljust(CMDLINE_LEN, b"\0")

    struct.pack_into("<I", header, OFF_KERNEL_SIZE, len(kernel))
    struct.pack_into("<I", header, OFF_RAMDISK_SIZE, len(ramdisk))
    struct.pack_into("<I", header, OFF_SECOND_SIZE, len(second))
    struct.pack_into("<I", header, OFF_RECOVERY_DTBO_SIZE, len(rdtbo))
    struct.pack_into("<I", header, OFF_HEADER_SIZE, header_size)
    struct.pack_into("<I", header, OFF_DTB_SIZE, len(dtb))
    header[OFF_ID:OFF_ID + 32] = hashlib.sha1(
        kernel + ramdisk + second + rdtbo + dtb).digest()

    with open(args.out, "wb") as f:
        f.write(header)
        f.write(b"\0" * (-len(header) % page))
        for blob in (kernel, ramdisk, second, rdtbo, dtb):
            f.write(blob)
            f.write(b"\0" * (-len(blob) % page))

    print("%s: kernel %d, ramdisk %d, dtb %d, %d bytes"
          % (args.out, len(kernel), len(ramdisk), len(dtb),
             os.path.getsize(args.out)))


if __name__ == "__main__":
    main()
