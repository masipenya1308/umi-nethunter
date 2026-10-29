#!/usr/bin/env bash
# Build a minimal busybox initramfs with the M0 /init.
# The busybox binary is taken from the Debian arm64 busybox-static package so
# nothing has to be compiled (and no arm64 binary is ever executed here).
set -euo pipefail

out=${1:-initramfs.cpio.gz}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

base=https://deb.debian.org/debian/pool/main/b/busybox/
deb=$(curl -fsSL "$base" | grep -o 'busybox-static_[^"]*_arm64\.deb' | sort -u | tail -1)
[ -n "$deb" ] || { echo "cannot find busybox-static arm64 in $base" >&2; exit 1; }
echo "busybox: $deb"

curl -fsSL -o "$work/busybox.deb" "$base$deb"
dpkg-deb -x "$work/busybox.deb" "$work/root"

root="$work/root"

# The package installs into /usr/bin (trixie merged-usr), so find it instead of
# assuming a path.
bb=$(find "$root" -type f -name busybox -print -quit)
[ -n "$bb" ] || { echo "busybox binary not found in $deb" >&2; exit 1; }

for d in bin sbin lib lib64; do
	[ -L "$root/$d" ] && rm -f "$root/$d"
done
rm -rf "$root/usr" "$root/etc" "$root/sbin"

mkdir -p "$root"/proc "$root"/sys "$root"/dev "$root"/tmp "$root"/bin
cp "$bb" "$root/bin/busybox"
cp "$here/init" "$root/init"
chmod 0755 "$root/init" "$root/bin/busybox"

# No arm64 execution on the build host, so create the applet links by hand.
for a in sh mount umount mkdir echo sleep cat dmesg ls ln rm exec setsid \
         mknod uname head tail grep poweroff reboot; do
	ln -sf busybox "$root/bin/$a"
done

( cd "$root" && find . -print0 | cpio --null -o -H newc --quiet | gzip -9 ) > "$out"
echo "wrote $out ($(stat -c %s "$out") bytes)"
