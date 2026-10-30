# State of the port — 2026-10-30

Where the umi port actually stands, what is proven, what is guessed, and the
exact next experiments. Written while the device is away, so that the next
session starts at the first real unknown instead of re-deriving it.

Milestone: **M0** — mainline kernel boots to a shell on the USB CDC-ACM console.
Status: **not reached.** The kernel boots, `/init` runs, nothing enumerates on
the host.

## What is proven

Each item below was observed, not inferred.

| Fact | Evidence |
| --- | --- |
| Kernel boots and reaches `/init` | An init that reboots after a diagnostic delay produced exactly the delay; an init that never reboots kept the phone alive for minutes (t15/t16). |
| `fastboot flash boot` works, `fastboot boot` does not | `Failed to load/authenticate boot image` for a known-good image. |
| `fastboot fetch <partition>` works | `fastboot fetch boot` pulled the live 48 MB boot partition back to the host. |
| The host never sees a USB device | 5-minute `Get-PnpDevice` + `SerialPort` poll during a boot: the bootloader interface disappears at handover and nothing replaces it. No `VID_0000` "descriptor request failed" entry either, so this is not a failed enumeration — the D+ pull-up never happens. |
| The phone reboots on its own even with an init that cannot reboot | t16 init loops forever and never calls reboot; the device still restarted ~3 min after boot. So the reset comes from the kernel or the PMIC, not from userspace. |
| All t1..t13 test images carried the kernel from the first build | Kernel SHA-256 identical across `boot-umi-mainline.img`, `t13`, `t12`, `t1`. Config changes made after 04:49 never reached the device. |

## The bug that was hiding in plain sight

`CONFIG_TYPEC_QCOM_PMIC=m` in every image up to and including CI run 41037207566.

The fragment asked for `=y`. Kconfig refused, quietly:

```
config TYPEC_QCOM_PMIC
        depends on DRM || DRM=n
```

arm64 defconfig has `DRM=m`, so the symbol is capped at `=m`. `merge_config.sh`
demoted it, `olddefconfig` kept the demotion, the build stayed green, and the
image shipped with **no Type-C driver at all** — the same dead end as t8, this
time wearing a passing CI run.

Fixed by `# CONFIG_DRM is not set` (M0 has no display driver anyway) and by
asserting the symbol in the workflow, so a demotion now fails the build instead
of the phone.

Current image (`m0-d23d340`) therefore has, and this is verified inside the
artifact: `CONFIG_TYPEC_QCOM_PMIC=y`, `CONFIG_TYPEC_TCPM=y`, `CONFIG_QCOM_WDT=y`,
`CONFIG_DRM is not set`.

## What is still unknown

1. **Does dwc3 probe at all?** If `/sys/class/udc` is empty, everything about
   pull-ups, roles and TCPM is irrelevant: the failure is one step earlier, in
   the PHY/regulator/clock chain.
2. **Why does the phone reset ~3 min in?** The AP watchdog is the obvious
   candidate, but `CONFIG_QCOM_WDT=y` plus `WATCHDOG_HANDLE_BOOT_ENABLED=y`
   plus init holding `/dev/watchdog` open should have covered it. Either the
   watchdog driver never probes, or this is a panic (`panic=10` in the cmdline)
   somewhere new — TCPM is the newest suspect.
3. **Do the RPMh regulators register?** `usb_1_hsphy` needs
   `vreg_l5a_0p88` / `vreg_l12a_1p8` / `vreg_l2a_3p1`; the Type-C block needs
   `vreg_l2a_3p1` as `vdd-pdphy-supply`. If `regulators-0` under `&apps_rsc`
   fails to register them, both the PHY and TCPM defer forever and dwc3 never
   appears. The lookup goes through cmd-db (SMEM), not through the PMIC node,
   and `sm8250.dtsi` already provides cmd-db and smem — so this *should* work,
   but it has never been confirmed on the device.

## Why we are blind, and the way out

The USB console is the only output channel, and it is the thing being debugged.
Everything so far was reported through reboot timing, which is why three
different failures looked identical for two days.

Two durable fixes, in order of value:

0. **The panel itself.** See "The screen is a log channel" below — the
   bootloader's splash surface is still live and `simple-framebuffer` costs one
   DTS node. If it works, it is a full text console with zero new drivers.
1. **UFS (M1).** Mainline supports `ufs_mem_hc` on sm8250 and elish already
   enables it. Once UFS probes, init can `dd` dmesg onto a scratch partition
   and the host can read it with `fastboot fetch <partition>` — no USB, no
   display, no guesswork. UFS is needed for the Kali rootfs anyway, so this is
   not a detour.
2. **Reboot-timing ladder.** Cheap, already built, one number per flash. Good
   enough to bisect the chain in a handful of boots.

## The screen is a log channel (found 2026-10-30, late)

The panel goes dark after the MI logo, which looked like a dead display. It is
not: nothing in mainline touches MDSS, so the bootloader's splash surface at
**0x9c000000** (`cont_splash_region`, 0x2300000 bytes, confirmed in the stock
DT) is still being scanned out. elish — same SoC, same ABL splash mechanism,
same address — hands exactly that region to `simple-framebuffer` and gets a
text console with no DSI driver, no DPU and no DRM.

