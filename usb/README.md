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

默认输出到本目录的 `output/`，缺少目录时自动创建。单页默认文件名为 `ix100-%Y%m%d-%H%M%S-%f.bmp`，在访问设备前按本机当地时间调用 `strftime` 展开。也可指定位置：

```powershell
python src/scan_direct.py output/page.bmp
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
python src/scan_interactive.py --output-dir output
```

`scan_direct.py` 对整个输出路径展开时间格式，包括目录；`%f` 为六位微秒，`%%` 表示字面百分号。自定义相对路径以当前工作目录为基准。交互入口沿用逐页时间戳命名，`--output-dir` 不展开时间格式。

## 选项

两个扫描入口共用以下选项：

| 选项                           | 用途与默认值                                      |
| ------------------------------ | ------------------------------------------------- |
| `--dpi 300`                    | 扫描分辨率，默认 300 DPI                         |
| `--color-mode color`           | `color` 彩色、`gray` 灰度、`mono` 黑白，默认彩色  |
| `--backend auto`               | `auto`、`usbscan` 或 `libusb`                     |
| `--overscan` / `--no-overscan` | 扫描宽度，开启为 10368、关闭为 10208，默认开启   |

DPI 接受整数，设备是否接受指定值以实际响应为准。窗口宽高单位为 1/1200 英寸：600 DPI 的高度固定为 17828，其他 DPI 为 42307；高度由程序选择。两档宽度直接下发。扫描参数在每批作业初始化时配置一次，连续扫描的后续页面沿用同一组参数。

输出保留设备返回的流宽，不做横向裁边、纠偏、旋转、OCR 或 PDF；图像不完整时会报错。保存 BMP 时才按文件格式补齐每行，不改变扫描宽度。图像尺寸使用设备返回的像素宽高；BMP 不指定 DPI，横纵像素/米字段均为 0。

程序被强制终止后，如需结束残留作业：

```powershell
python src/scan_direct.py --stop --backend usbscan
```

该命令会访问设备；使用其他驱动时选择对应后端。查看帮助不会访问设备：

```powershell
python -B src/scan_direct.py --help
python -B src/scan_interactive.py --help
```

Wi-Fi 扫描及无线配置入口见 [总说明](../README.md)。
