# Plan

Goal: a NetHunter Pro-style image for umi — mainline kernel, Kali arm64 rootfs,
Phosh, no Android HALs. Staged so that every step is testable and reversible.

## Constraints

* Device is **A-only** (no A/B slots): `boot`, `dtbo`, `vbmeta`, `recovery`
  are single partitions. A bad `boot` is recovered with `fastboot flash`.
* No UART pads. The only console is USB: dwc3 in peripheral mode + `gserial`
  (CDC-ACM). This already works on the device — the Droidian MTP gadget is the
  same dwc3 stack, just a different function.
* Boot image layout, verified from the backups: `header_version 2`,
  `page_size 4096`, kernel 55 MB, ramdisk 16 MB. Stock MIUI uses v0/2048, so
  the bootloader accepts both.
* `dtbo` must not contain the stock overlay when our own DT is used
  (`fastboot erase dtbo`), same as the NetHunter Pro sdm845 instructions.

## Milestones

### M0 — mainline boots to a shell over USB  (built, not yet tested on device)

Scope: `Image` + `sm8250-xiaomi-umi.dtb` + busybox initramfs, packed into
`boot.img`. No storage, no display, no PMIC regulators beyond what the
bootloader leaves enabled.

Deliverables:
* `dts/sm8250-xiaomi-umi.dts` — memory, USB1 (dwc3 + HS PHY, peripheral mode).
* `configs/umi-m0.config` — gadget/configfs/initramfs options.
* CI job producing `boot-umi-mainline.img`.

Success: `dmesg` and a shell appear on the PC's COM port.

Known risks: `gcc` clock controller not coming up without RPMh votes; dwc3
needing the QMP PHY even in HS mode; the bootloader refusing a v2 image.

### M1 — storage

Enable `ufs_mem_hc` + `ufs_mem_phy` (copy from elish), mount the Kali rootfs
from `userdata` or an image on it. Requires the rootfs build, which is the next
work item after M0 proves the kernel.

### M2 — display and touch

* Panel: BOE SW43404 AMOLED, cmd mode, DSC, 1080×2340. Mainline has the sibling
  `panel-lg-sw43408.c`; the init sequence is in the downstream
  `dsi-panel-sw43404*` dtsi (node `dsi_sw43404_amoled_cmd`).
* Touch: Goodix GT9889 (`goodix@5d` in the real dtbo). No mainline driver;
  the downstream driver has to be ported to the mainline input API, or the
  ST FTS variant if this unit has that controller instead.

### M3 — Wi-Fi and Bluetooth

PCIe0 + QCA6390: `ath11k_pci` + `qca6390-bt` over serdev, firmware from
`/vendor/firmware`. elish already does exactly this.

### M4 — power and audio

`pm8150`/`pm8150b`/`pm8150l`/`pm8009` RPMh regulators, `simple-battery`,
CS35L41 speaker amps, WCD9385 + LPASS.

### M5 — telephony

IPA, QMI, rmnet, rmtfs. Least certain part of the whole project; several
mainline phone ports never get here.

## Test procedure

1. `fastboot getvar current-slot`, record it.
2. Try `fastboot boot boot-umi-mainline.img` first (writes nothing).
3. If that is unsupported: `fastboot flash boot ...`, `fastboot erase dtbo`.
4. Watch for the CDC-ACM port; open it at 115200.
5. If nothing appears within ~60 s, power-cycle into fastboot and flash the
   backups back.

## Rollback

```bash
fastboot flash boot   D:\umi\backups\pre-flash-20261027\boot-before-flash.img
fastboot flash dtbo   D:\umi\backups\pre-stock\dtbo.img
fastboot flash vbmeta D:\umi\backups\pre-stock\vbmeta.img
fastboot reboot
```

`userdata` (Droidian rootfs) is never touched by these steps.
