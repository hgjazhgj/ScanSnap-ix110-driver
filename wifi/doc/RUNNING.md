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
| `python src/scan_direct.py generate-manager-id` | 离线生成主机标识，不写入文件 |
| `python src/scan_direct.py check-config` | 离线检查本地配置 |
| `python src/scan_direct.py discover` | 发送 UDP，输出发现结果 |
| `python src/scan_direct.py validate-params` | 连接、预约设备并提交参数，不启动进纸 |
| `python src/scan_direct.py scan output/page.bmp` | 立即扫描一页并保存 BMP |
| `python src/scan_direct.py listen-once output/panel.bmp` | 等待扫描仪面板触发后扫描一页 |
| `python src/scan_interactive.py --output-dir output` | 放纸自动扫描，回车结束连续作业 |

设备命令应在扫描仪已开机、网络可达并已填写配置后运行。`discover` 成功只证明 UDP 可达，休眠设备仍可能无法建立 TCP 会话。应先唤醒设备，再进行扫描。

所有需要配置的命令均可加 `--config FILE`。`listen-once` 默认持续等待，用 `--wait 120` 限制等待秒数。省略单页输出路径时使用 INI 的 `[scan] output`；相对路径均基于当前工作目录。输出文件扩展名统一为 `.bmp`。

成功扫描必须取得最终图像尺寸及完整像素，保存 BMP，并结束作业、释放设备。若失败，终端报告错误并返回非零退出码；不要把仅走纸或参数提交成功当作图像保存成功。连续扫描的退出方式见 [INTERACTIVE.md](INTERACTIVE.md)。
