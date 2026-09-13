# Python からの使用方法

[简体中文](API.md) | [English](API.en.md) | [日本語](API.ja.md)

Python 3.11 以降を使用し、`ix100/wifi/` で `python -m pip install -r requirements.txt` を実行して依存関係を導入します。`src/` をモジュール検索パスに追加するか、`src/` で Python を起動してください。

| モジュール | 役割 |
| --- | --- |
| `driver.py` | デバイスセッション、予約・保活、スキャン、最終寸法と非圧縮ピクセルの復元 |
| `app_common.py` | INI、スキャン設定の上書き、出力パス、BMP エンコード |
| `scan_direct.py` | 即座に 1 ページをスキャンする CLI 入口 |
| `scan_interactive.py` | 1 つの連続ジョブで用紙挿入時に自動スキャンし、ページごとに保存 |
| `discover.py` | 設定の読み込み、UDP 送信、検出結果の表示 |
| `generate_manager_id.py` | Manager ID のオフライン生成 |

`app_common.load_config_file()` はローカル設定を読み、`generate_manager_id.py` は Manager ID を生成します。どちらも機器にアクセスしません。以下の `DriverSession` とスキャン呼び出しは機器に接続してスキャンします。設定ファイルと出力パスは現在の作業ディレクトリを基準とします：

```python
from app_common import load_config_file, save_scan_image
from driver import ColorMode, DriverSession

config = load_config_file("config/ix100.local.ini")
config.dpi = 300
config.color_mode = ColorMode.COLOR
config.overscan = True
with DriverSession(config) as driver:
    driver.reserve()
    result = driver.scan()
    save_scan_image("output/ix100_scan.bmp", result)
```

セッションのコンテキストが機器を解放します。`DriverSession.scan()` は単一ページジョブを作成し、1 ページ後に終了します。`driver.batch(continuous=True)` は連続ジョブを提供します。そのコンテキストマネージャーでジョブを開始・終了し、`wait_for_paper(should_stop)` で用紙を待ち、`scan_page()` で 1 ページをスキャンして結果を返します。連続入口の使い方は [INTERACTIVE.ja.md](INTERACTIVE.ja.md) を参照してください。

ID 生成は `from generate_manager_id import generate_manager_id`、機器検出は `from discover import discover_devices` でインポートします。`discover_devices(config)` は UDP を送信して機器にアクセスします。

`Config.color_mode` は `ColorMode.COLOR`、`ColorMode.GRAY`、`ColorMode.MONO` を使い、既定は `COLOR` です。`Config.overscan` は既定で `True` です。設定はデバイスセッション作成前に確定します。INI の省略可能項目は既定値を使います。固定のセクション名・キー名・必須項目は [CONFIGURATION.ja.md](CONFIGURATION.ja.md) を参照してください。

`ScanResult.color_mode` は画像モードを記録します。`ScanResult.image` は上から下の行順のピクセルのみを保持し、カラーは 24 ビット BGR、グレースケールは 8 ビット単一チャネル、白黒は 1 ビットのパック形式です。想定行バイト数は `(width * bits_per_pixel + 7) // 8` で、画像長は行バイト数と最終高さの積と一致する必要があります。非圧縮グレースケール・白黒の応答形式と極性は実機未確認です。

保存処理はモードに応じた 24・8・1 ビット BMP を書き、必要なパレットと行パディングを追加します。色反転・切り取りは行わず、指定パスをそのまま使用します。`output/ix100_scan.bmp` のように正スラッシュと `.bmp` ファイル名を使用してください。`save_scan_image()` は時刻書式を展開しません。必要なら `datetime.now().strftime()` でパスを生成します。`scan_direct.py` は機器へのアクセス前に出力引数または INI の `[scan] output` を展開します。

モジュールのインポートはネットワークにアクセスしませんが、デバイスセッションの構築ではネットワークインターフェイスを選択し転送を初期化します。プロトコル解析・過去の検証資料は実行時依存関係ではありません。
