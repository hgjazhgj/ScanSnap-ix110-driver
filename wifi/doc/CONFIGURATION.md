# Wi-Fi 配置

以下路径和命令均以 `ix100/wifi/` 为当前目录。复制 `config/ix100.example.ini` 为 `config/ix100.local.ini` 后，按下表使用固定的节名和键名。必填项只有扫描仪 IP、Manager ID，以及启用连接密码时的密码；其余项使用默认值。

```powershell
python src/generate_manager_id.py
```

Manager ID由独立脚本随机生成，复制到 `[identity] wifi_manager_id` 后重复使用。生成器离线运行，只在终端输出标识，不改写配置文件。

| 配置项 | 含义 |
|---|---|
| `[identity] wifi_manager_id` | 必填；8 字节主机标识，写成 16 个十六进制字符且不能全零，生成后重复使用 |
| `[scanner] ip` | 必填；扫描仪当前 IPv4 地址，可从路由器租约表或 `discover.py` 结果取得 |
| `[scanner] control_port` | 可选，默认 53218；扫描控制 TCP 端口 |
| `[scanner] app_port` | 可选，默认 53219；预约、设备信息和释放 TCP 端口 |
| `[scanner] discovery_port` | 可选，默认 52217；UDP 发现与保活端口 |
| `[credential] password_required` | 可选，默认 `1`；使用设备连接密码时为 `1`，设备无需密码时为 `0` |
| `[credential] password` | 启用密码时必填；设备背面标签上的明文密码，1～16 个不含空格的可打印 ASCII 字符 |
| `[network] timeout_seconds` | 网络/扫描超时，默认 30 秒，按 5～300 秒取值 |
| `[scan] dpi` | 扫描分辨率整数，默认 300；接受参数不表示设备已支持或验证该值 |
| `[scan] color_mode` | `color`、`gray` 或 `mono`，默认 `color`；分别保存 24、8、1 位 BMP |
| `[scan] overscan` | `1` 开启边缘扩展扫描，`0` 关闭，默认 `1` |
| `[scan] max_image_mb` | 单页接收内存上限，默认 256 MiB，按 1～1024 MiB 取值 |
| `[scan] output` | 单页默认 BMP 输出路径，默认 `output/ix100_scan.bmp`；支持 `strftime` 时间模板，使用正斜杠及 `.bmp` 文件名 |

主机 IP、出站网卡、主机 MAC 和广播地址自动选择，无需在配置中填写。程序不读取官方应用的配置或注册表。

`scan_direct.py` 和 `scan_interactive.py` 均可用 `--dpi INTEGER`、`--color-mode color|gray|mono`、`--overscan`／`--no-overscan` 覆盖 INI 中对应设置，不改写配置文件。单页入口直接接收输出路径，例如 `python src/scan_direct.py output/ix100_scan.bmp`。

发现入口读取同一配置，运行 `python src/discover.py --config config/ix100.local.ini` 会发送UDP并访问设备。

窗口尺寸由主机按设置选择，单位为 1/1200 英寸：600 DPI 使用高度 17828，其他 DPI 使用 42307；overscan 开启时宽度 10368，关闭时 10208。这是当前主机策略，不代表完全复现官方自动纸型规则。较高 DPI 需要更多接收内存，可通过 `max_image_mb` 设置单页接收上限。

省略 `--config` 时固定使用发布目录的 `ix100/wifi/config/ix100.local.ini`。真实配置可存放在其他位置，通过 `--config FILE` 明确指定；不要求把凭据放进分发目录。

`scan_direct.py` 的输出位置参数优先于 `[scan] output`，选定后在访问设备前按本机当地时间调用 `strftime` 展开整个路径，包括目录。例如：

```ini
[scan]
output=output/%Y%m%d/scan-%H%M%S-%f.bmp
```

`%f` 为六位微秒，`%%` 表示字面百分号；INI 中的时间格式直接按上述形式填写。相对输出路径以当前工作目录为基准，输出文件名应使用 `.bmp`。交互入口只取该配置的父目录，不展开时间格式，并自行生成逐页文件名。配置格式以本页和 `config/ix100.example.ini` 为准。

当前请求单面未压缩图像，没有保存时裁剪开关。灰度和黑白的响应格式、极性尚未真机确认。本地 INI 含明文密码，已在忽略规则中排除；分发和共享文件时仅使用模板。
