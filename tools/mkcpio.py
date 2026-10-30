#!/usr/bin/env python3
"""Pack files into a gzip'd newc cpio, like `cpio -o -H newc | gzip -9`.

    mkcpio.py <out.cpio.gz> <file> [<file> ...]

Each file lands at "/<basename>" inside the archive. Used to override one file
of the initramfs that is already built into the kernel:

    mkcpio.py init.cpio.gz scripts/init

The external (boot.img) initramfs is unpacked on top of the built-in one, so
that single entry replaces /init and the rest of the tree - busybox included -
still comes from the kernel. Init changes then cost a repack instead of a
25 minute kernel rebuild.

Pure Python on purpose: the build host has no cpio, and the payloads are tiny.
"""
import gzip
import io
import os
import sys
import time


def newc(name, mode, data, ino, mtime):
    """One newc record: 110 byte ASCII header, name, body, both padded to 4."""
    namez = name.encode() + b"\0"
    fields = (ino, mode, 0, 0, 1, mtime, len(data), 0, 0, 0, 0, len(namez), 0)
    rec = b"070701" + b"".join(b"%08X" % f for f in fields) + namez
    rec += b"\0" * (-len(rec) % 4)
    rec += data
    rec += b"\0" * (-len(data) % 4)
    return rec


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out, srcs = sys.argv[1], sys.argv[2:]
    mtime = int(time.time())
    body = bytearray()
    for ino, src in enumerate(srcs, start=1):
        # 0755 for everything: these are initramfs files (scripts), and a
        # non-executable /init is a panic, not an error message.
        body += newc("/" + os.path.basename(src), 0o100755, open(src, "rb").read(),
                     ino, mtime)
    body += newc("TRAILER!!!", 0, b"", len(srcs) + 1, mtime)

    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(bytes(body))
    with open(out, "wb") as f:
        f.write(raw.getvalue())
    print("%s: %d file(s), %d bytes -> %d bytes gz"
          % (out, len(srcs), len(body), os.path.getsize(out)))


if __name__ == "__main__":
    main()