umi now does the same (`chosen/framebuffer@9c000000`, 1080x2340, stride 4320,
`a8r8g8b8`), plus `ramoops` at **0xb0000000** (4 MiB, the window elish uses,
verified free against umi's stock reserved-memory).

fbdev rather than simpledrm on purpose: DRM has to stay off so that
`TYPEC_QCOM_PMIC` can be built in (see above). `CONFIG_FB_SIMPLE` refuses to
build alongside `DRM_SIMPLEDRM`, which costs nothing here.

If the panel is live, the whole dmesg is on the phone's screen about a second
into boot and this document's "why we are blind" section stops applying.

## Next experiment — ready to flash

**`out/t18-screen.img`** — kernel `765a7ae` (fbcon + pstore + TCPM + WDT), DTB
with the framebuffer and ramoops, and an init that reports, waits 60 s so the
screen can be photographed, and only then reboots with a code.

```bash
fastboot flash boot D:\umi\work\umi-nethunter\out\t18-screen.img
fastboot reboot
```

Read the phone's screen first. If it shows text, stop: the log is right there,
and the interesting lines are `dwc3`, `usb_1`, `hsphy`, `typec`, `regulator`
and `pstore`. If it stays black, time the reboot from power-on:

| Interval | Meaning | Next step |
| --- | --- | --- |
| ~80 s | No `/sys/class/udc`, all three PHY rails registered | Chain dies above the regulators: gcc/GDSC/clocks. Try `dr_mode = "peripheral"` (no role switch) to remove TCPM from the picture. |
| ~90 s | No `/sys/class/udc`, at least one rail missing | `regulators-0` is not registering. Copy elish's full pm8150 regulator tree. |
| ~100 s | UDC exists, no `/dev/ttyGS0` | Gadget bind failed — configfs/composite, not PHY. |
| ~110 s | `/dev/ttyGS0` exists, UDC state not attached | Pull-up refused: role or PHY power. `select-utmi`, QMP PHY and TCPM matter here. |

(60 s dwell + 10 s boot + the code itself. ~15 s still means a panic.)

Older fallback: `out/t17-ladder.img`, same ladder without the dwell and without
the screen.

## Candidate fixes to try after the ladder

* **Full PMIC regulator tree.** elish includes `pm8150.dtsi`, `pm8150b.dtsi`,
  `pm8150l.dtsi`, `pm8009.dtsi` and defines `vph_pwr` plus the `vdd-s*`/
  `vdd-l*` parent supplies. We include only `pm8150b.dtsi` and define three
  LDOs with no parents. Copying elish's `regulators-0` wholesale removes the
  difference.
* **`dr_mode = "peripheral"` without `usb-role-switch`.** `udc->vbus` defaults
  to `true` at UDC registration (`drivers/usb/gadget/udc/core.c:1415`), so a
  plain peripheral gadget connects at bind time and needs no role from anyone.
  This isolates "PHY is fine, role is missing" from "PHY is broken".
* **QMP PHY alongside the HS PHY.** `qcom,select-utmi-as-pipe-clk` only
  rearranges QSCRATCH (`PIPE_UTMI_CLK_SEL`); it does not create a clock. If
  dwc3's core soft reset still does not clear, wiring `usb_1_qmpphy` as
  `usb3-phy` is the alternative elish does *not* need but umi might.

## Hardware notes worth not re-learning

* `usb_1_hsphy` is `phy@88e3000`; `phy@88e4000` is USB2's HS PHY and stays
  disabled. The QMP PHY for USB1 is `phy@88e8000`.
* The panel is a command-mode DSI AMOLED: it keeps showing the bootloader
  splash until a DSI driver feeds it. There is nothing to put a framebuffer on,
  so `console=tty0` is decorative.
* `panic=10` is in the boot image cmdline. A panic therefore reboots the phone
  after 10 s — indistinguishable from a short diagnostic delay without care.

## Reproducing the build

CI: `.github/workflows/build.yml`, push to `main`, artifacts
`umi-nethunter-m0` (boot image + `kernel.config` + DTB). Fetch an artifact with
the GitHub token already in the git credential store.

Local repack (kernel unchanged, new `/init` or DTB), ~2 s instead of ~12 min:

```bash
python tools/mkcpio.py out/x.cpio.gz <dir>/init
python tools/repack.py out/m0-<sha>/boot-umi-mainline.img out/x.img \
    --dtb out/m0-<sha>/sm8250-xiaomi-umi.dtb --ramdisk out/x.cpio.gz
```

`mkcpio.py` packs by basename, so the file must be called `init` to land on
`/init`. `.gitattributes` pins LF for `scripts/init` — a CRLF `/init` is a
panic, not an error message.

## Rollback

```bash
fastboot flash boot D:\umi\backups\pre-nethunter-20261029\boot.img
fastboot flash dtbo D:\umi\backups\pre-nethunter-20261029\dtbo.img
fastboot flash vbmeta D:\umi\backups\pre-nethunter-20261029\vbmeta.img
```
