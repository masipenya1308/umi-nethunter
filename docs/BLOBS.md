# Firmware blobs

Mainline loads the same vendor firmware files that Android and Droidian use.
Nothing has to be extracted from a proprietary installer: everything is either
on the phone or in an existing partition backup.

## Inventory

| Purpose | Files | Where |
|---|---|---|
| modem DSP | `modem.mdt`, `modem.b*`, `mba.mbn`, `qdsp6sw.mbn` | `D:\umi\backups\pre-stock\modem.img` (extract with `simg2img` if sparse) |
| ADSP / CDSP / SLPI / WPSS | `adsp.mbn`, `cdsp.mbn`, `slpi.mbn`, `wpss.mbn`, `*_dtbs.elf` | `/vendor/firmware` |
| GPU | `a650_sqe.fw`, `a650_gmu.bin`, `a650_zap.mbn` | `/vendor/firmware` |
| Wi-Fi (QCA6390) | `amss.bin`, `m3.bin`, `bdwlan.bin`, `regdb.bin` | `/vendor/firmware` |
| Bluetooth | `QCA6390/*.bin` | `/vendor/firmware` |
| Venus (video) | `venus-5.2/*.mbn` | `/vendor/firmware` |
| IPA | `ipa_fws.mbn` | `/vendor/firmware` |
| Touch | Goodix/ST config + firmware | `/vendor/firmware` |

## Collect from the phone

`scripts/fetch-firmware.sh` runs on the device (root) and produces
`umi-firmware.tar.gz` with the vendor firmware tree. Copy it off over SSH or
MTP, then unpack into the rootfs `/lib/firmware` (Kali uses the same layout).

```bash
scp -i D:\umi\work\ssh\umi_ed25519 root@192.168.1.37:/tmp/umi-firmware.tar.gz .
```

Blobs are **not** a blocker: remoteproc, `ath11k` and Adreno load these files
as-is. The only blob-related work is placing them where the mainline drivers
expect them and naming the subdirectories the way upstream expects
(e.g. `qcom/sm8250/`, `ath11k/QCA6390/hw2.0/`).
