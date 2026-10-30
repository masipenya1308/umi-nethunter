#!/usr/bin/env bash
# Build the M0 initramfs.
#
#   build-initramfs.sh <root-dir> [<out.cpio.gz>]
#
# The root directory is what CONFIG_INITRAMFS_SOURCE points at, so the kernel
# carries its own initramfs and does not depend on the bootloader handing a
# ramdisk over. The optional .cpio.gz is packed as the boot.img ramdisk as
# well, which is harmless and useful for debugging.
#
# busybox comes from the Debian arm64 busybox-static package: nothing is
# compiled here and no arm64 binary is ever executed.
set -euo pipefail

root=${1:?usage: build-initramfs.sh <root-dir> [out.cpio.gz]}
out=${2:-}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

base=https://deb.debian.org/debian/pool/main/b/busybox/
deb=$(curl -fsSL "$base" | grep -o 'busybox-static_[^"]*_arm64\.deb' | sort -u | tail -1)
[ -n "$deb" ] || { echo "cannot find busybox-static arm64 in $base" >&2; exit 1; }
echo "busybox: $deb"

curl -fsSL -o "$work/busybox.deb" "$base$deb"
dpkg-deb -x "$work/busybox.deb" "$work/deb"

# The package installs into /usr/bin (merged-usr), so find it instead of
# assuming a path.
bb=$(find "$work/deb" -type f -name busybox -print -quit)
[ -n "$bb" ] || { echo "busybox binary not found in $deb" >&2; exit 1; }

rm -rf "$root"
mkdir -p "$root"/proc "$root"/sys "$root"/dev "$root"/tmp "$root"/bin
cp "$bb" "$root/bin/busybox"
cp "$here/init" "$root/init"
chmod 0755 "$root/init" "$root/bin/busybox"

# No arm64 execution on the build host, so create the applet links by hand.
for a in sh mount umount mkdir echo sleep cat dmesg ls ln rm exec setsid \
         mknod uname head tail grep poweroff reboot; do
	ln -sf busybox "$root/bin/$a"
done

echo "root: $root"
ls -l "$root" "$root/bin" | sed 's/^/  /'

if [ -n "$out" ]; then
	( cd "$root" && find . -print0 | cpio --null -o -H newc --quiet | gzip -9 ) > "$out"
	echo "wrote $out ($(stat -c %s "$out") bytes)"
fi
