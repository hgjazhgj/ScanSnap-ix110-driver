# iX100 / iX110 Wi-Fi setup

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

Read and configure the scanner's wireless network over USB, with 86 Python device functions and corresponding CLI commands. Supports STA/AP, wireless profiles, WPS, IP, scan connection passwords, EH notification ports, PC registration and certificates. See the [function and CLI reference](doc/FUNCTIONS.en.md) for all parameters.

No official user-mode DLLs are loaded at runtime. USB information reading has been tested on iX110, covering MAC, network configuration, profiles, AP and certificate lists. **Configuration writes have not been validated on hardware**; some functions may be unsupported on particular models or firmware.

## Installation and entry points

Python 3.11 or later is required. Run from `ix100/wifi-setup/`:

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py set-wifi --help
```

These help and function-list commands run offline. All other device subcommands, including information reads and status queries, access the scanner over USB. Put connection options after the device subcommand.

On Windows, `--backend usbscan` only requires the Python standard library and an installed official `usbscan.sys` binding. For libusb, install dependencies first:

```powershell
py -m pip install -r .\requirements.txt
```

See the bundled [USB driver guide](../usb/driver/README.en.md) for driver bindings and Linux permissions. This tool does not install drivers or change bindings. `auto` tries libusb first, falling back to usbscan only if opening fails; it does not change backends after an operation starts.

## Reading and configuration

These commands access the device:

```powershell
py .\src\setup_cli.py get-mac-address --backend usbscan
py .\src\setup_cli.py get-serial-number --backend usbscan
py .\src\setup_cli.py get-profiles --backend usbscan
py .\src\setup_cli.py get-system-settings --backend usbscan
```

Windows ports are discovered dynamically by USB ID. With multiple devices, specify `--usbscan-port '\\.\Usbscan3'` explicitly if needed; port numbers can change.

Basic STA wireless configuration, replacing the SSID with your actual network name:

```powershell
py .\src\setup_cli.py set-wifi --backend usbscan --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-ip --backend usbscan --dhcp 1
```

Supplying `--wifi-key` without a value prompts for the wireless key without echoing it. Secret options such as `--password` and `--pin` also support this. The wireless key and scan connection password are separate fields.

For devices supporting wireless profiles:

```powershell
py .\src\setup_cli.py register-profile --backend usbscan --profile-no 0 --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-profile-ip --backend usbscan --index 0 --dhcp 1
py .\src\setup_cli.py apply-profiles --backend usbscan
```

Profile numbering starts at 0. Registering an existing number overwrites that profile; use the current profile count to append. `set_profiles()` / `set_profile_ip()` preserve other profiles and unspecified fields; `replace_profiles()` explicitly replaces the entire list. Saving and applying profiles are separate operations.

## Python API and batch execution

Add this directory's `src/` to `PYTHONPATH`, or start Python from `src/`. Running `py -m ix100_setup --help` from `src/` uses the same CLI entry point.

Runtime modules are directly in `src/`; `ix100_setup.py` provides the public Python API and module entry point, and `setup_cli.py` provides the script entry point.

```python
from ix100_setup import connect

with connect("usbscan") as device:
    mac = device.get_mac_address()
    profiles = device.get_profiles()
```

`connect()` manages USB opening, setup-session ownership and release, and backend closing. Operations in one session run sequentially. Functions return dictionaries, lists, strings, integers, bytes or `None`, and raise exceptions on failure.

`set_system_settings(name, password="", password_display=0)` changes both the name and scan connection password. **An empty password disables the password requirement.** To change only the name, first read and preserve the current password settings:

```python
with connect("usbscan") as device:
    system = device.get_system_settings()
    device.set_system_settings(
        "OfficeScanner", system["password"], system["password_display"]
    )
```

`run-file --commands-file jobs.local.json` executes multiple commands sequentially in one session. WPS waits for completion in that session by default; consider `--timeout 180` as needed. Reading results or cancelling after asynchronous startup should also remain in the same Python session or `run-file`. Batch failure does not roll back completed operations. See the [full reference](doc/FUNCTIONS.en.md) for JSON formats, signatures and options.

## Output and scope

The CLI hides passwords, keys, tokens and binary content by default. `--show-secrets` explicitly displays them; `--output-file` saves the same JSON. `--binary-output-file` explicitly saves complete raw EEPROM or device-file bytes, independently of JSON redaction. Python return values include actual fields; callers control saving and logging.

The configurable notification port is EH / `ReadyNotificationPort`, usually 53220. There is no persistent configuration interface for scan TCP/53218, TCP/53219 or discovery UDP/52217 ports. The EEPROM serial number is the chassis serial number; there is no separate radio-chip serial-number or MAC rewriting interface.

DNS/proxy support is limited to implemented iX1300/iX1500/iX1600 branches, and frequency/roaming to iX1300; iX100/iX110 report these as unsupported. Extended device information, 802.1X, profiles and AP features depend on functional version. Related basic-information getters can use `--no-extended` for older firmware.

`src/` contains runtime source, `doc/` contains usage references, and `requirements.txt` lists optional libusb dependencies.
