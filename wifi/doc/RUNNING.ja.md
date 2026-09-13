# 実行と配布

[简体中文](RUNNING.md) | [English](RUNNING.en.md) | [日本語](RUNNING.ja.md)

Windows/Linux で Python 3.11 以降を使用します。外部依存はネットワークインターフェイス・MAC・ブロードキャストアドレスの列挙に使う `psutil` のみです。BMP エンコードは標準ライブラリを使います。

`ix100/wifi/` から実行します：

```powershell
python -m pip install -r requirements.txt
```

実際の実行に使う Python に依存関係を導入してください。初期設定は [CONFIGURATION.ja.md](CONFIGURATION.ja.md) を参照してください。

| コマンド | 動作 |
| --- | --- |
| `python src/scan_direct.py --help` | オフラインで引数を表示 |
| `python src/scan_interactive.py --help` | オフラインで連続スキャンの引数を表示 |
| `python src/generate_manager_id.py` | オフラインでホスト ID を生成。ファイルには書き込まない |
| `python src/discover.py --config config/ix100.local.ini` | UDP を送信し検出結果を表示 |
| `python src/scan_direct.py output/ix100_scan.bmp` | 即座に 1 ページをスキャンして BMP を保存 |
| `python src/scan_interactive.py --output-dir output` | 用紙挿入で自動スキャン。Enter で連続ジョブ終了 |

デバイスコマンドは電源が入り、ネットワーク接続が可能で、設定を記入してから実行します。`discover.py` 成功は UDP 到達性のみを示し、スリープ中の機器では TCP セッションを確立できない場合があります。先に機器を起こしてからスキャンしてください。

予約が `status=-4 / 0xFFFFFFFC` を返す場合、他のクライアントが使用中です。ScanSnap Home、スマートフォン、他のプログラムの接続を終了してから再実行します。この段階ではスキャン設定は未送信で、給紙も開始していません。

スキャン・検出入口は `--config FILE` を指定できます。省略時はリリース内の `ix100/wifi/config/ix100.local.ini` を固定で使用し、別の場所は明示指定します。`scan_direct.py` は 1 ページだけスキャンします。出力位置引数は INI の `[scan] output` より優先し、既定は `output/ix100_scan.bmp` です。機器へのアクセス前に、ローカル時刻の `strftime` でディレクトリを含むパス全体を展開します。相対パスは現在の作業ディレクトリが基準です。正スラッシュと `.bmp` ファイル名を使用します：

```powershell
python src/scan_direct.py 'output/%Y%m%d/scan-%H%M%S-%f.bmp'
```

`%f` は 6 桁のマイクロ秒、`%%` は文字としてのパーセント記号です。INI の出力も同じテンプレートに対応します。対話型のディレクトリは時刻展開しません。ページごとの命名は [INTERACTIVE.ja.md](INTERACTIVE.ja.md) を参照してください。

`scan_direct.py` と `scan_interactive.py` は `--dpi INTEGER`、`--color-mode color|gray|mono`、`--overscan` / `--no-overscan` を受け付けます。明示値は INI より優先し、省略時は設定を維持します。設定の既定は 300 DPI、カラー、overscan 有効です。`discover.py` は同じ設定を読みますが、スキャン用引数は受け付けません。

カラー・グレースケール・白黒はそれぞれ 24・8・1 ビット BMP に保存します。非圧縮グレースケール・白黒の応答形式と極性は実機未確認です。

スキャン成功には、最終寸法と完全なピクセルの取得、BMP 保存、ジョブ終了、機器解放が必要です。失敗時は端末にエラーを表示し、非ゼロの終了コードを返します。給紙や設定送信だけの成功を画像保存成功と判断しないでください。連続スキャンの終了方法は [INTERACTIVE.ja.md](INTERACTIVE.ja.md) を参照してください。
