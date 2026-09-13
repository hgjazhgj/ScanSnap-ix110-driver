# Python API

[简体中文](PYTHON_API.md) | [English](PYTHON_API.en.md) | [日本語](PYTHON_API.ja.md)

[使用ドキュメント](../README.ja.md)

`ix100/usb/src/` を `PYTHONPATH` に追加するか、`src/` で Python を起動してください：

```python
from pathlib import Path

from bmp_output import save_bmp
from scanner_driver import ColorMode, ScanSettings, open_scan_batch

settings = ScanSettings(
    dpi=300, color_mode=ColorMode.GRAY,
    overscan=True,
)
with open_scan_batch("auto", settings, reporter=print) as batch:
    page = batch.scan_page()
save_bmp(Path("output/page.bmp"), page)
```

`save_bmp()` は指定パスに保存し、時刻書式は展開しません。タイムスタンプが必要なら `datetime.now().strftime()` でパスを生成してください。`scan_direct.py` はデバイスへのアクセス前にこの処理を行います。

`ScanSettings` は既定で単一ページモードとなり、1 ページの読み取り成功後にバッチを終了します。既定値は `dpi=300`、`overscan=True` です。コンストラクターに幅や高さは指定できません。幅は overscan 有効時 10368、無効時 10208、高さは 600 DPI 時 17828、それ以外は 42307 です。単位はともに **1/1200 インチ**で、基本・拡張フィールドに同じ寸法を使用します。既定の 300 DPI・カラー・overscan 有効では 10368×42307 単位、ピクセル上限は 2592×10577 です。

各バッチの初期化時に page3C と SET WINDOW を一度送信し、後続ページでは同じ設定を使います。複数ページでは `mode=ScanMode.CONTINUOUS` を設定します（`scanner_driver` から `ScanMode` をインポート）。各ページで先に `batch.wait_for_paper(should_stop)` を呼び、`True` が返ったら `scan_page()` を呼びます。`should_stop` は真偽値を返すコールバックです。`with` を抜けるとバッチの終了処理と転送リソースの解放を行います。

`window_width_units` と `window_height_units` は実際に送信する寸法です。`maximum_width_pixels` と `maximum_lines` は READ80 の応答の上限確認に使用します。行数上限は `ceil(window_height_units * dpi / 1200)` です。2 種類の幅はそのまま送信し、読み取りストライドは機器が返した実ストリーム幅から `ceil(実ストリーム幅 * ビット深度 / 8)` で計算します。白黒の行末の余りが 8 ビット未満でも 1 バイトを使用します。寸法と画像の完全性のチェックは維持します。BMP 保存時は実際の行長に基づき 4 バイト境界までゼロを補い、画像幅は変えません。この寸法選択はホスト側の方針であり、公式の全用紙サイズ計算を再現するものではありません。

`color_mode` には `ColorMode.COLOR`、`ColorMode.GRAY`、`ColorMode.MONO` を指定できます。`ScannedPage` は `pixels`、`width`、`height`、`color_mode` を持ち、DPI は持ちません。`pixels` は対応するモードのピクセルデータ、幅と高さは機器の応答値、`color_mode` はビット深度を示します。`save_bmp()` は横・縦のピクセル/メートルを 0 とし、物理解像度を未指定にします。スキャン要求の DPI は引き続き `ScanSettings.dpi` で制御します。

転送モジュールは `src/transport_libusb.py` と `src/transport_usbscan.py`、共通のフレーム処理は `src/transport_protocol.py` です。Windows のポート検出は `src/usbscan_device.py` が提供します。
