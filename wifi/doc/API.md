# Python 调用

[简体中文](API.md) | [English](API.en.md) | [日本語](API.ja.md)

使用 Python 3.11 或更新版本，并从 `ix100/wifi/` 执行 `python -m pip install -r requirements.txt` 安装依赖。将 `src/` 加入模块搜索路径，或在 `src/` 中启动 Python。

| 模块 | 职责 |
|---|---|
| `driver.py` | 设备会话、预约和保活、扫描、最终尺寸及未压缩像素恢复 |
| `app_common.py` | INI、扫描参数覆盖、输出路径和 BMP 编码 |
| `scan_direct.py` | 立即扫描一页的命令行入口 |
| `scan_interactive.py` | 一个连续作业内放纸自动扫描并逐页保存 |
| `discover.py` | 读取配置、发送UDP并输出设备发现结果 |
| `generate_manager_id.py` | 离线生成Manager ID |

`app_common.load_config_file()`读取本地配置，`generate_manager_id.py`生成Manager ID，两者均不访问设备。以下示例中的 `DriverSession` 和扫描调用会连接设备并执行扫描；配置文件和输出路径相对于当前工作目录：

```python
from app_common import load_config_file, save_scan_image
from driver import ColorMode, DriverSession

config = load_config_file("config/ix100.local.ini")
config.dpi = 300
config.color_mode = ColorMode.COLOR
config.overscan = True
with DriverSession(config) as driver:
    driver.reserve()
    result = driver.scan()
    save_scan_image("output/ix100_scan.bmp", result)
```

会话上下文负责释放设备。`DriverSession.scan()` 创建单页作业，扫描一页后结束该作业。`driver.batch(continuous=True)` 提供连续作业；使用其上下文管理器启动和结束作业，`wait_for_paper(should_stop)` 等纸，`scan_page()` 扫描并返回一页结果。连续入口的完整使用方式见 [INTERACTIVE.md](INTERACTIVE.md)。

标识生成函数从 `generate_manager_id` 导入：`from generate_manager_id import generate_manager_id`。设备发现函数从 `discover` 导入：`from discover import discover_devices`；`discover_devices(config)`会发送UDP并访问设备。

`Config.color_mode` 使用 `ColorMode.COLOR`、`ColorMode.GRAY` 或 `ColorMode.MONO`，默认 `COLOR`；`Config.overscan` 默认 `True`。设置在创建设备会话前确定，INI 可选项省略时使用默认值。固定节名、键名和必填项见 [CONFIGURATION.md](CONFIGURATION.md)。

`ScanResult.color_mode` 记录图像模式。`ScanResult.image` 按从上到下的行序保存纯像素：彩色为 24 位 BGR，灰度为 8 位单通道，黑白为 1 位打包。预期行字节数为 `(width * bits_per_pixel + 7) // 8`，图像长度必须等于行字节数乘以最终高度。灰度和黑白的未压缩响应格式、极性尚未真机确认。

保存器按模式写 24、8、1 位 BMP，增加所需调色板和行填充，不反色、不裁剪，按传入路径原样保存。输出路径使用正斜杠及 `.bmp` 文件名，例如 `output/ix100_scan.bmp`。`save_scan_image()` 不展开时间格式；需要时间戳时可自行用 `datetime.now().strftime()` 生成路径。`scan_direct.py` 已在访问设备前对输出参数或 INI `[scan] output` 完成此展开。

导入模块不会联网，但构造设备会话会选择网络接口并初始化传输。协议分析和历史验证资料不属于运行依赖。
