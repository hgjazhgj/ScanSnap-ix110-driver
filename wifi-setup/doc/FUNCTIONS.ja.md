# Python 関数・CLI リファレンス

[简体中文](FUNCTIONS.md) | [English](FUNCTIONS.en.md) | [日本語](FUNCTIONS.ja.md)

更新：2026-09-13。現在の Python API と対応する CLI の一覧です。iX110 で USB 情報読み取りを確認していますが、設定の書き込みは実機未検証です。導入・基本操作は[使用方法](../README.ja.md)を参照してください。

`ix100/wifi-setup/` から実行します：

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py list-functions --json
py .\src\setup_cli.py set-wifi --help
```

ヘルプ・一覧表示はオフラインです。他のデバイスサブコマンドは識別情報読み取り・状態照会を含め、USB を開き設定セッションを取得し、完了後に解放します。`src/` で `py -m ix100_setup` を実行しても同じ入口です。他の場所でインポートする場合は `src/` を `PYTHONPATH` に追加します。実行モジュールは `src/` 直下、公開 API は `ix100_setup.py` にあります。

`from ix100_setup import connect` を使い、`with connect("usbscan") as device:` で設定セッションを作成して、以下の関数を `device.関数(...)` として呼びます。`connect` はポートを自動検出し、終了時にセッションを解放・バックエンドを閉じます。公式 DLL は不要です。以下のシグネチャでは `self` を省略しています。

## 引数と結果の規則

- 関数名のアンダースコアは CLI ではハイフンになり、すべての引数を名前付きオプションで指定します。例：`set_wifi_mode(mode=0)` は `set-wifi-mode --mode 0`。
- 既定値がない引数は必須です。既定値がある引数を省略すると API の既定値を使います。整数・浮動小数点数は CLI が解析し、重複した範囲検証は追加していません。受理は機器の対応を意味しません。
- `bool` 引数は `--wait` / `--no-wait`、`--extended` / `--no-extended` のような対のスイッチです。必須の `enabled: bool` は `--enabled` または `--no-enabled` を明示します。
- `str` は文字列です。パスワード・キー・PIN は値を付けずにオプション名のみを指定すると、表示しない端末入力を要求します。例：`--wifi-key`、`--password`、`--pin`。パスワード引数自体の省略や明示的な空文字列は関数の既定値に従い、消去・無効化を意味する場合があります。各関数を確認してください。
- `list` / `dict` は UTF-8 JSON ファイルで渡し、オプション末尾に `-file` を付けます。例：`profiles` は `--profiles-file`。`bytes` も `-file` を付け、生バイト列を読みます。証明書アップロードは `--data-file` です。
- 正常出力は `operation` と `result` を含む UTF-8 JSON です。戻り値のない設定関数は `result: null` を返します。これは呼び出しの完了を示し、追加のネットワーク・用紙スキャン検証を意味しません。機器・プロトコル・I/O エラーは非ゼロの終了コードです。
- パスワード・キー・不透明なバイナリ内容は既定で非表示です。`--show-secrets` で明示表示できます。Python API は復号済みの値を返し、CLI の表示用マスキングは適用しません。

## 全デバイスサブコマンド共通オプション

`get-mac-address --backend usbscan` のようにサブコマンドの後に指定します。`run-file` にも適用し、オフラインの `list-functions` には適用しません。

| オプション | 既定値 | 用途 |
| --- | --- | --- |
| `--backend auto\|usbscan\|libusb` | `auto` | USB バックエンド選択。フォールバックはオープン時のみ。操作中に変更して再試行しない |
| `--usbscan-port` | 動的検出 | `\\.\Usbscan3` など Windows ポートを明示。過去の番号は固定アドレスではない |
| `--timeout` | `30.0` 秒 | setup 操作の非同期結果を待つ時間上限 |
| `--io-timeout` | `120.0` 秒 | libusb の単一 I/O タイムアウト。setup 待機上限とは別 |
| `--encoding` | `utf-8` | 機器文字フィールドのエンコード。CLI JSON・ヘルプは UTF-8 |
| `--legacy-key` | 無効 | 公式の別の `pFus...` キー難読化シード分岐を使用。iX100/iX110 は既定で `aQwe...`、プロファイルは公式の固定シード |
| `--show-secrets` | 無効 | 復号済み秘密情報とバイナリの 16 進内容を表示 |
| `--output-file` | stdout | stdout と同じマスキングで結果 JSON を保存 |
| `--binary-output-file` | 書き出さない | `get-eeprom` のバイト列または `get-device-file` の `data` をそのまま保存。バッチは最後のバイナリ結果。生バイト出力は JSON の `--show-secrets` マスキングとは独立 |

## プロファイル JSON：`--profiles-file`

`set-profiles` と `replace-profiles` はともに JSON 配列を受け付けます。フィールドの型と意味は以下のとおりです。

| JSON フィールド | 型 | 意味 |
| --- | --- | --- |
| `index` | 整数 | 既存プロファイルの 0 始まりインデックス。`get-profiles` が返す値 |
| `ssid` | 文字列 | ルーターの SSID |
| `security` | 文字列 | `WPA2` など公式認証方式の文字列 |
| `encryption` | 文字列 | `AES` など公式暗号方式の文字列 |
| `eap_type` | 文字列 | EAP 種別の文字列 |
| `ca_check` | 整数 | CA 検証の公式の生整数値 |
| `phase2` | 文字列 | EAP 第 2 段階認証の文字列 |
| `user_id` | 文字列 | 802.1X ユーザー ID |
| `eap_password` | 文字列 | 802.1X 認証パスワード。Wi-Fi PSK とは別 |
| `anonymous_identity` | 文字列 | 匿名 ID |
| `wifi_key` | 文字列 | 無線キー。スキャン接続パスワードとは別 |
| `certificate_name` | 文字列 | 登録済みクライアント証明書名 |
| `dhcp` | 整数 | DHCP の公式の生整数値 |
| `ip` | 文字列 | IPv4 アドレス |
| `netmask` | 文字列 | IPv4 サブネットマスク |
| `gateway` | 文字列 | IPv4 ゲートウェイ |

`set-profiles` は部分更新です。各項目に `index` が必須で、他は変更するフィールドだけを記入します。先に機器の完全な生一覧を読み、対応バイトを変更します。未指定フィールド・他のプロファイル・未知フィールドをすべて保持し、件数は変えません。次の `profile-patch.json` は先頭プロファイルの IP 設定だけを変更します：

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

適用コマンドは `py .\src\setup_cli.py set-profiles --profiles-file .\profile-patch.json --backend usbscan` です。アドレスは説明用の架空値なので、実際の環境に置き換えてください。

`replace-profiles` は新しい一覧全体を指定します。配列順が新しい順序、長さが新しい件数です。`index` のある項目は既存プロファイルをコピーして変更し、ない項目は空レコードから作成します。含めないプロファイルは有効一覧から外れ、`[]` は明示的に一覧を空にします。`[{"index":1},{"index":0}]` は元の 1 と 0 のみを逆順で残します。

`get-profiles` の Python 戻り値はプログラムで編集できます。CLI の既定の `<redacted>` は表示用であり、パスワードとして書き戻してはいけません。IP などだけを変える場合は部分更新ファイルを使い、キーは省略します。

## `run-file`：同一 USB セッション内の順次実行

`run-file --commands-file` は UTF-8 JSON 配列を受け付け、各項目は以下を含みます：

| フィールド | 内容 |
| --- | --- |
| `command` | `set_wifi` または `set-wifi` などの関数名・CLI 名 |
| `arguments` | アンダースコア名を使うキーワード引数オブジェクト。引数なしなら省略可能 |

スカラー・リストは `arguments` に直接記入します。`profiles` は配列そのもので、`profiles_file` ではありません。関数の `bytes` 引数は JSON ではファイルパスとし、相対パスはコマンド JSON のディレクトリが基準です。例：`upload_certificate` の `arguments.data` は `"certificates/client.p12"`。

次の `configure.example.json` は形式のみを示し、SSID とキーは架空のプレースホルダーです。実際のネットワーク設定に置き換えてから使用してください：

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

実行：`py .\src\setup_cli.py run-file --commands-file .\configure.example.json --backend usbscan`。

コマンドファイルとバイナリ入力を先に読み、USB を一度開いて setup 所有権を一度取得します。同じ `device` で順次実行します。エラーで停止し、完了操作と失敗操作を報告します。適用済み設定は自動ロールバックしません。正常結果は操作結果の配列です。ファイル内のパスワードはユーザー提供の設定として扱い、引数としてエコー表示しません。

## WPS の開始・結果受信・取消

`start-wps`、`start-ap-wps`、`start-profile-wps` は既定で `wait=True` です。同じ呼び出しでペアリングを開始し、結果を待ってからセッションを解放します。空の `pin` はプッシュボタン方式、`--pin`（端末入力も可能）は PIN 方式です。

非同期の分割操作は同じ Python の `with connect(...)` または同じ `run-file` に置きます。STA プッシュボタン WPS を開始し、同一セッションで結果を受け取る例：

```json
[
  {"command": "start_wps", "arguments": {"wait": false}},
  {"command": "get_wps_result", "arguments": {"wait": true}}
]
```

保留中の STA/AP/プロファイル WPS を取り消すには同一セッションで `cancel_wps()` を呼びます。現在の WPS 要求を置き換え、既定で取消結果を待ちます。他のコマンドは未完了の setup 要求を上書きできません。単独の `start-wps --no-wait` CLI を終了するとセッションを解放するため、別 CLI の `get-wps-result` で継続できるとは考えないでください。`wait=False` のポーリングは機器が処理中なら pending エラーを報告し、自分で状態処理する Python プログラム向けです。バッチはこのエラーを自動でポーリングループとして扱いません。

## 全関数一覧

「機器状態の変更」には設定変更・ペアリング・診断・セッション制御を含みます。「No」は読み取り機能ですが、USB 通信は行います。対応は機種・ファームウェアによって異なり、一覧の全機能が iX100/iX110 で対応・検証済みという意味ではありません。

<!-- GENERATED API TABLES -->


現在 86 個のデバイス関数があり、それぞれ対応する CLI サブコマンドがあります。Yes/No は機器状態を変更するかどうかを示します。

### core.py：セッション制御

| 関数シグネチャ | CLI サブコマンド | 説明 | 機器状態の変更 |
| --- | --- | --- | --- |
| `acquire_setup() -> dict` | `acquire-setup` | USB 無線設定セッションを取得（CLI 終了時に解放） | Yes |
| `release_setup() -> dict` | `release-setup` | 現在の USB 無線設定セッションを解放 | Yes |

### info.py：識別情報・機器情報・無線ネットワーク検索

| 関数シグネチャ | CLI サブコマンド | 説明 | 機器状態の変更 |
| --- | --- | --- | --- |
| `get_configfile() -> dict` | `get-configfile` | 完全なネットワーク設定ファイルと復号済みシステム項目を読み取り（秘密情報を含む） | No |
| `get_configfile_size() -> int` | `get-configfile-size` | 機器設定ファイルのサイズを読み取り | No |
| `get_connection_status(extended: bool = True) -> dict` | `get-connection-status` | 現在の無線接続状態を読み取り | No |
| `get_device_info(include_system: bool = True) -> dict` | `get-device-info` | 基本的な機器ネットワーク情報を読み取り | No |
| `get_device_info_8021x(include_system: bool = True) -> dict` | `get-device-info-8021x` | 802.1X 拡張機器ネットワーク情報を読み取り | No |
| `get_eeprom() -> bytes` | `get-eeprom` | 本体 EEPROM の生データ 512 バイトを読み取り | No |
| `get_eeprom_area() -> int` | `get-eeprom-area` | EEPROM の area バイトを読み取り（列挙値の意味は未確認） | No |
| `get_firmware_info() -> dict` | `get-firmware-info` | 機器ファームウェアのバージョンと生のバージョン記録を読み取り | No |
| `get_firmware_version() -> str` | `get-firmware-version` | 機器のファームウェアバージョンを読み取り | No |
| `get_functional_version() -> str` | `get-functional-version` | 無線機能バージョンを読み取り | No |
| `get_ip_settings(extended: bool = True) -> dict` | `get-ip-settings` | DHCP・IPv4・サブネットマスク・ゲートウェイを読み取り | No |
| `get_mac_address(extended: bool = True) -> str` | `get-mac-address` | 機器の MAC アドレスを読み取り | No |
| `get_model() -> str` | `get-model` | スキャナーの機種名を読み取り | No |
| `get_model_info() -> dict` | `get-model-info` | 標準 INQUIRY の機種情報を読み取り | No |
| `get_profile_number() -> int` | `get-profile-number` | 現在の Wi-Fi プロファイル番号を読み取り | No |
| `get_scanner_name(extended: bool = True) -> str` | `get-scanner-name` | スキャナーのネットワーク名を読み取り | No |
| `get_serial_info() -> dict` | `get-serial-info` | 本体シリアル番号と EEPROM area フィールドを読み取り | No |
| `get_serial_number() -> str` | `get-serial-number` | 本体シリアル番号を読み取り | No |
| `get_system_settings() -> dict` | `get-system-settings` | 接続パスワード設定と ReadyNotificationPort を読み取り | No |
| `get_wifi_settings(extended: bool = True) -> dict` | `get-wifi-settings` | ルーターの SSID・認証・暗号設定を読み取り | No |
| `get_wifi_status() -> dict` | `get-wifi-status` | ハードウェアの Wi-Fi スイッチ状態を読み取り | No |
| `scan_access_points() -> list` | `scan-access-points` | スキャナーで周囲の無線ネットワークを検索 | No |
| `scan_access_points_8021x() -> list` | `scan-access-points-8021x` | スキャナーで 802.1X 情報を含む無線ネットワークを検索 | No |

### wifi.py：STA・AP・プロファイル・WPS

| 関数シグネチャ | CLI サブコマンド | 説明 | 機器状態の変更 |
| --- | --- | --- | --- |
| `apply_profiles() -> None` | `apply-profiles` | 保存済み Wi-Fi プロファイルを適用 | Yes |
| `cancel_wps(wait: bool = True) -> None` | `cancel-wps` | WPS ペアリングを取り消し、既定で同一セッション内で結果を待機 | Yes |
| `diagnose_profile(profile_no: int) -> None` | `diagnose-profile` | 指定番号の Wi-Fi プロファイル接続を診断 | Yes |
| `diagnose_wifi() -> None` | `diagnose-wifi` | 設定済み STA 無線接続を診断 | Yes |
| `get_ap_settings() -> dict` | `get-ap-settings` | 直接接続 AP の SSID・セキュリティ・IP・DHCP サーバー設定を読み取り | No |
| `get_ap_system_info() -> dict` | `get-ap-system-info` | 直接接続 AP の状態・MAC・スキャナー名・接続設定を読み取り | No |
| `get_ap_wps_mode3_result(wait: bool = True) -> None` | `get-ap-wps-mode3-result` | 現在の USB セッションの AP WPS mode 3 結果を受信 | No |
| `get_ap_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-ap-wps-result` | 現在の USB セッションの直接接続 AP WPS 結果を受信 | No |
| `get_profile_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-profile-wps-result` | 現在の USB セッションのプロファイル WPS 結果を受信 | No |
| `get_profiles() -> list` | `get-profiles` | 保存済みの全 Wi-Fi プロファイルと各 IP 設定を読み取り | No |
| `get_startup_wifi_mode() -> int` | `get-startup-wifi-mode` | 起動時の Wi-Fi モードを読み取り | No |
| `get_wifi_mode() -> int` | `get-wifi-mode` | 現在の Wi-Fi モードを読み取り | No |
| `get_wps_cancel_result(wait: bool = True) -> None` | `get-wps-cancel-result` | 現在の USB セッションの WPS 取消結果を受信 | No |
| `get_wps_result(pin_mode: bool = False, wait: bool = True) -> None` | `get-wps-result` | 現在の USB セッションで開始した STA WPS の結果を受信 | No |
| `register_profile(profile_no: int, ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', certificate_name: str = '', ca_check: int = 0) -> None` | `register-profile` | 指定番号の Wi-Fi / 802.1X プロファイルを登録 | Yes |
| `replace_profiles(profiles: list) -> None` | `replace-profiles` | プロファイル一覧を明示置換。index で保持・並べ替えし、省略分は有効一覧から除外 | Yes |
| `set_ap_ip(ip: str, netmask: str, dhcp_server: int, lease_time: int, lease_start: str, lease_end: str) -> None` | `set-ap-ip` | 直接接続 AP の IPv4・マスク・DHCP サーバー・リース期間・アドレスプールを設定 | Yes |
| `set_ap_wifi(ssid: str, stealth: int, channel: int, security: str, encryption: str, wifi_key: str, key_display: int = 0) -> None` | `set-ap-wifi` | 直接接続 AP の SSID・非公開モード・チャネル・セキュリティを設定 | Yes |
| `set_ap_wps_status(status: int) -> None` | `set-ap-wps-status` | 直接接続 AP の WPS 状態を設定 | Yes |
| `set_ip(dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-ip` | STA の DHCP または固定 IPv4・マスク・ゲートウェイを設定 | Yes |
| `set_profile_ip(index: int, dhcp: int, ip: str = '', netmask: str = '', gateway: str = '') -> None` | `set-profile-ip` | 既存の 1 プロファイルの DHCP/IP を変更し、他のプロファイルとキーを保持 | Yes |
| `set_profiles(profiles: list) -> None` | `set-profiles` | 0 始まりの index で既存プロファイルを変更し、未指定プロファイルと未知フィールドを保持 | Yes |
| `set_startup_wifi_mode(mode: int) -> None` | `set-startup-wifi-mode` | 起動時の Wi-Fi モードを設定（iX100 分岐） | Yes |
| `set_wifi(ssid: str, security: str, encryption: str, wifi_key: str) -> None` | `set-wifi` | ルーターの SSID・認証方式・暗号方式・Wi-Fi キーを設定 | Yes |
| `set_wifi_8021x(ssid: str, security: str, encryption: str, eap_type: str = '', phase2: str = '', user_id: str = '', eap_password: str = '', anonymous_identity: str = '', wifi_key: str = '', ca_check: int = 0) -> None` | `set-wifi-8021x` | STA の 802.1X / EAP ID・証明書検証・無線キーを設定 | Yes |
| `set_wifi_mode(mode: int) -> None` | `set-wifi-mode` | Wi-Fi モードを即時切り替え（iX100 分岐） | Yes |
| `start_ap_wps(pin: str = '', wait: bool = True) -> None` | `start-ap-wps` | 直接接続 AP の WPS ボタン/PIN ペアリングを開始し、既定で結果を待機 | Yes |
| `start_ap_wps_mode3(wait: bool = True) -> None` | `start-ap-wps-mode3` | 公式 AP WPS mode 3 操作を開始し、既定で結果を待機 | Yes |
| `start_profile_wps(pin: str = '', wait: bool = True) -> None` | `start-profile-wps` | WPS ボタン/PIN でプロファイルを登録し、既定で結果を待機 | Yes |
| `start_wps(pin: str = '', wait: bool = True) -> None` | `start-wps` | STA WPS ボタン/PIN ペアリングを開始し、既定で同一セッション内で結果を待機 | Yes |

### advanced.py：システム・ポート・証明書・拡張設定

| 関数シグネチャ | CLI サブコマンド | 説明 | 機器状態の変更 |
| --- | --- | --- | --- |
| `delete_certificate(kind: int, filename: str = '') -> dict` | `delete-certificate` | 指定した証明書を削除 | Yes |
| `erase_access_token() -> dict` | `erase-access-token` | 保守モードに入り公式コマンドを実行して機器のアクセストークンを消去 | Yes |
| `execute_device_command(command: str) -> dict` | `execute-device-command` | 公式保守インターフェイスで機器コマンドを実行 | Yes |
| `get_certificate_info(kind: int, get_info: int, filename: str = '') -> dict` | `get-certificate-info` | 証明書の詳細を読み取り | No |
| `get_connect_frequency() -> dict` | `get-connect-frequency` | 接続周波数帯の列挙値を読み取り（公式では iX1300 のみ） | No |
| `get_device_auth() -> dict` | `get-device-auth` | 機器認証キーを読み取り（旧機種 Usb_Operate_Auth_Device の照会分岐） | No |
| `get_device_auth_requirement() -> dict` | `get-device-auth-requirement` | 機器認証要件と公式ステータスコードを読み取り | No |
| `get_device_file(path: str) -> dict` | `get-device-file` | 公式のページ分割インターフェイスで機器ファイルを読み取り | No |
| `get_dns() -> dict` | `get-dns` | DNS 設定を読み取り（公式の iX1300/iX1500/iX1600 用バイナリ分岐のみ） | No |
| `get_eh_port() -> dict` | `get-eh-port` | EH/ReadyNotificationPort 通知ポートを読み取り | No |
| `get_maintenance_mode() -> dict` | `get-maintenance-mode` | 保守モードを読み取り | No |
| `get_protocol() -> dict` | `get-protocol` | 通信プロトコル列挙値を読み取り（ポート番号ではない） | No |
| `get_proxy() -> dict` | `get-proxy` | プロキシ設定を読み取り（公式の iX1300/iX1500/iX1600 用バイナリ分岐のみ） | No |
| `get_registered_pcs() -> dict` | `get-registered-pcs` | 関連付け済み PC の 2 組のホスト ID を読み取り | No |
| `get_roaming() -> dict` | `get-roaming` | ローミング列挙値を読み取り（公式では iX1300 のみ） | No |
| `initialize_registered_pcs() -> dict` | `initialize-registered-pcs` | PC 関連付けデータを初期化（CLR HOSTID ADATA） | Yes |
| `list_certificates(kind: int) -> dict` | `list-certificates` | 証明書一覧を読み取り | No |
| `register_certificate(kind: int, filename: str, password: str = '') -> dict` | `register-certificate` | アップロード済み証明書とインポートパスワードを登録 | Yes |
| `register_pc(host_id: str, additional_host_id: str = '') -> dict` | `register-pc` | PC ホスト ID を 16 進文字列で登録 | Yes |
| `reset_invalidation(value: int) -> dict` | `reset-invalidation` | 公式 Reset_invalidation の生整数引数を書き込み | Yes |
| `reset_wifi_settings() -> dict` | `reset-wifi-settings` | 無線設定をリセットし、公式 iX110 の名前/SSID 復元分岐を再現 | Yes |
| `set_connect_frequency(frequency: int) -> dict` | `set-connect-frequency` | 接続周波数帯の列挙値を設定（公式では iX1300 のみ） | Yes |
| `set_dns(mode: int, primary: str = '', secondary: str = '') -> dict` | `set-dns` | DNS 設定を設定（公式の iX1300/iX1500/iX1600 用バイナリ分岐のみ） | Yes |
| `set_eh_port(port: int) -> dict` | `set-eh-port` | EH/ReadyNotificationPort 通知ポートを設定 | Yes |
| `set_maintenance_mode(mode: int) -> dict` | `set-maintenance-mode` | 保守モードを設定（公式 token 消去は 1 で開始、0 で終了） | Yes |
| `set_possession_setting(value: int) -> dict` | `set-possession-setting` | 公式 Possession_Setting を書き込み（SET OCCUPA RIGHT） | Yes |
| `set_protocol(protocol: int) -> dict` | `set-protocol` | 通信プロトコル列挙値を設定（公式値 0/1、ポート番号ではない） | Yes |
| `set_proxy(enabled: bool, address: str = '', port: int = 8080, authentication: bool = False, username: str = '', password: str = '') -> dict` | `set-proxy` | プロキシ設定を設定（公式の iX1300/iX1500/iX1600 用バイナリ分岐のみ） | Yes |
| `set_roaming(roaming: int) -> dict` | `set-roaming` | ローミング列挙値を設定（公式では iX1300 のみ） | Yes |
| `set_system_settings(name: str, password: str = '', password_display: int = 0) -> dict` | `set-system-settings` | スキャナー名・スキャン接続パスワード・パスワード表示設定を設定 | Yes |
| `upload_certificate(data: bytes, file_id: str = 'CertificateFile') -> dict` | `upload-certificate` | 証明書ファイルを機器の一時領域にアップロード | Yes |
