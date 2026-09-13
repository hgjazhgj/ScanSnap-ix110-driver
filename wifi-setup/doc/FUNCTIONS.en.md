# Python function and CLI reference

[简体中文](FUNCTIONS.md) | [English](FUNCTIONS.en.md) | [日本語](FUNCTIONS.ja.md)

Updated: 2026-09-13. This page lists the current Python API and corresponding CLI. USB information reading has been tested on iX110; configuration writes have not been validated on hardware. See the [user guide](../README.en.md) for installation and common operations.

Run from `ix100/wifi-setup/`:

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py list-functions --json
py .\src\setup_cli.py set-wifi --help
```

These help/list commands run offline. Other device subcommands, including identity reads and status queries, open USB, acquire a setup session and release it on completion. Running `py -m ix100_setup` from `src/` uses the same entry point. To import from elsewhere, add `src/` to `PYTHONPATH`. Runtime modules are directly in `src/`; `ix100_setup.py` provides the public interface.

Use `from ix100_setup import connect` and create a setup session with `with connect("usbscan") as device:`, then call the functions below as `device.function(...)`. `connect` automatically discovers ports and releases the session/closes the backend on exit, without official DLLs. Signatures below omit `self`.

## Argument and result rules

- Function-name underscores become CLI hyphens; all function arguments use named options. For example, `set_wifi_mode(mode=0)` becomes `set-wifi-mode --mode 0`.
- Arguments without defaults are required; omitted optional arguments use API defaults. The CLI parses integers/floats without duplicate range checks. Accepted input does not imply device support.
- `bool` arguments use paired switches, such as `--wait` / `--no-wait` and `--extended` / `--no-extended`. Required `enabled: bool` needs an explicit `--enabled` or `--no-enabled`.
- `str` arguments are text. Password, key and PIN options may omit their value to prompt without terminal echo, such as `--wifi-key`, `--password` and `--pin`. Omitting a password argument entirely or explicitly passing an empty string follows the function defaults and may clear/disable it; consult the function.
- `list` / `dict` arguments come from UTF-8 JSON files, with `-file` appended to the option, such as `--profiles-file` for `profiles`. `bytes` arguments also use `-file` and read raw bytes; certificate upload uses `--data-file`.
- Normal output is UTF-8 JSON with `operation` and `result`. Completed setters with no return value output `result: null`; this means the call returned, not that additional network or paper-scan verification occurred. Device, protocol and I/O errors return nonzero exit codes.
- Passwords/keys and opaque binary content are hidden by default; `--show-secrets` explicitly enables output. The Python API returns decoded values without CLI display redaction.

## Shared device-subcommand options

Place options after the subcommand, such as `get-mac-address --backend usbscan`. They also apply to `run-file`, but not offline `list-functions`.

| Option | Default | Purpose |
| --- | --- | --- |
| `--backend auto\|usbscan\|libusb` | `auto` | Select USB backend; fallback occurs only while opening, never by changing backends to retry an operation |
| `--usbscan-port` | Dynamic discovery | Explicit Windows port, such as `\\.\Usbscan3`; historical port numbers are not fixed addresses |
| `--timeout` | `30.0` seconds | Async-result wait budget for setup operations |
| `--io-timeout` | `120.0` seconds | Per-I/O libusb timeout, separate from the setup wait budget |
| `--encoding` | `utf-8` | Device text-field encoding; CLI JSON/help output uses UTF-8 |
| `--legacy-key` | Off | Use the alternative official `pFus...` key-obfuscation seed branch; iX100/iX110 default to `aQwe...`; profile commands use the official fixed seed |
| `--show-secrets` | Off | Display decoded secrets and hexadecimal binary content |
| `--output-file` | stdout | Save result JSON with the same redaction as stdout |
| `--binary-output-file` | No export | Explicitly save `get-eeprom` bytes or `get-device-file` `data` unchanged; batches save the last binary result. Raw-byte export is independent of JSON `--show-secrets` redaction |

## Profile JSON: `--profiles-file`

`set-profiles` and `replace-profiles` both accept JSON arrays with these field types and meanings:

| JSON field | Type | Meaning |
| --- | --- | --- |
| `index` | Integer | Zero-based existing profile index, as returned by `get-profiles` |
| `ssid` | String | Router SSID |
| `security` | String | Official authentication-type text, such as `WPA2` |
| `encryption` | String | Official encryption-type text, such as `AES` |
| `eap_type` | String | EAP-type text |
| `ca_check` | Integer | Official raw CA-check integer |
| `phase2` | String | EAP phase-two authentication text |
| `user_id` | String | 802.1X user identity |
| `eap_password` | String | 802.1X identity password, separate from Wi-Fi PSK |
| `anonymous_identity` | String | Anonymous identity |
| `wifi_key` | String | Wireless key, separate from the scan connection password |
| `certificate_name` | String | Registered client-certificate name |
| `dhcp` | Integer | Official raw DHCP integer |
| `ip` | String | IPv4 address |
| `netmask` | String | IPv4 subnet mask |
| `gateway` | String | IPv4 gateway |

`set-profiles` performs partial updates: each entry requires `index`, with only fields to change supplied. It first reads the complete raw device list and changes corresponding bytes, preserving unspecified fields, other profiles and unknown fields without changing the profile count. This `profile-patch.json` changes only the first profile's IP settings:

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

Apply with `py .\src\setup_cli.py set-profiles --profiles-file .\profile-patch.json --backend usbscan`. These are fictional documentation addresses; replace them with real deployment values.

`replace-profiles` specifies a complete new list: array order sets the new order and array length sets the new count. Entries with `index` copy an existing profile and apply changes; entries without it start from a blank record. Omitted profiles leave the active list, and `[]` explicitly clears it. For example, `[{"index":1},{"index":0}]` keeps only original profiles 1 and 0 in reversed order.

The Python return value of `get-profiles` can be edited programmatically. The CLI's default `<redacted>` is a display placeholder, not a password to write back. To change only IP fields, use a partial-update file and omit key fields.

## `run-file`: sequential execution in one USB session

`run-file --commands-file` accepts a UTF-8 JSON array whose entries contain:

| Field | Content |
| --- | --- |
| `command` | Function or CLI name, such as `set_wifi` or `set-wifi` |
| `arguments` | Keyword-argument object using underscore names; omit for commands without arguments |

Put scalars and lists directly in `arguments`; `profiles` is the array itself, not `profiles_file`. For function `bytes` arguments, the JSON value is a file path relative to the command JSON directory. For example, `upload_certificate` can use `"certificates/client.p12"` as `arguments.data`.

This `configure.example.json` illustrates the format only; SSID and key are fictional placeholders. Replace them with the target network settings before deployment:

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

Run with `py .\src\setup_cli.py run-file --commands-file .\configure.example.json --backend usbscan`.

Command files and binary inputs are read first, then USB is opened once and setup ownership acquired once. Entries run serially on the same `device`. A batch stops on error and reports completed and failed operations; applied settings are not automatically rolled back. Normal output is an array of operation results. Passwords in files are user-supplied configuration and are not echoed as arguments.

## Starting, receiving and cancelling WPS

`start-wps`, `start-ap-wps` and `start-profile-wps` default to `wait=True`: the same call starts pairing and waits for the result before releasing the session. An empty `pin` selects push-button mode; `--pin` (including prompted input) selects PIN mode.

Keep asynchronous steps in the same Python `with connect(...)` or `run-file`. This example starts STA push-button WPS and receives its result in the same session:

```json
[
  {"command": "start_wps", "arguments": {"wait": false}},
  {"command": "get_wps_result", "arguments": {"wait": true}}
]
```

Call `cancel_wps()` in the same session to cancel pending STA/AP/profile WPS. It replaces the current WPS request and waits for cancellation by default. Other commands cannot overwrite a pending setup request. Exiting a standalone `start-wps --no-wait` CLI releases its session; a second CLI's `get-wps-result` cannot be expected to continue it. Polling with `wait=False` reports a pending error while the device is busy, for Python callers that handle it themselves. Batch execution does not automatically turn that error into a polling loop.

## Complete function list

“Changes device state” includes configuration changes, pairing/diagnostics and session control. “No” means a read function, which still communicates over USB. Support depends on model and firmware; the complete list does not mean every function is supported or validated on iX100/iX110.

<!-- GENERATED API TABLES -->


There are 86 device functions, each with a corresponding CLI subcommand. Yes/No indicates whether the operation changes device state.

### core.py: Session control

| Function signature | CLI subcommand | Description | Changes device state |
| --- | --- | --- | --- |
| `acquire_setup() -> dict` | `acquire-setup` | Acquire the USB wireless setup session (the CLI releases it on exit) | Yes |
| `release_setup() -> dict` | `release-setup` | Release the current USB wireless setup session | Yes |

### info.py: Identity, device information and wireless discovery

| Function signature | CLI subcommand | Description | Changes device state |
| --- | --- | --- | --- |
| `get_configfile() -> dict` | `get-configfile` | Read the complete network configuration file and decoded system fields, including secrets | No |
| `get_configfile_size() -> int` | `get-configfile-size` | Read the device configuration file size | No |
| `get_connection_status(extended: bool = True) -> dict` | `get-connection-status` | Read the current wireless connection status | No |
| `get_device_info(include_system: bool = True) -> dict` | `get-device-info` | Read basic device network information | No |
| `get_device_info_8021x(include_system: bool = True) -> dict` | `get-device-info-8021x` | Read extended 802.1X device network information | No |
| `get_eeprom() -> bytes` | `get-eeprom` | Read the raw 512-byte chassis EEPROM | No |
| `get_eeprom_area() -> int` | `get-eeprom-area` | Read the EEPROM area byte (enumeration meanings are unconfirmed) | No |
| `get_firmware_info() -> dict` | `get-firmware-info` | Read device firmware version and raw version records | No |
| `get_firmware_version() -> str` | `get-firmware-version` | Read the device firmware version | No |
| `get_functional_version() -> str` | `get-functional-version` | Read the wireless functional version | No |
| `get_ip_settings(extended: bool = True) -> dict` | `get-ip-settings` | Read DHCP, IPv4, subnet mask and gateway settings | No |
| `get_mac_address(extended: bool = True) -> str` | `get-mac-address` | Read the device MAC address | No |
| `get_model() -> str` | `get-model` | Read the scanner model name | No |
| `get_model_info() -> dict` | `get-model-info` | Read standard INQUIRY model information | No |
| `get_profile_number() -> int` | `get-profile-number` | Read the current Wi-Fi profile number | No |
| `get_scanner_name(extended: bool = True) -> str` | `get-scanner-name` | Read the scanner network name | No |
| `get_serial_info() -> dict` | `get-serial-info` | Read the chassis serial number and EEPROM area field | No |
| `get_serial_number() -> str` | `get-serial-number` | Read the chassis serial number | No |
| `get_system_settings() -> dict` | `get-system-settings` | Read connection password settings and ReadyNotificationPort | No |
| `get_wifi_settings(extended: bool = True) -> dict` | `get-wifi-settings` | Read router SSID, authentication and encryption settings | No |
| `get_wifi_status() -> dict` | `get-wifi-status` | Read the hardware Wi-Fi switch state | No |
| `scan_access_points() -> list` | `scan-access-points` | Search for nearby wireless networks using the scanner | No |
| `scan_access_points_8021x() -> list` | `scan-access-points-8021x` | Search for wireless networks including 802.1X information using the scanner | No |

### wifi.py: STA, AP, profiles and WPS

| Function signature | CLI subcommand | Description | Changes device state |
| --- | --- | --- | --- |
| `apply_profiles() -> None` | `apply-profiles` | Apply the saved Wi-Fi profiles | Yes |
| `cancel_wps(wait: bool = True) -> None` | `cancel-wps` | Cancel WPS pairing and wait for the result in the same session by default | Yes |
| `diagnose_profile(profile_no: int) -> None` | `diagnose-profile` | Diagnose the Wi-Fi connection for the specified profile number | Yes |
| `diagnose_wifi() -> None` | `diagnose-wifi` | Diagnose the configured STA wireless connection | Yes |
| `get_ap_settings() -> dict` | `get-ap-settings` | Read direct-connect AP SSID, security, IP and DHCP server settings | No |
| `get_ap_system_info() -> dict` | `get-ap-system-info` | Read direct-connect AP status, MAC, scanner name and connection settings | No |
| `get_ap_wps_mode3_result(wait: bool = True) -> None` | `get-ap-wps-mode3-result` | Receive the AP WPS mode 3 result in the current USB session | No |
| `get_ap_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-ap-wps-result` | Receive the direct-connect AP WPS result in the current USB session | No |
| `get_profile_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-profile-wps-result` | Receive the profile WPS result in the current USB session | No |
| `get_profiles() -> list` | `get-profiles` | Read all saved Wi-Fi profiles and their IP settings | No |
| `get_startup_wifi_mode() -> int` | `get-startup-wifi-mode` | Read the startup Wi-Fi mode | No |
| `get_wifi_mode() -> int` | `get-wifi-mode` | Read the current Wi-Fi mode | No |
| `get_wps_cancel_result(wait: bool = True) -> None` | `get-wps-cancel-result` | Receive the WPS cancellation result in the current USB session | No |
| `get_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-wps-result` | Receive the started STA WPS result in the current USB session | No |
| `register_profile(profile_no: int, ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', certificate_name: str = '', ca_check: int = 0) -> None` | `register-profile` | Register a Wi-Fi / 802.1X profile at the specified number | Yes |
| `replace_profiles(profiles: list) -> None` | `replace-profiles` | Explicitly replace the profile list: retain/reorder by index and remove omitted profiles from the active list | Yes |
| `set_ap_ip(ip: str, netmask: str, dhcp_server: int, lease_time: int, lease_start: str, lease_end: str) -> None` | `set-ap-ip` | Set direct-connect AP IPv4, netmask, DHCP server, lease time and address pool | Yes |
| `set_ap_wifi(ssid: str, stealth: int, channel: int, security: str, encryption: str, wifi_key: str, key_display: int = 0) -> None` | `set-ap-wifi` | Set direct-connect AP SSID, stealth mode, channel and security parameters | Yes |
| `set_ap_wps_status(status: int) -> None` | `set-ap-wps-status` | Set the direct-connect AP WPS status | Yes |
| `set_ip(dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-ip` | Set STA DHCP or static IPv4, netmask and gateway | Yes |
| `set_profile_ip(index: int, dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-profile-ip` | Update DHCP/IP settings of one existing profile, preserving other profiles and keys | Yes |
| `set_profiles(profiles: list) -> None` | `set-profiles` | Update existing profiles by zero-based index, preserving unspecified profiles and unknown fields | Yes |
| `set_startup_wifi_mode(mode: int) -> None` | `set-startup-wifi-mode` | Set the startup Wi-Fi mode (iX100 branch) | Yes |
| `set_wifi(ssid: str, security: str, encryption: str, wifi_key: str) -> None` | `set-wifi` | Set router SSID, authentication, encryption and Wi-Fi key | Yes |
| `set_wifi_8021x(ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', ca_check: int = 0) -> None` | `set-wifi-8021x` | Set STA 802.1X / EAP identity, certificate checking and wireless key | Yes |
| `set_wifi_mode(mode: int) -> None` | `set-wifi-mode` | Switch Wi-Fi mode immediately (iX100 branch) | Yes |
| `start_ap_wps(pin: str = '', wait: bool = True) -> None` | `start-ap-wps` | Start direct-connect AP WPS push-button/PIN pairing and wait by default | Yes |
| `start_ap_wps_mode3(wait: bool = True) -> None` | `start-ap-wps-mode3` | Start the official AP WPS mode 3 operation and wait by default | Yes |
| `start_profile_wps(pin: str = '', wait: bool = True) -> None` | `start-profile-wps` | Register a profile using WPS push-button/PIN pairing and wait by default | Yes |
| `start_wps(pin: str = '', wait: bool = True) -> None` | `start-wps` | Start STA WPS push-button/PIN pairing and wait in the same session by default | Yes |

### advanced.py: System, ports, certificates and extended settings

| Function signature | CLI subcommand | Description | Changes device state |
| --- | --- | --- | --- |
| `delete_certificate(kind: int, filename: str = '') -> dict` | `delete-certificate` | Delete the specified certificate | Yes |
| `erase_access_token() -> dict` | `erase-access-token` | Erase the device access token by entering maintenance mode and issuing the official command | Yes |
| `execute_device_command(command: str) -> dict` | `execute-device-command` | Execute a device command through the official maintenance interface | Yes |
| `get_certificate_info(kind: int, get_info: int, filename: str = '') -> dict` | `get-certificate-info` | Read certificate details | No |
| `get_connect_frequency() -> dict` | `get-connect-frequency` | Read the connection frequency-band enumeration (officially iX1300 only) | No |
| `get_device_auth() -> dict` | `get-device-auth` | Read the device authentication key (query branch of Usb_Operate_Auth_Device for older models) | No |
| `get_device_auth_requirement() -> dict` | `get-device-auth-requirement` | Read device authentication requirements and official status codes | No |
| `get_device_file(path: str) -> dict` | `get-device-file` | Read a device file through the official paginated interface | No |
| `get_dns() -> dict` | `get-dns` | Read DNS settings (official binary branch for iX1300/iX1500/iX1600 only) | No |
| `get_eh_port() -> dict` | `get-eh-port` | Read the EH/ReadyNotificationPort notification port | No |
| `get_maintenance_mode() -> dict` | `get-maintenance-mode` | Read maintenance mode | No |
| `get_protocol() -> dict` | `get-protocol` | Read the communication protocol enumeration, not a port number | No |
| `get_proxy() -> dict` | `get-proxy` | Read proxy settings (official binary branch for iX1300/iX1500/iX1600 only) | No |
| `get_registered_pcs() -> dict` | `get-registered-pcs` | Read the two sets of registered PC host IDs | No |
| `get_roaming() -> dict` | `get-roaming` | Read the roaming enumeration (officially iX1300 only) | No |
| `initialize_registered_pcs() -> dict` | `initialize-registered-pcs` | Initialize PC registration data (CLR HOSTID ADATA) | Yes |
| `list_certificates(kind: int) -> dict` | `list-certificates` | Read the certificate list | No |
| `register_certificate(kind: int, filename: str, password: str = '') -> dict` | `register-certificate` | Register an uploaded certificate and its import password | Yes |
| `register_pc(host_id: str, additional_host_id: str = '') -> dict` | `register-pc` | Register PC host IDs as hexadecimal strings | Yes |
| `reset_invalidation(value: int) -> dict` | `reset-invalidation` | Write the raw integer argument for official Reset_invalidation | Yes |
| `reset_wifi_settings() -> dict` | `reset-wifi-settings` | Reset wireless settings and reproduce the official iX110 name/SSID restoration branch | Yes |
| `set_connect_frequency(frequency: int) -> dict` | `set-connect-frequency` | Set the connection frequency-band enumeration (officially iX1300 only) | Yes |
| `set_dns(mode: int, primary: str = '', secondary: str = '') -> dict` | `set-dns` | Set DNS settings (official binary branch for iX1300/iX1500/iX1600 only) | Yes |
| `set_eh_port(port: int) -> dict` | `set-eh-port` | Set the EH/ReadyNotificationPort notification port | Yes |
| `set_maintenance_mode(mode: int) -> dict` | `set-maintenance-mode` | Set maintenance mode (official token erasure enters with 1 and exits with 0) | Yes |
| `set_possession_setting(value: int) -> dict` | `set-possession-setting` | Write official Possession_Setting (SET OCCUPA RIGHT) | Yes |
| `set_protocol(protocol: int) -> dict` | `set-protocol` | Set the communication protocol enumeration (official values 0/1, not port numbers) | Yes |
| `set_proxy(enabled: bool, address: str = '', port: int = 8080, authentication: bool = False, username: str = '', password: str = '') -> dict` | `set-proxy` | Set proxy settings (official binary branch for iX1300/iX1500/iX1600 only) | Yes |
| `set_roaming(roaming: int) -> dict` | `set-roaming` | Set the roaming enumeration (officially iX1300 only) | Yes |
| `set_system_settings(name: str, password: str = '', password_display: int = 0) -> dict` | `set-system-settings` | Set the scanner name, scan connection password and password display setting | Yes |
| `upload_certificate(data: bytes, file_id: str = 'CertificateFile') -> dict` | `upload-certificate` | Upload a certificate file to device temporary storage | Yes |
