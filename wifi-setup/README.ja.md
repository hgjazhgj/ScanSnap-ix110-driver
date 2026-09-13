# iX100 / iX110 Wi-Fi 設定

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

USB 経由でスキャナーの無線ネットワークを読み取り・設定するツールです。86 個の Python デバイス関数と対応する CLI を提供します。STA/AP、無線プロファイル、WPS、IP、スキャン接続パスワード、EH 通知ポート、PC 関連付け、証明書などに対応します。全パラメーターは[関数・CLI リファレンス](doc/FUNCTIONS.ja.md)を参照してください。

実行時に公式のユーザーモード DLL は読み込みません。iX110 で MAC・ネットワーク設定・プロファイル・AP・証明書一覧を含む USB 情報の読み取りを確認しています。**設定の書き込みは実機未検証です**。機種やファームウェアによって一部機能に対応しない場合があります。

## 導入と入口

Python 3.11 以降が必要です。`ix100/wifi-setup/` から実行します：

```powershell
py .\src\setup_cli.py --help
py .\src\setup_cli.py list-functions
py .\src\setup_cli.py set-wifi --help
```

上記のヘルプ・関数一覧はオフラインです。他のデバイスサブコマンドは、情報読み取りや状態照会も含め USB で機器にアクセスします。接続オプションはデバイスサブコマンドの後に指定します。

Windows の `--backend usbscan` は Python 標準ライブラリと割り当て済みの公式 `usbscan.sys` ドライバーのみ必要です。libusb では先に依存関係を導入します：

```powershell
py -m pip install -r .\requirements.txt
```

ドライバーの割り当てと Linux の権限は、同梱の [USB ドライバー説明](../usb/driver/README.ja.md)を参照してください。本ツールはドライバーの導入・割り当て変更を行いません。`auto` は libusb を優先し、オープン失敗時のみ usbscan にフォールバックします。操作開始後は変更しません。

## 読み取りと設定

以下は機器にアクセスします：

```powershell
py .\src\setup_cli.py get-mac-address --backend usbscan
py .\src\setup_cli.py get-serial-number --backend usbscan
py .\src\setup_cli.py get-profiles --backend usbscan
py .\src\setup_cli.py get-system-settings --backend usbscan
```

Windows のポートは USB ID で動的検出します。複数台の場合は `--usbscan-port '\\.\Usbscan3'` で明示できますが、番号は変わる可能性があります。

STA 無線ネットワーク設定の基本形です。SSID は実際のネットワーク名に置き換えます：

```powershell
py .\src\setup_cli.py set-wifi --backend usbscan --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-ip --backend usbscan --dhcp 1
```

`--wifi-key` に値を付けない場合、入力内容を表示せず無線キーを尋ねます。`--password` や `--pin` などの秘密引数も同様です。無線キーとスキャン接続パスワードは別のフィールドです。

無線プロファイル対応機器では次の手順を使えます：

```powershell
py .\src\setup_cli.py register-profile --backend usbscan --profile-no 0 --ssid ExampleNetwork --security WPA2 --encryption AES --wifi-key
py .\src\setup_cli.py set-profile-ip --backend usbscan --index 0 --dhcp 1
py .\src\setup_cli.py apply-profiles --backend usbscan
```

番号は 0 始まりです。既存番号への登録は上書きとなり、追加時は現在のプロファイル数を指定します。`set_profiles()` / `set_profile_ip()` は他のプロファイルと未指定フィールドを保持し、`replace_profiles()` は一覧全体を明示的に置換します。保存と適用は別操作です。

## Python API とバッチ処理

このディレクトリの `src/` を `PYTHONPATH` に追加するか、`src/` から Python を起動します。`src/` で `py -m ix100_setup --help` を実行しても同じ CLI 入口を使います。

実行モジュールは `src/` 直下にあり、`ix100_setup.py` が公開 Python API とモジュール入口、`setup_cli.py` がスクリプト入口を提供します。

```python
from ix100_setup import connect

with connect("usbscan") as device:
    mac = device.get_mac_address()
    profiles = device.get_profiles()
```

`connect()` は USB オープン、設定セッションの所有権取得・解放、バックエンドのクローズを管理します。同一セッションでは順番に操作します。関数は辞書・リスト・文字列・整数・バイト列・`None` を返し、失敗時に例外を送出します。

`set_system_settings(name, password="", password_display=0)` は名前とスキャン接続パスワードを同時変更します。**空のパスワードはパスワード要求を無効化します**。名前だけ変える場合は、先に既存のパスワード設定を読み取り保持します：

```python
with connect("usbscan") as device:
    system = device.get_system_settings()
    device.set_system_settings(
        "OfficeScanner", system["password"], system["password_display"]
    )
```

`run-file --commands-file jobs.local.json` は同一セッションで複数コマンドを順次実行します。WPS は既定で同一セッション内で完了を待ちます。必要に応じて `--timeout 180` を設定してください。非同期開始後の結果取得・取消も同一 Python セッションまたは同じ `run-file` にまとめます。バッチ失敗時も完了した操作はロールバックしません。JSON 形式・関数シグネチャ・オプションは[完全リファレンス](doc/FUNCTIONS.ja.md)を参照してください。

## 出力と対応範囲

CLI は既定でパスワード・キー・token・バイナリ内容を隠します。`--show-secrets` で明示的に表示し、`--output-file` は同じ JSON を保存します。`--binary-output-file` は EEPROM またはデバイスファイルの完全な生バイト列を明示保存し、JSON のマスキングとは独立しています。Python の戻り値は実際の値を含み、保存・ログは呼び出し側で管理します。

設定可能な通知ポートは EH / `ReadyNotificationPort` で、通常 53220 です。スキャン TCP/53218、TCP/53219、検出 UDP/52217 の永続的なポート設定 API はありません。EEPROM のシリアル番号は本体のもので、無線チップ固有の番号取得や MAC 書き換え API はありません。

DNS・プロキシは実装済みの iX1300/iX1500/iX1600 分岐、周波数帯・ローミングは iX1300 に限定され、iX100/iX110 では非対応エラーになります。拡張機器情報・802.1X・プロファイル・AP は機能バージョンに依存します。古いファームウェアでは関連する基本情報 getter に `--no-extended` を指定できます。

`src/` は実行ソース、`doc/` は使用リファレンス、`requirements.txt` は任意の libusb 依存関係です。
