# 驱动与设备权限

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

扫描操作见[使用说明](../README.md)。USB 扫描和同包的 Wi-Fi setup 共用这些驱动准备条件。

## Windows

完整步骤见 [Windows 驱动配置](WINDOWS.md)：确认硬件 ID、使用已有官方驱动、通过 Zadig 配置 WinUSB、安装 Python 依赖，以及恢复官方驱动。

已有官方驱动时使用 `--backend usbscan`，运行前退出 ScanSnap Home；Python 依赖仍按各组件说明安装。已有 WinUSB 绑定时使用 `--backend libusb`。

支持的 USB ID 为 iX110 `05CA:03C8` 和 iX100 `04C5:13F4`。iX110 的官方驱动名称可能显示为 iX100。程序会动态查找端口，无需固定 Usbscan 编号。

当前发布目录不附带已签名的 WinUSB 安装包。WinUSB 与官方 usbscan 是同一接口的不同绑定；切换为 WinUSB 后，ScanSnap Home 无法通过该 USB 接口访问设备。

## Linux

安装系统 libusb 运行库后，从 `ix100/usb/` 执行：

```bash
sudo install -m 0644 driver/60-scansnap-ix100.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

重新连接扫描仪。桌面环境不支持 `TAG+=uaccess` 时，按本机用户组调整[权限规则](60-scansnap-ix100.rules)。

## macOS

使用 Homebrew 时执行 `brew install libusb`，再安装组件的 Python 依赖。
