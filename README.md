# umi-nethunter

Kali NetHunter Pro bring-up for the **Xiaomi Mi 10 (umi, SM8250)**.

This is a separate project from the Droidian port
([`umi-droidian-build`](https://github.com/masipenya1308/umi-droidian-build)).
Nothing here modifies that repository or the running Droidian system: the goal
is a **pure Kali NetHunter Pro** image (mainline kernel, no Android HALs, no
libhybris, no chroot), exactly the way NetHunter Pro is built for the officially
supported devices.

## Status

**M0 builds, not yet booted.** CI compiles mainline v6.12 with our umi device
tree, packs a busybox initramfs and produces `boot-umi-mainline.img`
(header v2 / 4096-byte pages, the layout the LineageOS image on this device
already uses). The device tree compiles cleanly against mainline, which is the
first real result. Next step is flashing it and looking for the USB console.
See [`docs/PLAN.md`](docs/PLAN.md).

## Why this is possible at all

* SM8250 is already supported in mainline (`arch/arm64/boot/dts/qcom/sm8250.dtsi`):
  GCC/GPUCC/VIDEOCC/DISPCC, TLMM, interconnect + LLCC, UFS, two dwc3 + PHYs,
  PCIe x3, DPU + DSI0/1, Adreno 650, Venus, ADSP/CDSP/SLPI, LPASS, CCI, QCE.
* Xiaomi already has mainline SM8250 devices: Pad 5 (`elish`) and Pad 6
  (`pipa`). `sm8250-xiaomi-elish-common.dtsi` is the closest template — same
  vendor, same bootloader conventions, same PMIC family, QCA6390 Wi-Fi.
* The downstream kernel source for umi is public
  (`LineageOS/android_kernel_xiaomi_sm8250`, branch `lineage-23.2`) and contains
  the device tree, panel init sequence and touch driver.
* All firmware blobs are on the phone (`/vendor/firmware`) or in the existing
  partition backups.

What is missing is device-tree work plus two drivers (panel, touch). See
[`docs/HARDWARE.md`](docs/HARDWARE.md) for the full inventory.

## Layout

```
dts/sm8250-xiaomi-umi.dts     M0 device tree (USB console only, untested)
configs/umi-m0.config         kernel config fragment for M0
scripts/build-initramfs.sh    busybox initramfs with a USB CDC-ACM shell
scripts/init                  initramfs /init (gadget setup + shell)
scripts/fetch-firmware.sh     run on the phone, collect the vendor blobs
.github/workflows/build.yml   mainline + DT + initramfs -> boot.img
docs/PLAN.md                  milestones, test procedure, rollback
docs/HARDWARE.md              what the phone has and what mainline covers
docs/BLOBS.md                 firmware inventory and how to get it
```

## Build

CI does everything on push. Locally, the same steps:

```bash
git clone --depth 1 --branch v6.12 \
  https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git linux
cp dts/sm8250-xiaomi-umi.dts linux/arch/arm64/boot/dts/qcom/
make -C linux ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
linux/scripts/kconfig/merge_config.sh -m linux/.config configs/umi-m0.config
make -C linux ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C linux -j"$(nproc)" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image dtbs
bash scripts/build-initramfs.sh initramfs.cpio.gz
```

Packing uses AOSP `mkbootimg` with the parameters this device actually boots
with (verified against the LineageOS boot image in the backups):
`--header_version 2 --pagesize 4096 --dtb ...`.

## Test (M0)

The device is A-only, so everything is reversible with `fastboot`:

```bash
fastboot getvar current-slot        # record it
fastboot flash boot boot-umi-mainline.img
fastboot erase dtbo                 # our DT is inside boot.img
fastboot reboot
```

Then watch for a new CDC-ACM device on the PC (`/dev/ttyACM0`, Windows: a COM
port). Rollback:

```bash
fastboot flash boot    D:\umi\backups\pre-flash-20261027\boot-before-flash.img
fastboot flash dtbo    D:\umi\backups\pre-stock\dtbo.img
fastboot flash vbmeta  D:\umi\backups\pre-stock\vbmeta.img
```

`fastboot boot boot-umi-mainline.img` is worth trying first: if this bootloader
supports it, nothing has to be written at all.

## Hard rules

* No changes to the Droidian repository, its CI, or the phone's rootfs.
* Nothing is flashed before the partition backups in `D:\umi\backups` are
  verified; the device must stay restorable to stock MIUI and to the working
  Droidian image.
* Camera is explicitly out of scope. Telephony is a stretch goal (M5).
