# ScanSnap iX100/iX110 USB スキャン

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

USB 経由で片面のカラー・グレースケール・白黒 BMP を保存する独立した Python ドライバーです。単一ページスキャンと、用紙を挿入すると自動でスキャンする連続ジョブに対応し、公式のユーザーモード DLL は読み込みません。

以下のコマンドはすべて `ix100/usb/` から実行します。Python 3.11 以降が必要です。

## インストール

```powershell
python -m pip install -r requirements.txt
```

| 環境 | 準備 |
| --- | --- |
| Windows、公式 USB ドライバー導入済み | `--backend usbscan` を使用し、実行前に ScanSnap Home を終了 |
| Windows、WinUSB に割り当て済み | `--backend libusb` を使用 |
| Windows、公式ドライバー未導入 | [Windows ドライバー設定](driver/WINDOWS.ja.md)に従って Zadig で WinUSB を設定 |
| Linux/macOS | システムの libusb ランタイムを導入。Linux ではデバイス権限も設定 |

Windows での導入・切り替え・復元は [Windows ドライバー設定](driver/WINDOWS.ja.md)、Linux の権限は [driver/README.ja.md](driver/README.ja.md) を参照してください。既定の `auto` は libusb を優先し、Windows でオープンに失敗した場合のみ usbscan にフォールバックします。スキャン中にバックエンドは切り替えません。

## スキャン

スキャナーを接続して用紙を挿入し、1 ページをスキャンします：

```powershell
python src/scan_direct.py
```

連続スキャンは起動直後から用紙を待ち、挿入するたびにスキャンして個別の BMP を保存します：

```powershell
python src/scan_interactive.py
```

Enter を押すと現在のページの読み取り・保存後に終了します。Ctrl-C は現在のページを中断してジョブを終了します。2 つのスキャンプログラムを同時に実行しないでください。

既定の保存先はこのディレクトリの `output/` で、存在しなければ自動作成します。単一ページの既定名は `ix100-%Y%m%d-%H%M%S-%f.bmp` で、デバイスにアクセスする前にローカル時刻の `strftime` で展開します。保存先も指定できます：

```powershell
python src/scan_direct.py output/page.bmp
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
python src/scan_interactive.py --output-dir output
```

`scan_direct.py` はディレクトリを含む出力パス全体の時刻書式を展開します。`%f` は 6 桁のマイクロ秒、`%%` は文字としてのパーセント記号です。指定した相対パスは現在の作業ディレクトリを基準とします。対話型エントリーポイントはページごとのタイムスタンプ命名を使用し、`--output-dir` の時刻書式は展開しません。

## オプション

両スキャンエントリーポイントで次のオプションを共用します：

| オプション | 用途と既定値 |
| --- | --- |
| `--dpi 300` | スキャン解像度。既定は 300 DPI |
| `--color-mode color` | `color`：カラー、`gray`：グレースケール、`mono`：白黒。既定はカラー |
| `--backend auto` | `auto`、`usbscan`、`libusb` |
| `--overscan` / `--no-overscan` | スキャン幅。有効時 10368、無効時 10208。既定は有効 |

DPI は整数を受け付けます。指定値を機器が受け付けるかは実際の応答によります。ウィンドウの幅と高さの単位は 1/1200 インチです。高さはプログラムが選択し、600 DPI では 17828、それ以外では 42307 に固定します。2 種類の幅はそのまま送信します。パラメーターはバッチ初期化時に一度設定し、連続スキャンの後続ページでも共用します。

出力は機器が返したストリーム幅を保持します。横方向の切り取り、傾き補正、回転、OCR、PDF 出力は行いません。画像が不完全ならエラーにします。BMP 保存時だけ形式に従って行をパディングし、スキャン幅は変更しません。画像サイズは機器が返したピクセル幅・高さを使用します。BMP の DPI は未指定で、横・縦のピクセル/メートルフィールドはともに 0 です。

プログラムの強制終了後に残ったジョブを終了する場合：

```powershell
python src/scan_direct.py --stop --backend usbscan
```

このコマンドはデバイスにアクセスします。別のドライバーでは対応するバックエンドを選択してください。ヘルプの表示はデバイスにアクセスしません：

```powershell
python -B src/scan_direct.py --help
python -B src/scan_interactive.py --help
```

Wi-Fi スキャンと無線設定の入口は[メイン README](../README.ja.md)を参照してください。
