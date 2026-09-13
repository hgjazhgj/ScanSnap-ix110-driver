# ScanSnap iX100/iX110 Wi-Fi ドライバー

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

Windows/Linux 対応の独立した Python ドライバーで、ScanSnap Home や公式 DLL は不要です。Wi-Fi 経由で機器を検出・予約・制御し、片面の非圧縮カラー・グレースケール・白黒画像を要求して、それぞれ 24・8・1 ビット BMP に保存します。

Python 3.11 以降を使用します。以下はすべてこのディレクトリ `ix100/wifi/` から実行します：

```powershell
python -m pip install -r requirements.txt
Copy-Item config/ix100.example.ini config/ix100.local.ini
python src/generate_manager_id.py
```

`config/ix100.local.ini` を編集し、`[scanner] ip` と `[identity] wifi_manager_id` を記入します。`[credential] password_required` は既定で有効なので、機器背面ラベルの接続パスワードを `[credential] password` に記入します。パスワード不要の機器では `0` にします。他は既定値を使用できます。ID 生成スクリプトはオフラインで動作し、設定ファイルは変更しません。

機器を検出する場合は独立した入口を使用します。このコマンドは UDP を送信し、機器にアクセスします：

```powershell
python src/discover.py --config config/ix100.local.ini
```

用紙を挿入して 1 ページをスキャンします：

```powershell
python src/scan_direct.py output/ix100_scan.bmp
```

既定は 300 DPI、カラー、overscan 有効です。コマンドラインから INI の設定を上書きできます：

```powershell
python src/scan_direct.py output/ix100_scan.bmp --dpi 300 --color-mode gray --no-overscan
```

`--color-mode` は `color|gray|mono` を受け付けます。`--overscan` は端部の拡張スキャンを有効に、`--no-overscan` は無効にします。非圧縮グレースケール・白黒の応答形式と極性は実機未確認です。引数を受け付けても、そのモードが検証済みとは限りません。

用紙を挿入すると自動スキャンし、Enter で連続ジョブを終了します：

```powershell
python src/scan_interactive.py --output-dir output
```

| パス | 用途 |
| --- | --- |
| `src/` | ドライバー、共通設定・画像保存、スキャンと独立ツールの入口 |
| `requirements.txt` | Python 依存関係 |
| `config/ix100.example.ini` | 配布可能な設定テンプレート |
| [doc/CONFIGURATION.ja.md](doc/CONFIGURATION.ja.md) | 固定 INI 形式、必須項目、既定値 |
| [doc/RUNNING.ja.md](doc/RUNNING.ja.md) | 導入、全コマンド、配布 |
| [doc/INTERACTIVE.ja.md](doc/INTERACTIVE.ja.md) | 連続スキャン、命名、終了 |
| [doc/API.ja.md](doc/API.ja.md) | Python からの使用方法 |

`--config` を省略すると、このディレクトリの `config/ix100.local.ini` を固定で使用します。他の場所は `--config FILE` で指定します。`scan_direct.py` の出力引数は INI の `[scan] output` より優先され、既定は `output/ix100_scan.bmp` です。機器にアクセスする前にローカル時刻の `strftime` で出力パス全体を展開します。相対パスは現在の作業ディレクトリが基準です。正スラッシュと `.bmp` ファイル名を使用します：

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` は 6 桁のマイクロ秒、`%%` は文字としてのパーセント記号です。INI の `[scan] output` も同じ時刻テンプレートに対応します。対話型のディレクトリは展開せず、ファイル名はページごとに生成します。色反転・切り取り・非可逆圧縮は行いません。

ローカルの `ix100.local.ini` には専用 ID と平文パスワードが含まれるため、汎用パッケージには配布しません。リリースには設定テンプレートのみ含めます。
