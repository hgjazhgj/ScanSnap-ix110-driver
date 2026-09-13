# ScanSnap iX100/iX110 Wi-Fi 驱动

独立 Python 驱动，支持 Windows/Linux，不需要 ScanSnap Home 或官方 DLL。通过 Wi-Fi 发现、预约和控制扫描仪，请求单面未压缩彩色、灰度或黑白图像，分别保存为 24、8 或 1 位 BMP。

使用 Python 3.11 或更新版本。以下命令均从本目录 `ix100/wifi/` 运行：

```powershell
python -m pip install -r requirements.txt
Copy-Item config/ix100.example.ini config/ix100.local.ini
python src/generate_manager_id.py
```

编辑 `config/ix100.local.ini`，填写 `[scanner] ip` 和 `[identity] wifi_manager_id`。`[credential] password_required` 默认开启，此时还须填写 `[credential] password`，使用设备背面标签上的连接密码；设备无需密码时设为 `0`。其余配置可使用默认值。生成标识的脚本离线运行，不改写配置文件。

需要发现扫描仪时，运行独立入口；该命令会发送UDP并访问设备：

```powershell
python src/discover.py --config config/ix100.local.ini
```

放入纸张后扫描一页：

```powershell
python src/scan_direct.py output/ix100_scan.bmp
```

默认使用 300 DPI、彩色、开启 overscan。可用命令行覆盖 INI 设置，例如：

```powershell
python src/scan_direct.py output/ix100_scan.bmp --dpi 300 --color-mode gray --no-overscan
```

`--color-mode` 接受 `color|gray|mono`；`--overscan` 开启、`--no-overscan` 关闭边缘扩展扫描。未压缩灰度和黑白的响应格式、极性尚未真机确认；接受参数不代表对应模式已经验证。

放纸自动扫描、回车结束连续作业：

```powershell
python src/scan_interactive.py --output-dir output
```

| 路径                                         | 用途                                     |
| -------------------------------------------- | ---------------------------------------- |
| `src/`                                       | 驱动、公共配置和图像保存、扫描及独立工具入口 |
| `requirements.txt`                           | Python 依赖                              |
| `config/ix100.example.ini`                   | 可分发的配置模板                         |
| [doc/CONFIGURATION.md](doc/CONFIGURATION.md) | 固定 INI 格式、必填项和默认值           |
| [doc/RUNNING.md](doc/RUNNING.md)             | 安装、全部命令与分发                     |
| [doc/INTERACTIVE.md](doc/INTERACTIVE.md)     | 连续扫描、命名与退出                     |
| [doc/API.md](doc/API.md)                     | Python 调用方式                          |

省略 `--config` 时固定使用本目录的 `config/ix100.local.ini`；其他位置的配置须通过 `--config FILE` 指定。`scan_direct.py` 的输出参数优先于 INI 的 `[scan] output`，默认 `output/ix100_scan.bmp`。整个输出路径在访问设备前按本机当地时间调用 `strftime` 展开，相对路径以当前工作目录为基准。路径使用正斜杠及 `.bmp` 文件名，例如：

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` 为六位微秒，`%%` 表示字面百分号。INI 的 `[scan] output` 也支持相同时间模板；交互入口的目录不展开时间格式，文件名由其逐页生成。程序不反色、不裁剪，也不进行有损编码。

本机 `ix100.local.ini` 含专用标识和明文密码，不随通用包分发。发布目录只附配置模板。
