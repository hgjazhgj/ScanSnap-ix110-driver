# Python からの使用方法

[简体中文](API.md) | [English](API.en.md) | [日本語](API.ja.md)

Python 3.11 以降を使用し、`ix100/wifi/` で `python -m pip install -r requirements.txt` を実行して依存関係を導入します。`src/` をモジュール検索パスに追加するか、`src/` で Python を起動してください。

| モジュール | 役割 |
| --- | --- |
| `driver.py` | デバイスセッション、予約・保活、スキャン、最終寸法と非圧縮ピクセルの復元 |
| `app_common.py` | INI の読み込み、既定の設定パス、既存公開インターフェイスの互換エクスポート |
| `cli_common.py` | スキャン引数と設定の上書き、`report` / `report_saved` によるコンソール出力、`end_requested` による対話終了の確認 |
| `bmp_output.py` | BMP エンコードと保存 |
| `scan_direct.py` | 即座に 1 ページをスキャンする CLI 入口 |
| `scan_interactive.py` | 1 つの連続ジョブで用紙挿入時に自動スキャンし、ページごとに保存 |
| `discover.py` | 設定の読み込み、UDP 送信、検出結果の表示 |
| `generate_manager_id.py` | Manager ID のオフライン生成 |

`app_common.load_config_file()` はローカル設定を読み、`generate_manager_id.py` は Manager ID を生成します。どちらも機器にアクセスしません。以下の `DriverSession` とスキャン呼び出しは機器に接続してスキャンします。設定ファイルと出力パスは現在の作業ディレクトリを基準とします：

```python
from pathlib import Path

from app_common import load_config_file
from bmp_output import save_bmp
from driver import ColorMode, DriverSession

config = load_config_file(Path("config/ix100.local.ini"))
config.dpi = 300
config.color_mode = ColorMode.COLOR
config.overscan = True
with DriverSession(config) as driver:
    driver.reserve()
    result = driver.scan()
    save_bmp(Path("output/ix100_scan.bmp"), result)
```

`DriverSession(config, reporter=callback)` では、単一の `str` 引数を受け取る進捗コールバックを指定できます。`reporter` を省略すると、従来どおりコンソールに出力します。`save_bmp(path: Path, page: ScanResult) -> None` は画像の保存のみを行い、保存ログを出力しません。CLI 入口は `cli_common.report_saved()` で保存結果を表示します。

セッションのコンテキストが機器を解放します。`DriverSession.scan()` は単一ページジョブを作成し、1 ページ後に終了します。`driver.batch(continuous=True)` は連続ジョブを提供します。そのコンテキストマネージャーでジョブを開始・終了し、`wait_for_paper(should_stop)` で用紙を待ち、`scan_page()` で 1 ページをスキャンして結果を返します。連続入口の使い方は [INTERACTIVE.ja.md](INTERACTIVE.ja.md) を参照してください。

ID 生成は `from generate_manager_id import generate_manager_id`、機器検出は `from discover import discover_devices` でインポートします。`discover_devices(config)` は UDP を送信して機器にアクセスします。

`Config.color_mode` は `ColorMode.COLOR`、`ColorMode.GRAY`、`ColorMode.MONO` を使い、既定は `COLOR` です。`Config.overscan` は既定で `True` です。設定はデバイスセッション作成前に確定します。INI の省略可能項目は既定値を使います。固定のセクション名・キー名・必須項目は [CONFIGURATION.ja.md](CONFIGURATION.ja.md) を参照してください。

`ScanResult.color_mode` は画像モードを記録します。`ScanResult.image` は上から下の行順のピクセルのみを保持し、カラーは 24 ビット BGR、グレースケールは 8 ビット単一チャネル、白黒は 1 ビットのパック形式です。想定行バイト数は `(width * bits_per_pixel + 7) // 8` で、画像長は行バイト数と最終高さの積と一致する必要があります。非圧縮グレースケール・白黒の応答形式と極性は実機未確認です。

保存処理はモードに応じた 24・8・1 ビット BMP を書き、必要なパレットと行パディングを追加します。色反転・切り取りは行わず、指定パスをそのまま使用します。画像寸法、ピクセル長、非ゼロの解像度、BMP 形式の上限の検査を維持し、BMP 解像度には機器が返す実際の水平・垂直 DPI を引き続き使用します。まず `.part` 一時ファイルに書き込み、`flush()` と `os.fsync()` の後に `os.replace()` で保存先を置き換えます。`output/ix100_scan.bmp` のように正スラッシュと `.bmp` ファイル名を使用してください。`save_bmp()` は時刻書式を展開しません。必要なら `datetime.now().strftime()` でパスを生成します。`scan_direct.py` は機器へのアクセス前に出力引数または INI の `[scan] output` を展開します。

既存のインポートも使用できます。`app_common.add_scan_options` と `app_common.apply_scan_options` は `cli_common` の実装を互換用に再エクスポートし、`app_common.default_config_path()` は引き続き既定の設定パスを返します。`app_common.save_scan_image(output, result) -> Path` は保存を `save_bmp()` に委譲し、従来の保存ログを出力して保存先パスを返します。この関数も時刻書式を展開しません。

モジュールのインポートはネットワークにアクセスしませんが、デバイスセッションの構築ではネットワークインターフェイスを選択し転送を初期化します。プロトコル解析・過去の検証資料は実行時依存関係ではありません。
