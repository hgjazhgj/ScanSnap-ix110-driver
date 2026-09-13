# Python 接口

[简体中文](PYTHON_API.md) | [English](PYTHON_API.en.md) | [日本語](PYTHON_API.ja.md)

[使用文档索引](../README.md)

将 `ix100/usb/src/` 加入 `PYTHONPATH`，或在 `src/` 目录中启动Python后：

```python
from pathlib import Path

from bmp_output import save_bmp
from scanner_driver import ColorMode, ScanSettings, open_scan_batch

settings = ScanSettings(
    dpi=300, color_mode=ColorMode.GRAY,
    overscan=True,
)
with open_scan_batch("auto", settings, reporter=print) as batch:
    page = batch.scan_page()
save_bmp(Path("output/page.bmp"), page)
```

`save_bmp()` 按给定路径保存，不展开时间格式。需要时间戳时可自行用 `datetime.now().strftime()` 生成路径；`scan_direct.py` 已在访问设备前完成这一步。

`ScanSettings` 默认单页模式，成功读取一页即结束批次；默认 `dpi=300`、`overscan=True`。构造器不接收宽度或高度参数。宽度按 overscan 选择开启 10368、关闭 10208；高度在 600 DPI 时为 17828，其他 DPI 为 42307。宽高单位均为 **1/1200 英寸**，基础和扩展字段使用同一组尺寸。默认300 DPI彩色开启overscan后，尺寸为10368×42307单位，像素预算2592×10577。

每批作业初始化时发送一次 page3C 和 SET WINDOW；批次中的后续页面沿用同一组参数。多页设置 `mode=ScanMode.CONTINUOUS`（从 `scanner_driver` 导入 `ScanMode`），每页先调用 `batch.wait_for_paper(should_stop)`，返回 `True` 后再调用 `scan_page()`；`should_stop` 是返回布尔值的回调。退出 `with` 会执行批次收尾并释放传输资源。

`window_width_units`、`window_height_units` 给出实际下发尺寸；`maximum_width_pixels`、`maximum_lines` 用于检查 READ80 返回上界。行数预算为 `ceil(window_height_units * dpi / 1200)`。两档宽度直接下发，读取行步长由设备返回的实际流宽计算：`ceil(实际流宽 * 位深 / 8)`，黑白行末不足8位仍占1字节。尺寸及完整图像检查保留。保存BMP时按实际行长补零到4字节，不改变图像宽度。当前宽高选择是主机策略，不复现官方全部纸型计算。

`color_mode` 可选择 `ColorMode.COLOR`、`ColorMode.GRAY` 或 `ColorMode.MONO`。`ScannedPage` 包含 `pixels`、`width`、`height` 和 `color_mode`，不包含 DPI；`pixels` 保存对应模式的像素数据，宽高来自设备返回结果，`color_mode` 标识位深。`save_bmp()` 将横纵像素/米字段写为 0，表示未指定物理分辨率；扫描请求的 DPI 仍由 `ScanSettings.dpi` 控制。

传输模块为 `src/transport_libusb.py`、`src/transport_usbscan.py`，共享封包在 `src/transport_protocol.py`；Windows 端口发现由 `src/usbscan_device.py` 提供。
