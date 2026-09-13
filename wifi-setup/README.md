# iX100 / iX110 Wi-Fi 设置

通过 USB 读取和配置扫描仪无线网络，提供 86 个 Python 设备函数及对应 CLI。支持 STA/AP、无线档案、WPS、IP、扫描连接密码、EH 通知端口、电脑关联和证书等操作。完整参数见 [函数与 CLI 参考](doc/FUNCTIONS.md)。

运行时不加载官方用户态 DLL。已在 iX110 上完成 USB 信息读取，覆盖 MAC、网络配置、档案、AP 和证书列表；**配置写入尚未真机验证**，不同型号和固件可能不支持部分功能。

## 安装与入口

需要 Python 3.11 或更新版本。从 `ix100/wifi-setup/` 目录运行：

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py set-wifi --help
```

以上帮助与函数清单命令离线。其余设备子命令，包括读取信息和查询状态，都会通过 USB 访问扫描仪。连接参数放在设备子命令之后。

Windows 使用 `--backend usbscan` 时只需要 Python 标准库及已绑定的官方 `usbscan.sys` 驱动。使用 libusb 时先安装依赖：

```powershell
py -m pip install -r .\requirements.txt
```

驱动绑定与 Linux 权限见同一发布包中的 [USB 驱动说明](../usb/driver/README.md)。本工具不安装驱动或改变绑定。`auto` 先尝试 libusb，仅在打开阶段失败时回退 usbscan；操作开始后不更换后端。

## 读取与设置

以下命令会访问设备：

```powershell
py .\src\setup_cli.py get-mac-address --backend usbscan
py .\src\setup_cli.py get-serial-number --backend usbscan
py .\src\setup_cli.py get-profiles --backend usbscan
py .\src\setup_cli.py get-system-settings --backend usbscan
```

Windows 端口按 USB ID 动态发现。多台设备时可以明确指定 `--usbscan-port '\\.\Usbscan3'`；端口编号可能变化。

配置 STA 无线网络的基本形式如下，SSID 需要替换成实际网络名：

```powershell
py .\src\setup_cli.py set-wifi --backend usbscan --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-ip --backend usbscan --dhcp 1
```

`--wifi-key` 不附值时会无回显询问无线密钥；`--password`、`--pin` 等秘密参数也支持此方式。无线密钥与扫描连接密码是两个独立字段。

支持无线档案的设备可以采用以下流程：

```powershell
py .\src\setup_cli.py register-profile --backend usbscan --profile-no 0 --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-profile-ip --backend usbscan --index 0 --dhcp 1
py .\src\setup_cli.py apply-profiles --backend usbscan
```

档案编号从 0 开始。注册已有编号会覆盖该档案，追加使用当前档案数。`set_profiles()` / `set_profile_ip()` 保留其他档案和未指定字段；`replace_profiles()` 明确替换完整列表。保存档案和应用档案是独立操作。

## Python API 与批处理

Python 程序需要将本目录的 `src/` 加入 `PYTHONPATH`，或从 `src/` 启动 Python。从 `src/` 运行 `py -m ix100_setup --help` 也是同一 CLI 入口。

运行模块直接平铺在 `src/`，`ix100_setup.py` 提供公开 Python 接口和模块入口，`setup_cli.py` 提供脚本入口。

```python
from ix100_setup import connect

with connect("usbscan") as device:
    mac = device.get_mac_address()
    profiles = device.get_profiles()
```

`connect()` 管理 USB 打开、设置会话占有与释放以及后端关闭；同一会话按顺序操作。函数返回字典、列表、字符串、整数、字节或 `None`，失败抛异常。

`set_system_settings(name, password="", password_display=0)` 同时修改名称和扫描连接密码，**空密码会关闭密码要求**。只改名称时应先读取并保留原密码设置：

```python
with connect("usbscan") as device:
    system = device.get_system_settings()
    device.set_system_settings(
        "OfficeScanner", system["password"], system["password_display"]
    )
```

`run-file --commands-file jobs.local.json` 在同一会话依次执行多条命令。WPS 默认在同一会话等待完成，建议按需要设置 `--timeout 180`；异步启动后的结果读取或取消也应留在同一 Python 会话或同一 `run-file` 中。批处理失败后不会回滚已完成操作。JSON 格式、函数签名和选项见 [完整参考](doc/FUNCTIONS.md)。

## 输出与适用范围

CLI 默认遮盖密码、密钥、token 和二进制内容。`--show-secrets` 显式显示这些内容；`--output-file` 保存相同 JSON。`--binary-output-file` 显式保存 EEPROM 或设备文件的完整原始字节，不受 JSON 脱敏控制。Python 返回值包含真实字段，保存和日志由调用者控制。

可设置的通知端口是 EH / `ReadyNotificationPort`，通常为 53220；未提供扫描 TCP/53218、TCP/53219 和发现 UDP/52217 的持久端口配置接口。读取的 EEPROM 序列号是机身序列号，没有射频芯片独立序列号或 MAC 改写接口。

DNS/代理限已实现的 iX1300/iX1500/iX1600 分支，频段/漫游限 iX1300，在 iX100/iX110 上会报告不支持。扩展设备信息、802.1X、档案和 AP 功能取决于功能版本；旧固件的相关基本信息 getter 可使用 `--no-extended`。

目录中的 `src/` 是运行源码，`doc/` 是使用参考，`requirements.txt` 是可选 libusb 依赖。
