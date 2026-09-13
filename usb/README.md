# ScanSnap iX100/iX110 USB 扫描

独立 Python 驱动，通过 USB 保存单面彩色、灰度或黑白 BMP。支持单页扫描和放纸自动扫描的连续作业，不加载官方用户态 DLL。

以下命令均从 `ix100/usb/` 执行。需要 Python 3.11 或更新版本。

## 安装

```powershell
python -m pip install -r requirements.txt
```

| 环境                       | 准备工作                                                       |
| -------------------------- | -------------------------------------------------------------- |
| Windows，已有官方 USB 驱动 | 使用 `--backend usbscan`，运行前退出 ScanSnap Home             |
| Windows，已绑定 WinUSB     | 使用 `--backend libusb`                                        |
| Windows，未安装官方驱动    | 按 [Windows 驱动配置](driver/WINDOWS.md)使用 Zadig 配置 WinUSB |
| Linux/macOS                | 安装系统 libusb 运行库；Linux 还需配置设备权限                 |

Windows 安装、切换与恢复步骤见 [Windows 驱动配置](driver/WINDOWS.md)，Linux 权限说明见 [driver/README.md](driver/README.md)。默认 `auto` 优先打开 libusb，仅在 Windows 打开失败时回退 usbscan。扫描中不会自动切换后端。

## 扫描

连接扫描仪并放入纸张后，执行单页扫描：

```powershell
python src/scan_direct.py
```

连续扫描会立即等纸，每次放纸自动扫描并保存独立 BMP：

```powershell
python src/scan_interactive.py
```

按回车结束，当前页会读完并保存；Ctrl-C 中止当前页并结束作业。不要同时运行两个扫描程序。

默认输出到本目录的 `output/`，缺少目录时自动创建。也可指定位置：

```powershell
python src/scan_direct.py output/page.bmp
python src/scan_interactive.py --output-dir output
```

## 选项

两个扫描入口共用以下选项：

| 选项                           | 用途与默认值                                      |
| ------------------------------ | ------------------------------------------------- |
| `--dpi 300`                    | 扫描分辨率，默认 300 DPI, 最高 600                |
| `--color-mode color`           | `color` 彩色、`gray` 灰度、`mono` 黑白，默认彩色  |
| `--backend auto`               | `auto`、`usbscan` 或 `libusb`                     |
| `--height 42307`               | 高度上限，单位 1/1200 英寸；型号参考范围 1～42307 |
| `--overscan` / `--no-overscan` | 扩展扫描宽度，默认开启，不改变输入高度            |

DPI 和高度接受整数，设备是否接受指定值以实际响应为准。输出保留设备返回的流宽，不做横向裁边、纠偏、旋转、OCR 或 PDF；图像不完整时会报错。

程序被强制终止后，如需结束残留作业：

```powershell
python src/scan_direct.py --stop --backend usbscan
```

该命令会访问设备；使用其他驱动时选择对应后端。查看帮助不会访问设备：

```powershell
python -B src/scan_direct.py --help
python -B src/scan_interactive.py --help
```

Python 调用与已验证范围见 [使用文档](doc/README.md)。Wi-Fi 扫描及无线配置入口见 [总说明](../README.md)。
