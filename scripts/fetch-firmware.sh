#!/bin/sh
# Collect the vendor firmware blobs needed by a mainline kernel.
# Run as root on the phone (Droidian), then copy /tmp/umi-firmware.tar.gz off.
set -eu

out=${1:-/tmp/umi-firmware.tar.gz}
list=""

for d in /vendor/firmware /vendor/firmware_mnt/image /vendor/lib/firmware /system/vendor/firmware; do
	[ -d "$d" ] && list="$list $d"
done

if [ -z "$list" ]; then
	echo "no vendor firmware directories found" >&2
	exit 1
fi

echo "collecting:$list"
# shellcheck disable=SC2086
tar -czf "$out" $list 2>/dev/null || tar -czf "$out" --ignore-failed-read $list

ls -lh "$out"
echo "copy it off with:"
echo "  scp -i <key> root@<phone>:$out ."
