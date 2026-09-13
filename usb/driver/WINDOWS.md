# Windows 驱动配置

本说明适用于 USB 扫描和同包的 [Wi-Fi setup](../../wifi-setup/README.md)。Wi-Fi setup 通过 USB 配置无线网络，因此也需要正确的 USB 驱动绑定；纯 Wi-Fi 扫描不需要这些 USB 驱动。

## 选择驱动

| 当前情况                                | 配置方式                               | 程序参数            |
| --------------------------------------- | -------------------------------------- | ------------------- |
| 已有 ScanSnap 官方 USB 驱动             | 保留当前绑定，运行前退出 ScanSnap Home | `--backend usbscan` |
| 未安装官方软件，或希望使用通用 USB 驱动 | 按下文用 Zadig 将扫描仪绑定到 WinUSB   | `--backend libusb`  |
| 已经绑定 WinUSB                         | 安装 Python 依赖后直接使用             | `--backend libusb`  |

`usbscan.sys` 和 `winusb.sys` 是同一个 USB 接口的两种绑定。切换为 WinUSB 后，ScanSnap Home 无法通过该接口访问设备；需要官方 USB 功能时按下文恢复。

默认 `--backend auto` 优先尝试 libusb，仅在 Windows 打开失败时回退 usbscan。它不会安装或切换驱动，也不会在扫描或配置过程中更换后端。

## 确认目标设备

连接并开启扫描仪，在设备管理器中找到设备，打开“属性 → 详细信息 → 硬件 ID”，核对：

| 型号           | 硬件 ID                 |
| -------------- | ----------------------- |
| ScanSnap iX110 | `USB\VID_05CA&PID_03C8` |
| ScanSnap iX100 | `USB\VID_04C5&PID_13F4` |

硬件 ID 后面可以带有 `&REV_...`。iX110 的官方驱动名称可能显示为 iX100，选择设备时以 VID/PID 为准。在“驱动程序 → 驱动程序详细信息”中可查看当前使用的是 `usbscan.sys` 还是 `winusb.sys`。

## 使用已有官方驱动

设备已有正常工作的官方 USB 驱动时，无需切换绑定。退出 ScanSnap Home 及其他扫描程序，再安装本项目的 Python 依赖。

需要安装或修复官方驱动时，从设备销售地区的 [ScanSnap 官方软件下载入口](https://www.pfu.ricoh.com/global/scanners/scansnap/support/software/org56.html)选择对应型号与 Windows 系统，按官方安装程序提示操作。本发布包不附带 Ricoh/PFU 官方驱动文件。

扫描时选择 `--backend usbscan`。程序会动态发现 Usbscan 端口，不要假设端口编号固定。USB 扫描和 Wi-Fi setup 都独占设备，不能同时运行。

## 使用 Zadig 配置 WinUSB

这是手动安装或替换当前设备驱动的步骤。先结束扫描及设置作业，退出相关程序。

1. 从 [Zadig 官网](https://zadig.akeo.ie/)下载并运行工具，在 Windows 提示时授予管理员权限。
2. 打开 `Options → List All Devices`，让已安装官方驱动的设备也显示在列表中。
3. 选择扫描仪，核对 `USB ID` 为 `05CA:03C8` 或 `04C5:13F4`。不要选择 USB 集线器或其他设备。
4. 在目标驱动栏选择 **WinUSB**。
5. 核对设备和目标驱动后，点击 `Install Driver` 或 `Replace Driver`；按钮文字随当前绑定状态变化。
6. 等待安装成功，确认当前驱动显示 WinUSB，然后关闭 Zadig。

界面操作依据 [Zadig 官方使用指南](https://github.com/pbatard/libwdi/wiki/Zadig#basic-usage)。此步骤由 Zadig 为本机设备安装绑定，不需要本项目的开发用 INF 模板。本发布包目前不提供已签名的 WinUSB 自动安装包。

## 安装依赖与运行

需要 Python 3.11 或更新版本。以下命令从 `ix100/usb/` 执行：

```powershell
python -m pip install -r requirements.txt
python -B src/scan_direct.py --help
```

`requirements.txt` 提供 PyUSB，以及 Windows 所需的 `libusb-package` 和 libusb DLL，无需另外复制 DLL。安装 Python 依赖不会把扫描仪绑定到 WinUSB；设备绑定仍需完成上述步骤。`--help` 只检查程序入口，不访问设备，也不能证明驱动已经可用。

准备进行实际扫描时，放入纸张并选择与当前绑定相符的一条命令：

```powershell
# 官方 usbscan 驱动
python src/scan_direct.py --backend usbscan

# WinUSB 驱动
python src/scan_direct.py --backend libusb
```

两条扫描命令都会实际访问设备并扫描一页。连续扫描及其他选项见 [USB 使用说明](../README.md)。

Wi-Fi setup 使用自己的依赖与入口。其 `usbscan` 后端只需要 Python 标准库和已绑定的官方驱动；使用 `libusb` 时，在 `ix100/wifi-setup/` 安装该目录的 `requirements.txt`。连接参数放在设备子命令之后，具体用法见 [Wi-Fi setup 说明](../../wifi-setup/README.md)。

## 恢复官方驱动

结束本项目的扫描或配置作业，再在设备管理器中按硬件 ID 找到扫描仪。

- 如果“属性 → 驱动程序 → 回退驱动程序”可用，并且上一版是官方驱动，可使用回退恢复。
- 如果无法回退，使用对应型号的官方安装程序修复或重新安装驱动。已有完整官方驱动包时，也可在“更新驱动程序 → 浏览我的电脑以查找驱动程序”中指定该包的位置。

按 Windows 提示完成安装，只有提示需要时再重启。恢复后确认驱动为 `usbscan.sys`，本项目改用 `--backend usbscan`。手动安装与回退操作参见 [Microsoft 设备管理器驱动说明](https://support.microsoft.com/en-us/windows/update-drivers-through-device-manager-in-windows-ec62f46c-ff14-c91d-eead-d7126dc1f7b6)。

## 常见问题

| 现象                                                | 检查位置                                                                    |
| --------------------------------------------------- | --------------------------------------------------------------------------- |
| Zadig 列表中没有扫描仪                              | 确认 USB 连接、设备已开启，并启用 `List All Devices`                        |
| `libusb-package is required` 或 libusb DLL 无法加载 | 用实际运行入口的同一个 Python 安装 `requirements.txt`                       |
| libusb 找不到或打不开扫描仪                         | 按硬件 ID 确认目标设备及 WinUSB 绑定，并关闭占用设备的程序                  |
| usbscan 找不到端口                                  | 确认当前绑定为官方 `usbscan.sys`；已切换 WinUSB 时改用 `libusb`             |
| 提示设备被占用或访问被拒绝                          | 先结束另一扫描/设置作业并退出官方软件；管理员权限不能解除其他程序的独占占用 |
| WinUSB 安装后官方软件无法通过 USB 扫描              | 按上节恢复官方驱动                                                          |

当前 USB 真机验证范围见 [支持说明](../doc/SUPPORT.md)。驱动安装成功或帮助命令成功不代表所有扫描模式已完成验证。
