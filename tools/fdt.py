#!/usr/bin/env python3
"""Minimal Flattened Device Tree reader/patch helper.

    fdt.py dump  <file.dtb> [path]      print a subtree
    fdt.py get   <file.dtb> <path> <prop>
    fdt.py find  <file.dtb> <prop-substring>

Written because the build host has no dtc/libfdt and reading a DTB by eye with
hexdump is how wrong conclusions get made. Read-only: patching a compiled DTB
is done by repack.py's sibling tools, not here.

FDT layout (v17): header, memory reservation map, struct block, strings block.
The struct block is a token stream: BEGIN_NODE(name), PROP(len, nameoff, value),
END_NODE, NOP, END.
"""
import struct
import sys

FDT_MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


class Node:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.props = {}          # name -> bytes
        self.children = []

    @property
    def path(self):
        if self.parent is None:
            return "/"
        p = self.parent.path
        return (p if p.endswith("/") else p + "/") + self.name

    def child(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def find(self, path):
        if path in ("/", ""):
            return self
        node = self
        for part in path.strip("/").split("/"):
            node = node.child(part)
            if node is None:
                return None
        return node

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def parse(data):
    magic, totalsize, off_struct, off_strings = struct.unpack_from(">IIII", data, 0)
    if magic != FDT_MAGIC:
        raise SystemExit("not a DTB (magic %08x)" % magic)
    strings = data[off_strings:]
    pos = off_struct
    root = None
    cur = None
    while True:
        (tok,) = struct.unpack_from(">I", data, pos)
        pos += 4
        if tok == BEGIN_NODE:
            end = data.index(b"\0", pos)
            name = data[pos:end].decode(errors="replace")
            pos += ((end - pos) // 4 + 1) * 4
            node = Node(name, cur)
            if cur is None:
                root = node
            else:
                cur.children.append(node)
            cur = node
        elif tok == END_NODE:
            cur = cur.parent
        elif tok == PROP:
            length, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            end = strings.index(b"\0", nameoff)
            pname = strings[nameoff:end].decode(errors="replace")
            cur.props[pname] = data[pos:pos + length]
            pos += (length + 3) & ~3
        elif tok == NOP:
            pass
        elif tok == END:
            break
        else:
            raise SystemExit("bad token %d at %d" % (tok, pos - 4))
    return root


def show_prop(name, val):
    if not val:
        return "%s" % name
    if len(val) == 4:
        return "%s = <0x%08x>" % (name, struct.unpack(">I", val)[0])
    if len(val) % 4 == 0 and len(val) <= 16:
        return "%s = <%s>" % (name, " ".join("0x%08x" % w
                                             for w in struct.unpack(">%dI" % (len(val) // 4), val)))
    if val[-1:] == b"\0":
        try:
            s = val[:-1].decode()
            if all(32 <= ord(c) < 127 for c in s):
                return '%s = "%s"' % (name, s)
        except UnicodeDecodeError:
            pass
    if len(val) <= 8:
        return "%s = [%s]" % (name, val.hex())
    return "%s = <%d bytes>" % (name, len(val))


def dump(node, indent=0):
    pad = "  " * indent
    print("%s%s {" % (pad, node.name or "/"))
    for k, v in node.props.items():
        print("%s  %s;" % (pad, show_prop(k, v)))
    for c in node.children:
        dump(c, indent + 1)
    print("%s};" % pad)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    data = open(path, "rb").read()
    root = parse(data)
    if cmd == "dump":
        node = root.find(sys.argv[3]) if len(sys.argv) > 3 else root
        if node is None:
            raise SystemExit("no such node")
        dump(node)
    elif cmd == "get":
        node = root.find(sys.argv[3])
        if node is None or sys.argv[4] not in node.props:
            raise SystemExit("not found")
        print(show_prop(sys.argv[4], node.props[sys.argv[4]]))
    elif cmd == "find":
        needle = sys.argv[3]
        for n in root.walk():
            for k, v in n.props.items():
                if needle in k:
                    print("%-50s %s" % (n.path, show_prop(k, v)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
