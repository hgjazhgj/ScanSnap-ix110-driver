# Python 调用

使用 Python 3.11 或更新版本，并从 `ix100/wifi/` 执行 `python -m pip install -r requirements.txt` 安装依赖。将 `src/` 加入模块搜索路径，或在 `src/` 中启动 Python。

| 模块 | 职责 |
|---|---|
| `driver.py` | 设备会话、预约和保活、扫描、最终尺寸及未压缩像素恢复 |
| `app_common.py` | INI、Manager ID、输出路径和 BMP 编码 |
| `scan_direct.py` | 单次命令行操作 |
| `scan_interactive.py` | 一个连续作业内放纸自动扫描并逐页保存 |

加载配置和生成 Manager ID 不访问设备。以下示例中的 `DriverSession` 和扫描调用会连接设备并执行扫描；配置文件和输出路径相对于当前工作目录：

```python
from app_common import load_config_file, save_scan_image
from driver import DriverSession

config = load_config_file("config/ix100.local.ini")
with DriverSession(config) as driver:
    driver.reserve()
    result = driver.scan()
    save_scan_image("output/page.bmp", result)
```

会话上下文负责释放设备。`DriverSession.scan()` 创建单页作业，扫描一页后结束该作业。`driver.batch(continuous=True)` 提供连续作业；使用其上下文管理器启动和结束作业，`wait_for_paper(should_stop)` 等纸，`scan_page()` 扫描并返回一页结果。连续入口的完整使用方式见 [INTERACTIVE.md](INTERACTIVE.md)。

`ScanResult.image` 是从上到下排列的纯 24 位 BGR 像素，长度必须恰好等于 `result.info.width × result.info.height × 3`。驱动取得最终尺寸并检查像素完整性后才返回成功。保存器仅写入 BMP 文件头和格式所需的行填充，不反色、不裁剪，路径后缀统一为 `.bmp`。

导入模块不会联网，但构造设备会话会选择网络接口并初始化传输。协议分析和历史验证资料不属于运行依赖。当前实机验证范围见 [README](../README.md)。