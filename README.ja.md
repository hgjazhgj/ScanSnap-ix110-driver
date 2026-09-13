# ScanSnap iX100 / iX110 用の汎用サードパーティードライバー

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

携帯型スキャナーを購入しました。現在市販されている携帯型スキャナーで、Type-C 端子を備える唯一の製品かもしれません。  
ところが購入してみると、公式ドライバーはクソでした。非常に肥大化しているうえ、各機種のハードウェアドライバーと後段のソフトウェア画像処理が一体化しています（高校を中退して働き始めた日本の社畜には使いやすく、好評なのかもしれません）。さらに肝心のハードウェアドライバーが出力できるのは、非可逆圧縮形式の JPG と PDF だけ。これは受け入れられません。  
実際には、ハードウェア自体に非圧縮画像を出力する能力があります。

本プロジェクトの目標は、この機器を購入した誰もが公式アプリをダウンロード・インストールせずに、元の画像データを取得できるようにすることです。  
ただし民生用スキャナーであり、プロ用カメラではありません。ハードウェアには raw センサーデータの出力機能がなく、出力できるのはデモザイク処理後の BMP データです。

スキャナー本体は約 24,000 円でしたが、リバースエンジニアリングに使う AI だけでも、少なくとも 30,000 円の ChatGPT Pro 20x サブスクリプションが必要です。  
各モジュールを正しく動作させ、挙動を合わせるには、開発者が専門知識を持ったうえで相当量の手動の指示を与える必要があります。テスト中もハードウェアの状態を繰り返し手動で整えなければなりません。  
「きれいなリバースエンジニアリング結果を出して」と一言伝えるだけで、一度で完成する時代を心から待ち望んでいます。

このディレクトリに 3 つの独立したコンポーネントをまとめています。各コンポーネントの実行用ソースは `src/`、使用ドキュメントは `doc/`、Python の依存関係は各コンポーネントのルートにあります。

| コンポーネント | 用途 | 使用方法 |
| --- | --- | --- |
| `usb/` | USB で単一ページ・連続スキャンし、BMP を保存 | [USB スキャン](usb/README.ja.md) |
| `wifi/` | Wi-Fi で単一ページ・パネル起動・連続スキャンし、BMP を保存 | [Wi-Fi スキャン](wifi/README.ja.md) |
| `wifi-setup/` | USB 経由でスキャナーの無線設定を読み取り・設定 | [Wi-Fi setup](wifi-setup/README.ja.md) |

Python 3.11 以降が必要です。使用するコンポーネントのディレクトリに移動し、その README に従って依存関係とドライバーまたは設定を準備してください。このディレクトリから各コンポーネントのオフラインヘルプを表示する例：

```powershell
python -B usb/src/scan_direct.py --help
python -B wifi/src/scan_direct.py --help
python -B wifi-setup/src/setup_cli.py --help
```

リポジトリの残りの部分はほぼすべて AI が生成したもので、一部を加筆・削除しています。

## 全ドキュメント

| ドキュメント | 简体中文 | English | 日本語 |
| --- | --- | --- | --- |
| プロジェクト概要 | [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) |
| USB スキャン | [简体中文](usb/README.md) | [English](usb/README.en.md) | [日本語](usb/README.ja.md) |
| USB Python API | [简体中文](usb/doc/PYTHON_API.md) | [English](usb/doc/PYTHON_API.en.md) | [日本語](usb/doc/PYTHON_API.ja.md) |
| ドライバーとデバイス権限 | [简体中文](usb/driver/README.md) | [English](usb/driver/README.en.md) | [日本語](usb/driver/README.ja.md) |
| Windows ドライバー設定 | [简体中文](usb/driver/WINDOWS.md) | [English](usb/driver/WINDOWS.en.md) | [日本語](usb/driver/WINDOWS.ja.md) |
| Wi-Fi スキャン | [简体中文](wifi/README.md) | [English](wifi/README.en.md) | [日本語](wifi/README.ja.md) |
| Wi-Fi 設定 | [简体中文](wifi/doc/CONFIGURATION.md) | [English](wifi/doc/CONFIGURATION.en.md) | [日本語](wifi/doc/CONFIGURATION.ja.md) |
| 実行と配布 | [简体中文](wifi/doc/RUNNING.md) | [English](wifi/doc/RUNNING.en.md) | [日本語](wifi/doc/RUNNING.ja.md) |
| 連続スキャン | [简体中文](wifi/doc/INTERACTIVE.md) | [English](wifi/doc/INTERACTIVE.en.md) | [日本語](wifi/doc/INTERACTIVE.ja.md) |
| Wi-Fi Python API | [简体中文](wifi/doc/API.md) | [English](wifi/doc/API.en.md) | [日本語](wifi/doc/API.ja.md) |
| Wi-Fi 設定ツール | [简体中文](wifi-setup/README.md) | [English](wifi-setup/README.en.md) | [日本語](wifi-setup/README.ja.md) |
| 設定関数・CLI リファレンス | [简体中文](wifi-setup/doc/FUNCTIONS.md) | [English](wifi-setup/doc/FUNCTIONS.en.md) | [日本語](wifi-setup/doc/FUNCTIONS.ja.md) |
