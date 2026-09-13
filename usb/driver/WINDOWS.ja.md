# Windows ドライバー設定

[简体中文](WINDOWS.md) | [English](WINDOWS.en.md) | [日本語](WINDOWS.ja.md)

USB スキャンと同梱の [Wi-Fi setup](../../wifi-setup/README.ja.md) に適用する説明です。Wi-Fi setup は USB 経由で無線ネットワークを設定するため、適切な USB ドライバーの割り当てが必要です。Wi-Fi のみでのスキャンにはこれらの USB ドライバーは不要です。

## ドライバーの選択

| 現在の状態 | 設定方法 | プログラムのオプション |
| --- | --- | --- |
| ScanSnap 公式 USB ドライバー導入済み | 現在の割り当てを維持し、実行前に ScanSnap Home を終了 | `--backend usbscan` |
| 公式ソフト未導入、または汎用 USB ドライバーを使いたい | 以下の手順で Zadig を使い WinUSB に割り当て | `--backend libusb` |
| WinUSB に割り当て済み | Python 依存関係を導入して使用 | `--backend libusb` |

`usbscan.sys` と `winusb.sys` は同じ USB インターフェイスに対する別の割り当てです。WinUSB に切り替えると ScanSnap Home はそのインターフェイスを利用できません。公式の USB 機能が必要になったら、以下の手順で復元してください。

既定の `--backend auto` は libusb を優先し、Windows でオープンに失敗した場合のみ usbscan にフォールバックします。ドライバーの導入や切り替えは行わず、スキャン・設定中にバックエンドも変更しません。

## 対象デバイスの確認

スキャナーを接続して電源を入れ、デバイスマネージャーで「プロパティ → 詳細 → ハードウェア ID」を開いて確認します：

| 機種 | ハードウェア ID |
| --- | --- |
| ScanSnap iX110 | `USB\VID_05CA&PID_03C8` |
| ScanSnap iX100 | `USB\VID_04C5&PID_13F4` |

ID の末尾に `&REV_...` が付く場合があります。iX110 の公式ドライバー名が iX100 と表示されることもあるため、VID/PID で選択してください。「ドライバー → ドライバーの詳細」で、現在 `usbscan.sys` と `winusb.sys` のどちらを使用しているか確認できます。

## 導入済み公式ドライバーの利用

公式 USB ドライバーが正常に動作していれば割り当ての変更は不要です。ScanSnap Home と他のスキャンプログラムを終了して、本プロジェクトの Python 依存関係を導入します。

公式ドライバーの導入・修復が必要なら、販売地域に対応する [ScanSnap 公式ソフトウェアダウンロード](https://www.pfu.ricoh.com/global/scanners/scansnap/support/software/org56.html)で機種と Windows を選択し、インストーラーに従ってください。このリリースには Ricoh/PFU の公式ドライバーファイルは含まれません。

スキャン時は `--backend usbscan` を使用します。Usbscan ポートは動的に検出するため、番号が固定とは限りません。USB スキャンと Wi-Fi setup はデバイスを排他的に使用し、同時実行できません。

## Zadig による WinUSB の設定

現在のデバイスドライバーを手動で導入・置換する手順です。先にスキャン・設定ジョブと関連プログラムを終了します。

1. [Zadig 公式サイト](https://zadig.akeo.ie/)からダウンロードして起動し、Windows に求められたら管理者権限を許可します。
2. `Options → List All Devices` を有効にし、公式ドライバー導入済みの機器も表示します。
3. スキャナーを選択し、`USB ID` が `05CA:03C8` または `04C5:13F4` であることを確認します。USB ハブや他の機器を選ばないでください。
4. 対象ドライバーとして **WinUSB** を選択します。
5. 機器と対象ドライバーを確認し、`Install Driver` または `Replace Driver` をクリックします。表示は現在の割り当てにより異なります。
6. インストール成功を待ち、現在のドライバーが WinUSB と表示されることを確認して Zadig を閉じます。

画面操作は [Zadig 公式ガイド](https://github.com/pbatard/libwdi/wiki/Zadig#basic-usage)に基づきます。Zadig がローカル機器への割り当てを導入するため、本プロジェクトの開発用 INF テンプレートは不要です。現在、署名済み WinUSB 自動インストーラーは配布していません。

## 依存関係の導入と実行

Python 3.11 以降が必要です。`ix100/usb/` から実行します：

```powershell
python -m pip install -r requirements.txt
python -B src/scan_direct.py --help
```

`requirements.txt` は PyUSB、および Windows 用の `libusb-package` と libusb DLL を提供し、DLL の手動コピーは不要です。Python 依存関係の導入だけでは WinUSB に割り当てられません。上記の手順を別途完了してください。`--help` は入口の確認のみで、機器にアクセスせず、ドライバーが使えることも証明しません。

実際にスキャンする際は用紙を挿入し、現在の割り当てに合うコマンドを 1 つ選びます：

```powershell
# 公式 usbscan ドライバー
python src/scan_direct.py --backend usbscan

# WinUSB ドライバー
python src/scan_direct.py --backend libusb
```

どちらも実際にデバイスにアクセスして 1 ページをスキャンします。連続スキャンと他のオプションは [USB 使用方法](../README.ja.md)を参照してください。

Wi-Fi setup は独自の依存関係と入口を使います。`usbscan` バックエンドは Python 標準ライブラリと割り当て済みの公式ドライバーだけで動作します。`libusb` では `ix100/wifi-setup/` の `requirements.txt` を導入します。接続オプションはデバイスサブコマンドの後に指定します。詳細は [Wi-Fi setup](../../wifi-setup/README.ja.md)を参照してください。

## 公式ドライバーの復元

本プロジェクトのスキャン・設定ジョブを終了し、デバイスマネージャーでハードウェア ID を使ってスキャナーを探します。

- 「プロパティ → ドライバー → ドライバーを元に戻す」が使用可能で、前のドライバーが公式版なら、この操作で復元します。
- 戻せない場合は対応機種の公式インストーラーで修復または再インストールします。完全な公式ドライバーパッケージがある場合は、「ドライバーの更新 → コンピューターを参照してドライバーを検索」でその場所を指定できます。

Windows の指示に従い、要求された場合のみ再起動します。復元後に `usbscan.sys` を確認し、本プロジェクトでは `--backend usbscan` を使用します。手動導入とロールバックは [Microsoft のデバイスマネージャーの説明](https://support.microsoft.com/en-us/windows/update-drivers-through-device-manager-in-windows-ec62f46c-ff14-c91d-eead-d7126dc1f7b6)を参照してください。

## よくある問題

| 症状 | 確認事項 |
| --- | --- |
| Zadig にスキャナーが表示されない | USB 接続・電源を確認し `List All Devices` を有効化 |
| `libusb-package is required` または libusb DLL を読み込めない | 実行時と同じ Python で `requirements.txt` を導入 |
| libusb がスキャナーを検出・オープンできない | ハードウェア ID と WinUSB 割り当てを確認し、使用中のプログラムを終了 |
| usbscan がポートを検出できない | 公式 `usbscan.sys` への割り当てを確認。WinUSB に変更済みなら `libusb` を使用 |
| 使用中またはアクセス拒否と表示される | 他のスキャン・設定ジョブと公式ソフトを終了。管理者権限でも他のプログラムの排他使用は解除できない |
| WinUSB 導入後に公式ソフトで USB スキャンできない | 上の手順で公式ドライバーを復元 |

ドライバーの導入やヘルプの表示に成功しても、すべてのスキャンモードの実機検証が完了したことにはなりません。
