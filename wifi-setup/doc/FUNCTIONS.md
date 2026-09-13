# Python 函数与 CLI 参考

[简体中文](FUNCTIONS.md) | [English](FUNCTIONS.en.md) | [日本語](FUNCTIONS.ja.md)

更新：2026-09-13。本页列出当前 Python API 与对应 CLI。已在 iX110 上完成 USB 信息读取，设置写入尚未真机验证。安装与常用操作见 [使用说明](../README.md)。

从 `ix100/wifi-setup/` 目录运行：

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py list-functions --json
py .\src\setup_cli.py set-wifi --help
```

这些帮助/清单命令离线。其余设备子命令（包括读取身份、查询状态）会打开 USB、占有设置会话，完成后释放。从 `src/` 目录运行 `py -m ix100_setup` 是同一入口；在其他目录导入模块时，需要将 `src/` 加入 `PYTHONPATH`。运行模块直接平铺在 `src/`，公开接口由 `ix100_setup.py` 提供。

函数通过 `from ix100_setup import connect` 使用：`with connect("usbscan") as device:` 创建一个设置会话；后续调用本页的 `device.函数(...)`。`connect` 自动发现端口并在退出时释放会话/关闭后端，不依赖官方 DLL。下面的函数签名省略 `self`。

## 参数与结果规则

- 函数名的下划线在 CLI 中变为连字符，所有函数参数都使用命名选项；例如 `set_wifi_mode(mode=0)` 对应 `set-wifi-mode --mode 0`。
- 无默认值的参数必填；有默认值的参数省略时直接采用 API 默认值。整数/浮点数由 CLI 解析，未添加重复范围校验；接受输入不等于设备支持该值。
- `bool` 参数用成对开关：例如 `--wait` / `--no-wait`、`--extended` / `--no-extended`。必填 `enabled: bool` 必须明确选择 `--enabled` 或 `--no-enabled`。
- `str` 参数为文字。密码、密钥、PIN 选项可以只给选项名，不附值，通过无回显终端提示输入。例如 `--wifi-key`、`--password`、`--pin`。密码参数完全省略和显式传空字符串遵循函数默认值，可能表示清空/禁用，详见对应函数。
- `list` / `dict` 参数通过 UTF-8 JSON 文件传入，选项尾部增加 `-file`；例如 `profiles` 使用 `--profiles-file`。`bytes` 参数同样增加 `-file`，读取原始文件字节；例如证书上传使用 `--data-file`。
- 正常结果为 UTF-8 JSON，包含 `operation` 与 `result`。完成且无返回值的设置函数输出 `result: null`；这表示调用已返回，不代表额外进行过联网或纸张扫描验证。设备、协议、I/O 错误返回非零退出码。
- 默认隐藏密码/密钥及不透明二进制内容；`--show-secrets` 明确启用其输出。Python API 返回解码值，不应用 CLI 的展示脱敏。

## 所有设备子命令共用的选项

选项放在子命令之后，例如 `get-mac-address --backend usbscan`；它们同样适用于 `run-file`，不适用于离线 `list-functions`。

| 选项 | 默认值 | 用途 |
| --- | --- | --- |
| `--backend auto\|usbscan\|libusb` | `auto` | 选择 USB 后端；自动回退只发生在打开阶段，操作中不更换后端重试 |
| `--usbscan-port` | 动态发现 | 显式指定 Windows 端口，例如 `\\.\Usbscan3`；不要把历史端口号当作固定地址 |
| `--timeout` | `30.0` 秒 | setup 操作的异步结果等待预算 |
| `--io-timeout` | `120.0` 秒 | libusb 单次 I/O 超时，与 setup 等待预算不同 |
| `--encoding` | `utf-8` | 设备文字字段编码；CLI JSON/help 输出为 UTF-8 |
| `--legacy-key` | 关闭 | 使用另一官方 `pFus...` 密钥混淆种子分支；iX100/iX110 默认 `aQwe...`，档案命令按官方固定种子处理 |
| `--show-secrets` | 关闭 | 显示解码后的秘密和二进制十六进制内容 |
| `--output-file` | stdout | 保存结果 JSON，脱敏策略与 stdout 相同 |
| `--binary-output-file` | 不导出 | 显式将 `get-eeprom` 的字节或 `get-device-file` 的 `data` 字节原样存入文件；批处理保存最后一个二进制结果。此选项明确导出原始字节，不受 JSON 的 `--show-secrets` 脱敏控制 |

## 档案 JSON：`--profiles-file`

相关命令：`set-profiles`、`replace-profiles`。两者都接收 JSON 数组；字段类型与语义如下。

| JSON 字段 | 类型 | 含义 |
| --- | --- | --- |
| `index` | 整数 | 现有档案的零基索引；`get-profiles` 返回这个值 |
| `ssid` | 字符串 | 路由器 SSID |
| `security` | 字符串 | 官方认证类型文字，例如 `WPA2` |
| `encryption` | 字符串 | 官方加密类型文字，例如 `AES` |
| `eap_type` | 字符串 | EAP 类型文字 |
| `ca_check` | 整数 | CA 检查的官方原始整数 |
| `phase2` | 字符串 | EAP 第二阶段认证文字 |
| `user_id` | 字符串 | 802.1X 用户身份 |
| `eap_password` | 字符串 | 802.1X 身份密码，与 Wi-Fi PSK 不同 |
| `anonymous_identity` | 字符串 | 匿名身份 |
| `wifi_key` | 字符串 | 无线密钥，与扫描连接密码不同 |
| `certificate_name` | 字符串 | 已注册客户端证书的名称 |
| `dhcp` | 整数 | DHCP 的官方原始整数 |
| `ip` | 字符串 | IPv4 地址 |
| `netmask` | 字符串 | IPv4 子网掩码 |
| `gateway` | 字符串 | IPv4 网关 |

`set-profiles` 表示局部更新：每项必须有 `index`，其余仅填写需要改变的字段。先读取设备完整原始列表，再修改对应字节；未指定字段、其他档案和未知字段全部保留，档案数量不变。例如以下 `profile-patch.json` 只修改第一个档案的 IP 参数：

```json
[
  {
    "index": 0,
    "dhcp": 0,
    "ip": "192.0.2.30",
    "netmask": "255.255.255.0",
    "gateway": "192.0.2.1"
  }
]
```

应用该文件的命令形式为 `py .\src\setup_cli.py set-profiles --profiles-file .\profile-patch.json --backend usbscan`。示例地址是虚构文档地址，须替换为实际部署参数。

`replace-profiles` 表示完整的新列表：数组顺序是新顺序、数组长度是新数量。带 `index` 的项复制对应现有档案并应用改动；不带 `index` 的项新建，以空白记录为基础填写字段。未纳入新列表的档案移出有效列表，`[]` 明确清空有效列表。比如 `[{"index":1},{"index":0}]` 表示只保留原档案 1、0，并交换它们的顺序。

`get-profiles` 的 Python 返回值可以供程序后续编辑。CLI 默认返回的 `<redacted>` 是展示占位符，不能当作密码值写回。只改 IP 等字段时直接使用局部更新文件，省略密钥字段。

## `run-file`：同一个 USB 会话内顺序执行

`run-file --commands-file` 接收 UTF-8 JSON 数组，每项包括：

| 字段 | 内容 |
| --- | --- |
| `command` | 函数名或对应 CLI 名，例如 `set_wifi` 或 `set-wifi` |
| `arguments` | 函数关键字参数对象，使用下划线名称。无参数可省略此对象 |

标量和列表直接写入 `arguments`；这里的 `profiles` 是数组本身，不是 `profiles_file`。对于函数 `bytes` 参数，JSON 值是文件路径，相对路径以命令 JSON 所在目录为基准。例如 `upload_certificate` 的 `arguments.data` 可以写 `"certificates/client.p12"`。

以下 `configure.example.json` 示例仅展示格式，SSID 和密钥均为虚构占位符。实际部署应填写目标网络参数，不能原样当作真实配置：

```json
[
  {
    "command": "set_wifi",
    "arguments": {
      "ssid": "REPLACE_WITH_NETWORK_SSID",
      "security": "WPA2",
      "encryption": "AES",
      "wifi_key": "REPLACE_WITH_WIFI_KEY"
    }
  },
  {"command": "set_ip", "arguments": {"dhcp": 1}},
  {"command": "diagnose_wifi"},
  {"command": "get_device_info"}
]
```

调用形式：`py .\src\setup_cli.py run-file --commands-file .\configure.example.json --backend usbscan`。

命令文件及二进制输入先读取，再打开一次 USB 并取得一次 setup 所有权，各项在同一个 `device` 对象上串行执行。批处理遇到错误会停止，报告已完成操作及失败操作；已执行的配置不会自动回滚。正常结果是操作结果数组。文件里的密码属于用户提供的配置内容，不会作为参数回显。

## WPS 开始、接收与取消

`start-wps`、`start-ap-wps`、`start-profile-wps` 默认 `wait=True`：同一次调用发起配对并等待结果，结束后才释放 setup 会话。空 `pin` 选择按钮方式；提供 `--pin`（可通过终端提示输入）选择 PIN 方式。

异步分步操作应放在同一 Python `with connect(...)` 中，或同一 `run-file` 文件中。例如以下内容发起 STA 按钮 WPS 并在同会话接收结果：

```json
[
  {"command": "start_wps", "arguments": {"wait": false}},
  {"command": "get_wps_result", "arguments": {"wait": true}}
]
```

要取消当前待完成的 STA/AP/profile WPS，可以在同会话调用 `cancel_wps()`；它替换当前 WPS 请求并默认等待取消结果。其他命令不能覆盖尚未完成的 setup 请求。单独退出一个 `start-wps --no-wait` CLI 会释放会话；不要指望第二个 CLI 的 `get-wps-result` 接续前一会话。轮询函数 `wait=False` 在设备仍忙时报告 pending 错误，适用于自行处理此状态的 Python 程序，批处理不会把该错误自动当作继续循环。

## 完整函数清单

表中“改变设备状态”包括修改配置、配对/诊断和会话控制；“否”表示读取功能，仍会通过 USB 与设备通信。具体支持情况取决于型号和固件，完整函数清单不代表 iX100/iX110 已支持或验证全部功能。

<!-- GENERATED API TABLES -->

当前共 86 个设备函数，各有一个对应的 CLI 子命令。表格 Yes/No 分别表示会/不会改变设备状态。

### core.py：会话控制

| 函数签名 | CLI 子命令 | 说明 | 改变设备状态 |
| --- | --- | --- | --- |
| `acquire_setup() -> dict` | `acquire-setup` | 占有 USB 无线设置会话（CLI 会在结束时释放） | Yes |
| `release_setup() -> dict` | `release-setup` | 释放当前 USB 无线设置会话 | Yes |

### info.py：身份、设备信息与无线网络搜索

| 函数签名 | CLI 子命令 | 说明 | 改变设备状态 |
| --- | --- | --- | --- |
| `get_configfile() -> dict` | `get-configfile` | 读取完整网络配置文件及已解码系统字段（包含秘密） | No |
| `get_configfile_size() -> int` | `get-configfile-size` | 读取设备配置文件长度 | No |
| `get_connection_status(extended: bool = True) -> dict` | `get-connection-status` | 读取当前无线连接状态 | No |
| `get_device_info(include_system: bool = True) -> dict` | `get-device-info` | 读取基础设备网络信息 | No |
| `get_device_info_8021x(include_system: bool = True) -> dict` | `get-device-info-8021x` | 读取 802.1X 扩展设备网络信息 | No |
| `get_eeprom() -> bytes` | `get-eeprom` | 读取机身 EEPROM 原始 512 字节 | No |
| `get_eeprom_area() -> int` | `get-eeprom-area` | 读取 EEPROM 的 area 字节（枚举含义未确认） | No |
| `get_firmware_info() -> dict` | `get-firmware-info` | 读取设备固件版本及原始版本记录 | No |
| `get_firmware_version() -> str` | `get-firmware-version` | 读取设备固件版本 | No |
| `get_functional_version() -> str` | `get-functional-version` | 读取无线功能版本 | No |
| `get_ip_settings(extended: bool = True) -> dict` | `get-ip-settings` | 读取 DHCP、IPv4、子网掩码和网关 | No |
| `get_mac_address(extended: bool = True) -> str` | `get-mac-address` | 读取设备 MAC 地址 | No |
| `get_model() -> str` | `get-model` | 读取扫描仪型号名 | No |
| `get_model_info() -> dict` | `get-model-info` | 读取标准 INQUIRY 型号信息 | No |
| `get_profile_number() -> int` | `get-profile-number` | 读取当前 Wi-Fi 档案编号 | No |
| `get_scanner_name(extended: bool = True) -> str` | `get-scanner-name` | 读取扫描仪网络名称 | No |
| `get_serial_info() -> dict` | `get-serial-info` | 读取机身序列号及 EEPROM area 字段 | No |
| `get_serial_number() -> str` | `get-serial-number` | 读取机身序列号 | No |
| `get_system_settings() -> dict` | `get-system-settings` | 读取连接密码设置及 ReadyNotificationPort | No |
| `get_wifi_settings(extended: bool = True) -> dict` | `get-wifi-settings` | 读取路由器 SSID、认证和加密设置 | No |
| `get_wifi_status() -> dict` | `get-wifi-status` | 读取硬件 Wi-Fi 开关状态 | No |
| `scan_access_points() -> list` | `scan-access-points` | 由扫描仪搜索周围无线网络 | No |
| `scan_access_points_8021x() -> list` | `scan-access-points-8021x` | 由扫描仪搜索包含 802.1X 信息的无线网络 | No |

### wifi.py：STA、AP、档案与 WPS

| 函数签名 | CLI 子命令 | 说明 | 改变设备状态 |
| --- | --- | --- | --- |
| `apply_profiles() -> None` | `apply-profiles` | 应用已经保存的 Wi-Fi 档案 | Yes |
| `cancel_wps(wait: bool = True) -> None` | `cancel-wps` | 取消 WPS 配对并默认在同一会话等候结果 | Yes |
| `diagnose_profile(profile_no: int) -> None` | `diagnose-profile` | 诊断指定编号的 Wi-Fi 档案连接 | Yes |
| `diagnose_wifi() -> None` | `diagnose-wifi` | 执行已配置 STA 无线连接诊断 | Yes |
| `get_ap_settings() -> dict` | `get-ap-settings` | 读取直连 AP 的 SSID、安全设置、IP 和 DHCP 服务设置 | No |
| `get_ap_system_info() -> dict` | `get-ap-system-info` | 读取直连 AP 当前状态、MAC、扫描仪名称和连接设置 | No |
| `get_ap_wps_mode3_result(wait: bool = True) -> None` | `get-ap-wps-mode3-result` | 接收当前 USB 会话内 AP WPS mode 3 的结果 | No |
| `get_ap_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-ap-wps-result` | 接收当前 USB 会话内直连 AP WPS 结果 | No |
| `get_profile_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-profile-wps-result` | 接收当前 USB 会话内档案 WPS 的结果 | No |
| `get_profiles() -> list` | `get-profiles` | 读取全部保存的 Wi-Fi 档案及各自 IP 设置 | No |
| `get_startup_wifi_mode() -> int` | `get-startup-wifi-mode` | 读取开机 Wi-Fi 模式 | No |
| `get_wifi_mode() -> int` | `get-wifi-mode` | 读取当前 Wi-Fi 模式 | No |
| `get_wps_cancel_result(wait: bool = True) -> None` | `get-wps-cancel-result` | 接收当前 USB 会话内 WPS 取消操作的结果 | No |
| `get_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-wps-result` | 接收当前 USB 会话内已启动的 STA WPS 结果 | No |
| `register_profile(profile_no: int, ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', certificate_name: str = '', ca_check: int = 0) -> None` | `register-profile` | 注册指定编号的 Wi-Fi / 802.1X 档案 | Yes |
| `replace_profiles(profiles: list) -> None` | `replace-profiles` | 显式替换档案列表：按 index 保留/重排，省略的档案移出有效列表 | Yes |
| `set_ap_ip(ip: str, netmask: str, dhcp_server: int, lease_time: int, lease_start: str, lease_end: str) -> None` | `set-ap-ip` | 设置直连 AP 的 IPv4、掩码、DHCP 服务和地址租期/地址池 | Yes |
| `set_ap_wifi(ssid: str, stealth: int, channel: int, security: str, encryption: str, wifi_key: str, key_display: int = 0) -> None` | `set-ap-wifi` | 设置直连 AP 的 SSID、隐藏模式、信道及安全参数 | Yes |
| `set_ap_wps_status(status: int) -> None` | `set-ap-wps-status` | 设置直连 AP WPS 状态 | Yes |
| `set_ip(dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-ip` | 设置 STA 的 DHCP 或静态 IPv4、掩码、网关 | Yes |
| `set_profile_ip(index: int, dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-profile-ip` | 修改单个已有档案的 DHCP/IP 参数，保留其他档案及密钥 | Yes |
| `set_profiles(profiles: list) -> None` | `set-profiles` | 按零基 index 修改已有档案，保留未指定档案和未知字段 | Yes |
| `set_startup_wifi_mode(mode: int) -> None` | `set-startup-wifi-mode` | 设置开机 Wi-Fi 模式（iX100 分支） | Yes |
| `set_wifi(ssid: str, security: str, encryption: str, wifi_key: str) -> None` | `set-wifi` | 设置路由器 SSID、认证方式、加密方式和 Wi-Fi 密钥 | Yes |
| `set_wifi_8021x(ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', ca_check: int = 0) -> None` | `set-wifi-8021x` | 设置 STA 的 802.1X / EAP 身份、证书检查和无线密钥 | Yes |
| `set_wifi_mode(mode: int) -> None` | `set-wifi-mode` | 立即切换 Wi-Fi 模式（iX100 分支） | Yes |
| `start_ap_wps(pin: str = '', wait: bool = True) -> None` | `start-ap-wps` | 启动直连 AP WPS 按钮/PIN 配对，默认等候结果 | Yes |
| `start_ap_wps_mode3(wait: bool = True) -> None` | `start-ap-wps-mode3` | 启动官方 AP WPS mode 3 操作，默认等候结果 | Yes |
| `start_profile_wps(pin: str = '', wait: bool = True) -> None` | `start-profile-wps` | 通过 WPS 按钮/PIN 注册档案，默认等候结果 | Yes |
| `start_wps(pin: str = '', wait: bool = True) -> None` | `start-wps` | 启动 STA WPS 按钮/PIN 配对，默认在同一会话等候结果 | Yes |

### advanced.py：系统、端口、证书与扩展设置

| 函数签名 | CLI 子命令 | 说明 | 改变设备状态 |
| --- | --- | --- | --- |
| `delete_certificate(kind: int, filename: str = '') -> dict` | `delete-certificate` | 删除指定证书 | Yes |
| `erase_access_token() -> dict` | `erase-access-token` | 清除设备访问 token（进入维护模式并执行官方命令） | Yes |
| `execute_device_command(command: str) -> dict` | `execute-device-command` | 通过官方维护接口执行设备命令 | Yes |
| `get_certificate_info(kind: int, get_info: int, filename: str = '') -> dict` | `get-certificate-info` | 读取证书详细信息 | No |
| `get_connect_frequency() -> dict` | `get-connect-frequency` | 读取连接频段枚举（官方仅 iX1300） | No |
| `get_device_auth() -> dict` | `get-device-auth` | 读取设备认证 key（旧型号 Usb_Operate_Auth_Device 的查询分支） | No |
| `get_device_auth_requirement() -> dict` | `get-device-auth-requirement` | 读取设备认证需求及官方状态码 | No |
| `get_device_file(path: str) -> dict` | `get-device-file` | 通过官方分页接口读取设备文件 | No |
| `get_dns() -> dict` | `get-dns` | 读取 DNS 参数（官方仅 iX1300/iX1500/iX1600 二进制分支） | No |
| `get_eh_port() -> dict` | `get-eh-port` | 读取 EH/ReadyNotificationPort 通知端口 | No |
| `get_maintenance_mode() -> dict` | `get-maintenance-mode` | 读取维护模式 | No |
| `get_protocol() -> dict` | `get-protocol` | 读取通信协议枚举（不是端口号） | No |
| `get_proxy() -> dict` | `get-proxy` | 读取代理服务器（官方仅 iX1300/iX1500/iX1600 二进制分支） | No |
| `get_registered_pcs() -> dict` | `get-registered-pcs` | 读取已关联电脑的两组主机 ID | No |
| `get_roaming() -> dict` | `get-roaming` | 读取漫游枚举（官方仅 iX1300） | No |
| `initialize_registered_pcs() -> dict` | `initialize-registered-pcs` | 初始化电脑关联数据（CLR HOSTID ADATA） | Yes |
| `list_certificates(kind: int) -> dict` | `list-certificates` | 读取证书列表 | No |
| `register_certificate(kind: int, filename: str, password: str = '') -> dict` | `register-certificate` | 注册已上传的证书及其导入密码 | Yes |
| `register_pc(host_id: str, additional_host_id: str = '') -> dict` | `register-pc` | 注册电脑主机 ID（十六进制字符串） | Yes |
| `reset_invalidation(value: int) -> dict` | `reset-invalidation` | 写入官方 Reset_invalidation 的原始整数参数 | Yes |
| `reset_wifi_settings() -> dict` | `reset-wifi-settings` | 重置无线设置并复现官方 iX110 名称/SSID 恢复分支 | Yes |
| `set_connect_frequency(frequency: int) -> dict` | `set-connect-frequency` | 设置连接频段枚举（官方仅 iX1300） | Yes |
| `set_dns(mode: int, primary: str = '', secondary: str = '') -> dict` | `set-dns` | 设置 DNS 参数（官方仅 iX1300/iX1500/iX1600 二进制分支） | Yes |
| `set_eh_port(port: int) -> dict` | `set-eh-port` | 设置 EH/ReadyNotificationPort 通知端口 | Yes |
| `set_maintenance_mode(mode: int) -> dict` | `set-maintenance-mode` | 设置维护模式（官方 token 清除使用进入 1、退出 0） | Yes |
| `set_possession_setting(value: int) -> dict` | `set-possession-setting` | 写入官方 Possession_Setting（SET OCCUPA RIGHT） | Yes |
| `set_protocol(protocol: int) -> dict` | `set-protocol` | 设置通信协议枚举（官方值 0/1，不是端口号） | Yes |
| `set_proxy(enabled: bool, address: str = '', port: int = 8080, authentication: bool = False, username: str = '', password: str = '') -> dict` | `set-proxy` | 设置代理服务器（官方仅 iX1300/iX1500/iX1600 二进制分支） | Yes |
| `set_roaming(roaming: int) -> dict` | `set-roaming` | 设置漫游枚举（官方仅 iX1300） | Yes |
| `set_system_settings(name: str, password: str = '', password_display: int = 0) -> dict` | `set-system-settings` | 设置扫描仪名称、扫描连接密码及密码显示设置 | Yes |
| `upload_certificate(data: bytes, file_id: str = 'CertificateFile') -> dict` | `upload-certificate` | 上传证书文件到设备暂存区 | Yes |

