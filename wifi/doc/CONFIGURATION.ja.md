# Wi-Fi 設定

[简体中文](CONFIGURATION.md) | [English](CONFIGURATION.en.md) | [日本語](CONFIGURATION.ja.md)

以下のパスとコマンドは `ix100/wifi/` を作業ディレクトリとします。`config/ix100.example.ini` を `config/ix100.local.ini` にコピーし、次の固定セクション名とキー名で設定します。必須なのはスキャナー IP、Manager ID、および接続パスワード有効時のパスワードのみです。他は既定値を使います。

```powershell
python src/generate_manager_id.py
```

独立スクリプトで Manager ID をランダム生成し、`[identity] wifi_manager_id` にコピーして継続使用します。生成器はオフラインで動作し、端末に ID を表示するだけで設定ファイルは変更しません。

| 設定項目 | 意味 |
| --- | --- |
| `[identity] wifi_manager_id` | 必須。8 バイトのホスト ID を 16 桁の 16 進文字列で記入。全ゼロ不可。生成後は継続使用 |
| `[scanner] ip` | 必須。現在のスキャナー IPv4 アドレス。ルーターのリース表または `discover.py` の結果で取得 |
| `[scanner] control_port` | 任意。既定 53218。スキャン制御用 TCP ポート |
| `[scanner] app_port` | 任意。既定 53219。予約・機器情報・解放用 TCP ポート |
| `[scanner] discovery_port` | 任意。既定 52217。UDP 検出・保活用ポート |
| `[credential] password_required` | 任意。既定 `1`。接続パスワードを使う場合 `1`、不要なら `0` |
| `[credential] password` | 有効時は必須。背面ラベルの平文パスワード。空白を含まない印字可能 ASCII 文字 1～16 文字 |
| `[network] timeout_seconds` | ネットワーク・スキャンのタイムアウト。既定 30 秒、範囲 5～300 秒 |
| `[scan] dpi` | 整数のスキャン解像度。既定 300。受け付けても機器の対応・検証済みを意味しない |
| `[scan] color_mode` | `color`、`gray`、`mono`。既定 `color`。それぞれ 24・8・1 ビット BMP |
| `[scan] overscan` | `1` で端部拡張スキャンを有効化、`0` で無効化。既定 `1` |
| `[scan] max_image_mb` | 1 ページの受信メモリ上限。既定 256 MiB、範囲 1～1024 MiB |
| `[scan] output` | 単一ページの既定 BMP パス。既定 `output/ix100_scan.bmp`。`strftime` テンプレート対応。正スラッシュと `.bmp` ファイル名を使用 |

ホスト IP、送信インターフェイス、ホスト MAC、ブロードキャストアドレスは自動選択し、記入不要です。公式アプリの設定やレジストリは読みません。

`scan_direct.py` と `scan_interactive.py` は `--dpi INTEGER`、`--color-mode color|gray|mono`、`--overscan` / `--no-overscan` で INI 設定を上書きでき、ファイルは変更しません。単一ページの入口は出力パスを直接受け付けます。例：`python src/scan_direct.py output/ix100_scan.bmp`。

検出入口も同じ設定を読みます。`python src/discover.py --config config/ix100.local.ini` は UDP を送信し機器にアクセスします。

ウィンドウ寸法はホストが選択し、単位は 1/1200 インチです。高さは 600 DPI で 17828、それ以外で 42307、幅は overscan 有効時 10368、無効時 10208 です。これは現在のホスト側の方針で、公式の自動用紙サイズ規則の完全再現ではありません。高 DPI は受信メモリを多く使い、`max_image_mb` でページごとの上限を設定できます。

`--config` を省略するとリリース内の `ix100/wifi/config/ix100.local.ini` を固定で使用します。実際の設定は別の場所に置き、`--config FILE` で指定できます。認証情報を配布ディレクトリに置く必要はありません。

`scan_direct.py` の出力位置引数は `[scan] output` より優先されます。選択後、機器へのアクセス前に、ローカル時刻の `strftime` でディレクトリを含むパス全体を展開します：

```ini
[scan]
output=output/%Y%m%d/scan-%H%M%S-%f.bmp
```

`%f` は 6 桁のマイクロ秒、`%%` は文字としてのパーセント記号です。INI には上記の形式をそのまま記入します。相対出力パスは現在の作業ディレクトリが基準で、ファイル名は `.bmp` にします。対話型入口はこの設定の親ディレクトリのみを使い、時刻書式は展開せず、ページごとの名前を生成します。設定形式は本ページと `config/ix100.example.ini` に従ってください。

現在は片面の非圧縮画像を要求し、保存時の切り取りオプションはありません。グレースケール・白黒の応答形式と極性は実機未確認です。ローカル INI は平文パスワードを含み、無視ルールで除外されています。配布・共有にはテンプレートのみを使用します。
