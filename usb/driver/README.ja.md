# ドライバーとデバイス権限

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

スキャン操作は[使用方法](../README.ja.md)を参照してください。USB スキャンと同梱の Wi-Fi setup は、同じドライバーの準備が必要です。

## Windows

ハードウェア ID の確認、導入済み公式ドライバーの利用、Zadig による WinUSB 設定、Python 依存関係の導入、公式ドライバーの復元は [Windows ドライバー設定](WINDOWS.ja.md)を参照してください。

公式ドライバー導入済みなら `--backend usbscan` を使い、実行前に ScanSnap Home を終了します。Python の依存関係は各コンポーネントの説明に従って導入してください。WinUSB に割り当て済みなら `--backend libusb` を使用します。

対応 USB ID は iX110 が `05CA:03C8`、iX100 が `04C5:13F4` です。iX110 の公式ドライバー名が iX100 と表示される場合があります。ポートは動的に検出するため、Usbscan 番号を固定する必要はありません。

このリリースには署名済み WinUSB インストーラーは含まれません。WinUSB と公式 usbscan は同じインターフェイスへの異なる割り当てです。WinUSB に切り替えると ScanSnap Home はその USB インターフェイスからデバイスにアクセスできなくなります。

## Linux

システムの libusb ランタイムを導入後、`ix100/usb/` から実行します：

```bash
sudo install -m 0644 driver/60-scansnap-ix100.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

スキャナーを再接続してください。デスクトップ環境が `TAG+=uaccess` に対応しない場合は、ローカルのユーザーグループに合わせて[権限ルール](60-scansnap-ix100.rules)を調整します。

## macOS

Homebrew を使用する場合は `brew install libusb` を実行し、続けてコンポーネントの Python 依存関係を導入します。
