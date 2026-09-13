# ScanSnap iX100/iX110 Wi-Fi 驱动

独立 Python 驱动，支持 Windows/Linux，不需要 ScanSnap Home 或官方 DLL。通过 Wi-Fi 发现、预约和控制扫描仪，固定请求单面彩色未压缩图像并保存为 24 位 BMP。

使用 Python 3.11 或更新版本。以下命令均从本目录 `ix100/wifi/` 运行：

```powershell
python -m pip install -r requirements.txt
Copy-Item .\config\ix100.example.ini .\config\ix100.local.ini
python src/scan_direct.py generate-manager-id
```

编辑 `config/ix100.local.ini`，填写扫描仪 IP、设备背面标签上的连接密码，以及生成的 Manager ID。随后检查本地配置：

```powershell
python src/scan_direct.py check-config
```

放入纸张后扫描一页：

```powershell
python src/scan_direct.py scan output/page.bmp
```

放纸自动扫描、回车结束连续作业：

```powershell
python src/scan_interactive.py --output-dir output
```

| 路径                                         | 用途                                     |
| -------------------------------------------- | ---------------------------------------- |
| `src/`                                       | 驱动、公共配置和图像保存、两个命令行入口 |
| `requirements.txt`                           | Python 依赖                              |
| `config/ix100.example.ini`                   | 可分发的配置模板                         |
| [doc/CONFIGURATION.md](doc/CONFIGURATION.md) | 配置项、默认路径与已有配置兼容           |
| [doc/RUNNING.md](doc/RUNNING.md)             | 安装、全部命令与分发                     |
| [doc/INTERACTIVE.md](doc/INTERACTIVE.md)     | 连续扫描、命名与退出                     |
| [doc/API.md](doc/API.md)                     | Python 调用方式                          |

已有相对输出路径以启动程序时的当前工作目录为基准；省略输出参数时使用 INI 的 `[scan] output`。输出统一为 `.bmp`，旧配置中的 `.jpg` 扩展名也会自动替换，不改写 INI。程序不反色、不裁剪，也不进行有损编码。

本机 `ix100.local.ini` 含专用标识和明文密码，不随通用包分发。发布目录只附配置模板。
