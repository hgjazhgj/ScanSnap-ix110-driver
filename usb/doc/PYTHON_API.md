# Python 接口

[使用文档索引](README.md)

将 `ix100/usb/src/` 加入 `PYTHONPATH`，或在 `src/` 目录中启动Python后：

```python
from bmp_output import default_output, save_bmp
from scanner_driver import ColorMode, ScanSettings, open_scan_batch

settings = ScanSettings(
    dpi=300, color_mode=ColorMode.GRAY,
    height_units=42307, overscan=True,
)
with open_scan_batch("auto", settings, reporter=print) as batch:
    page = batch.scan_page()
save_bmp(default_output(), page)
```

`ScanSettings` 默认单页模式，成功读取一页即结束批次；默认 `height_units=42307`、`overscan=True`。`width_units`为只读属性，按overscan返回10200或10368，构造器不再接收宽度参数。宽高单位均为 **1/1200 英寸**。默认300 DPI彩色开启overscan后，基础/扩展尺寸均为10368×42307单位，像素预算2592×10577。多页设置 `mode=ScanMode.CONTINUOUS`（从 `scanner_driver` 导入 `ScanMode`），每页先调用 `batch.wait_for_paper(should_stop)`，返回 `True` 后再调用 `scan_page()`；`should_stop` 是返回布尔值的回调。退出 `with` 会执行批次收尾并释放传输资源。

`window_width_units`、`window_height_units` 给出实际下发尺寸；`maximum_width_pixels`、`maximum_lines` 用于检查 READ80 返回上界。行数预算为 `ceil(height_units * dpi / 1200)`，不会反算修改高度。读取接受未按4字节对齐的返回宽度，行步长为 `ceil(实际流宽 * 位深 / 8)`，黑白行末不足8位仍占1字节；尺寸及完整图像检查保留。保存BMP时按实际行长补零到4字节，不改变图像宽度。下发窗口按整行 4 字节约束对齐；当前选择两档宽度，不复现官方全部纸型计算。

`color_mode` 可选择 `ColorMode.COLOR`、`ColorMode.GRAY` 或 `ColorMode.MONO`。`ScannedPage.pixels` 保存对应模式的像素数据（原 `rgb` 字段改名），`color_mode` 标识位深；优先通过 `save_bmp()` 保存。

传输模块为 `src/transport_libusb.py`、`src/transport_usbscan.py`，共享封包在 `src/transport_protocol.py`；Windows 端口发现由 `src/usbscan_device.py` 提供。
