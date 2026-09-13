# 运行与分发

使用 Python 3.11 或更新版本，支持 Windows/Linux。唯一第三方依赖是用于枚举网卡、MAC 和广播地址的 `psutil`；BMP 编码使用标准库。

以下命令均在 `ix100/wifi/` 执行：

```powershell
python -m pip install -r requirements.txt
```

依赖需安装到实际运行入口所用的解释器。首次配置见 [CONFIGURATION.md](CONFIGURATION.md)。

| 命令 | 行为 |
|---|---|
| `python src/scan_direct.py --help` | 离线查看参数 |
| `python src/scan_interactive.py --help` | 离线查看连续扫描参数 |
| `python src/generate_manager_id.py` | 离线生成主机标识，不写入文件 |
| `python src/discover.py --config config/ix100.local.ini` | 发送 UDP，输出发现结果 |
| `python src/scan_direct.py output/ix100_scan.bmp` | 立即扫描一页并保存 BMP |
| `python src/scan_interactive.py --output-dir output` | 放纸自动扫描，回车结束连续作业 |

设备命令应在扫描仪已开机、网络可达并已填写配置后运行。`discover.py` 成功只证明 UDP 可达，休眠设备仍可能无法建立 TCP 会话。应先唤醒设备，再进行扫描。

若预约返回 `status=-4 / 0xFFFFFFFC`，表示扫描仪被其他客户端占用。请先结束 ScanSnap Home、手机或其他程序的连接，再执行扫描；此时尚未提交扫描参数或启动进纸。

扫描和发现入口均可加 `--config FILE`；省略时固定使用发布目录的 `ix100/wifi/config/ix100.local.ini`，其他位置须明确指定。`scan_direct.py` 只执行一次单页扫描；输出位置参数优先于 INI 的 `[scan] output`，默认 `output/ix100_scan.bmp`。整个路径在访问设备前按本机当地时间调用 `strftime` 展开，包括目录。相对路径基于当前工作目录，路径使用正斜杠及 `.bmp` 文件名：

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` 为六位微秒，`%%` 表示字面百分号。INI 输出配置也支持相同时间模板；交互入口的目录不展开时间格式，逐页名称见 [INTERACTIVE.md](INTERACTIVE.md)。

`scan_direct.py` 和 `scan_interactive.py` 接受 `--dpi INTEGER`、`--color-mode color|gray|mono`、`--overscan`／`--no-overscan`。命令行指定的值覆盖 INI；省略时保留配置，配置缺省为 300 DPI、彩色、开启 overscan。`discover.py` 读取相同配置，不接受这些扫描参数。

彩色、灰度、黑白分别保存为 24、8、1 位 BMP。灰度和黑白的未压缩响应格式与极性尚未真机确认。

成功扫描必须取得最终图像尺寸及完整像素，保存 BMP，并结束作业、释放设备。若失败，终端报告错误并返回非零退出码；不要把仅走纸或参数提交成功当作图像保存成功。连续扫描的退出方式见 [INTERACTIVE.md](INTERACTIVE.md)。
