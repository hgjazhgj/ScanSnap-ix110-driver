# Wi-Fi 配置

以下路径和命令均以 `ix100/wifi/` 为当前目录。复制 `config/ix100.example.ini` 为 `config/ix100.local.ini` 后，填写设备地址、背面标签密码和稳定的 Manager ID。

```powershell
python src/scan_direct.py generate-manager-id
python src/scan_direct.py check-config --config config/ix100.local.ini
```

Manager ID 由程序随机生成，复制到 `[identity] wifi_manager_id` 后重复使用。`check-config` 只读取本地文件，不连接设备。它会输出设备地址、DPI 和密码字符数，不输出密码。

| 配置项 | 含义 |
|---|---|
| `[identity] wifi_manager_id` | 8 字节主机标识，写成 16 个十六进制字符；可沿用已有值 |
| `[scanner] ip` | 扫描仪当前 IPv4 地址，可从路由器租约表或 `discover` 结果取得 |
| `[scanner] name`、`serial`、`mac` | 便于人工辨认的设备名称、序列号和 MAC；当前协议不依赖这些记录字段 |
| `control_port` | 扫描控制 TCP 端口，默认 53218 |
| `app_port` | 预约、设备信息和释放 TCP 端口，默认 53219 |
| `discovery_port` | UDP 发现与保活端口，默认 52217 |
| `[credential] password_required` | 使用标签连接密码时填 `1` |
| `[credential] password` | 设备背面标签上的明文密码，1～16 个不含空格的可打印 ASCII 字符 |
| `[network] timeout_seconds` | 网络/扫描超时，默认 30 秒，按 5～300 秒取值 |
| `[scan] dpi` | 150、200、300 或 600，默认 300 |
| `[scan] max_image_mb` | 单页接收内存上限，默认 100 MiB，按 1～1024 MiB 取值 |
| `[scan] output` | 单页默认 BMP 输出路径，模板为 `output/ix100_scan.bmp` |

主机 IP、出站网卡、主机 MAC 和广播地址自动选择，无需在配置中填写。程序不读取官方应用的配置或注册表。

显式 `--config FILE` 优先。省略时依次查找：

1. Wi-Fi 源码目录下的 `config/ix100.local.ini`，即 `ix100/wifi/config/ix100.local.ini`。
2. 入口脚本同级及上一级的 `config/ix100.local.ini`。
3. 当前工作目录的 `config/ix100.local.ini`。

未找到时按第一项路径报告错误。真实配置可存放在其他位置，通过 `--config` 指定；不要求把凭据放进分发目录。

兼容已有配置中的 `default_ip`、`notification_port` 和 `[host] manager_id`。`[host] manager_id` 非空时优先于 `[identity] wifi_manager_id`。旧 Additional Manager ID、User ID、Single Mode ID 不参与当前驱动。输出路径中的旧 `.jpg` 后缀会改为 `.bmp`，配置文件保持原样。相对输出路径以当前工作目录为基准。

当前固定单面彩色未压缩扫描，没有裁剪开关。已验证范围见 [README](../README.md)。本地 INI 含明文密码，已在忽略规则中排除；分发和共享文件时仅使用模板。
