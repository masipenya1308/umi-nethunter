# Hardware inventory (umi = Xiaomi Mi 10, SM8250 "kona")

Sources: downstream device tree (`LineageOS/android_kernel_xiaomi_sm8250`,
`lineage-23.2`: `umi-sm8250.dtsi`, `umi-pinctrl.dtsi`,
`xiaomi-sm8250-common.dtsi`), the real `dtbo.img` from the partition backup,
and mainline `arch/arm64/boot/dts/qcom/`.

## SoC blocks already in mainline

From `sm8250.dtsi`:

| Block | Compatible |
|---|---|
| clocks/resets | `qcom,sm8250-gcc`, `gpucc`, `videocc`, `dispcc` |
| pinctrl | `qcom,sm8250-tlmm`, LPASS LPI pinctrl |
| interconnect | config/system/aggre1/aggre2/compute/mmss/dc/gem/npu noc, LLCC |
| storage | `qcom,sm8250-ufshc` + `qcom,sm8250-qmp-ufs-phy`, `qcom,sm8250-sdhci` |
| USB | `qcom,sm8250-dwc3` x2, `qcom,sm8250-usb-hs-phy`, `qcom,sm8250-qmp-usb3-dp-phy`, `qcom,sm8250-qmp-usb3-uni-phy` |
| PCIe | 3 controllers + `qmp-gen3x1/gen3x2/modem` PHYs |
| display | DPU (`mdss`), DSI0/DSI1 + PHYs |
| GPU | Adreno 650 + zap shader, `qcom,sm8250-gpucc` |
| video | `qcom,sm8250-venus` |
| remoteproc | ADSP, CDSP, SLPI (`*-pas`), IPCC |
| audio | LPASS WSA/VA/RX/TX macros |
| camera | CCI |
| crypto | QCE |

Upstream SM8250 boards: `sm8250-mtp`, `sm8250-hdk`, `sm8250-sony-xperia-edo-pdx203/206`,
`sm8250-samsung-r8q/x1q`, `sm8250-xiaomi-elish-{boe,csot}`, `sm8250-xiaomi-pipa`.

## umi parts

| Part | umi | Mainline |
|---|---|---|
| SoC | SM8250 (kona) | good |
| PMIC | PM8150, PM8150B, PM8150L, PM8009, PM8008 | good (elish: same set minus 8150B) |
| UFS | `qcom,ufs-phy-qmp-v4` | good |
| USB | dwc3 + `linux,extcon-usb-gpio` role switch | good |
| Wi-Fi/BT | QCA6390 over PCIe | `ath11k` + `qca6390-bt` |
| Panel | **BOE SW43404 AMOLED**, cmd mode, DSC, 1080×2340 | sibling `panel-lg-sw43408.c` exists; needs adaptation |
| Touch | Goodix **GT9889** at i2c `0x5d`; ST FTS also referenced | **no mainline driver** |
| Haptics | Awinic AW8697 | no mainline driver |
| Speaker amp | Cirrus CS35L41 | mainline driver exists |
| Charger | TI BQ2597X + SMB1390, Nuvolta wireless | no mainline driver (optional) |
| NFC | NXP NQ-NCI | `nxp-nci-i2c` exists |
| Fingerprint | FPC1020 / Goodix | none (skip) |
| Camera | 4 sensors | out of scope |

`dtbo.img` (the DT the bootloader really passes) contains, verbatim:
`sw43404 amoled boe fhd+ panel with DSC`, `sw43404 amoled cmd mode dsi boe panel
with DSC`, `goodix@5d`, `fpc1020`, `aw8697`, `bt_qca6390`.

## Notes for DT work

* `umi-pinctrl.dtsi` (downstream) is the source of truth for TLMM pin numbers
  (UART, I2C, SPI, panel reset, touch reset/IRQ).
* Regulator names/voltages are in `xiaomi-sm8250-common.dtsi` and
  `umi-sm8250.dtsi`; mainline uses the `pm8150-rpmh-regulators` bindings.
* Battery data: `fg-gen4-batterydata-umi-{gybm,NVTBM4N}-4780mah.dtsi`.
