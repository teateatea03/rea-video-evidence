# REA Video Evidence

[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

動画のショット、画面内テキスト、音声信号、制作方法の仮説を整理する CLI とエージェント用スキルです。必要な時間帯の証拠を取り出し、レポート全体をエージェントへ渡す負担を減らします。

本プロジェクトは [JuneYaooo/rea-video](https://github.com/JuneYaooo/rea-video) の commit `d2fb1e06373a7ecc9379545591ac3904f154b8c9` を基にした、独立管理の派生版です。Apache-2.0 ライセンスと原作者の表示を維持しています。変更範囲は [UPSTREAM.md](UPSTREAM.md) を参照してください。

## この版の追加機能

- **必要な証拠だけを取得**：時間範囲や文字列で既存の分析を絞り込み、時刻と出典を含む JSON を返します。
- **レビュー待ち一覧**：エージェントのレビューが未適用のショットを、不確実なものから優先してページ単位で表示します。
- **状態を明確に区別**：OCR、ツールの証拠、エージェントのレビュー、外部 VLM、画像の欠落、未記録の聴取確認を分けます。
- **Windows の Unicode パス対応**：日本語などを含むパスでも、ストーリーボードや要素・ステッカー画像を保存できます。
- **移植可能なスキル**：Codex、Claude Code などへ、既存スキルを上書きせずに導入できます。

ショット検出、制作分類、OCR、レポート、再制作計画は上流プロジェクトを継承しています。分類スコアは仮説であり、制作元の証明ではありません。

## インストール

Python 3.10 以上と、PATH 上の FFmpeg／FFprobe が必要です。上流版と `rea_video` モジュールおよび `rea-video` コマンドを共有するため、専用環境を使ってください。

```sh
git clone https://github.com/teateatea03/rea-video-evidence.git
cd rea-video-evidence
python -m venv .venv
```

macOS／Linux は `source .venv/bin/activate`、Windows PowerShell は `.venv\Scripts\Activate.ps1` で有効化します。実行ポリシーにより有効化できない場合は、環境内の Python／CLI をフルパスで呼び出してください。

```sh
python -m pip install -e ".[dev]"
rea-video --help
python scripts/install_skill.py --agent codex
```

配布パッケージ名は `rea-video-evidence`、CLI 名は `rea-video` です。スキル導入スクリプトはスキルだけをコピーし、PATH や CLI を変更しません。既存の保存先は上書きしません。`--agent claude`、`--agent agents`、または `--dest` も指定できます。

OCR は任意です。RapidOCR が要求する `opencv-python` は headless OpenCV とファイルが競合するため、専用環境内で次を実行します。

```sh
python -m pip install -e ".[ocr]"
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
```

この上流の回避策では、headless 版が `cv2` を提供していても、`pip check` に RapidOCR の依存メタデータ警告が残ります。実際の OCR 動作を確認し、依存チェックが完全に成功したとは扱わないでください。

## 使い方

```sh
rea-video decompose "reference.mp4" -o "out/reference-01" --no-vlm --lang en
rea-video summary "out/reference-01/breakdown.json"
rea-video evidence "out/reference-01" --start 3.5 --end 8 --limit 4
rea-video evidence "out/reference-01" --query "商品" --limit 4
rea-video evidence "out/reference-01" --pending --limit 4
```

`evidence` は読み取り専用です。再デコード、モデル呼び出し、認証情報の読み込み、永続メモリへの書き込みは行いません。検索対象は既存の OCR・ツール・レビューの文字列であり、音声認識や未観察の映像内容の意味検索ではありません。結果がゼロでも、動画中に存在しないとは限りません。

時間範囲は `[start,end)` です。`pagination.next_offset` を `--offset` に指定すると続きを取得できます。画像を見られるエージェントは次を使います。

```sh
rea-video review "out/reference-01"
# 実際に画像を確認し、確認済みショットだけ review_answers.json に記入します。
rea-video apply-review "out/reference-01" --by your-agent
```

HTML／Markdown レポート、JSON、ショット画像、利用可能な字幕・音声ファイルを出力します。初回の音源分離では、約 67 MB の UVR ONNX モデルをローカルキャッシュへダウンロードします。外部 VLM は任意で、別途設定が必要となり、料金が発生する場合があります。認証情報はリポジトリに保存しないでください。

## 制約と検証

ツールのレポート生成言語は `zh` と `en` です。4 言語の README は、日本語・韓国語レポートのネイティブ対応を意味しません。エージェントの返答は利用者の言語に合わせられます。

フレーム周期だけで AI 生成とは断定できません。OCR は音声の文字起こしではなく、画像ファイルの存在は目視確認の証明でもありません。デコード成功や音声信号は、聞き取りやすさや音楽の出典を保証しません。適用済みレビューはサンプルフレームの記録であり、全編視聴を意味しません。新たな分類精度は主張していません。

```sh
python -m pytest -q
```

テストは生成した素材と分離されたメモリを使用します。参考動画、利用者のレポート、モデル重み、認証情報、個別端末の保守ログは配布しません。

## リンクとクレジット

- [GitHub](https://github.com/teateatea03/rea-video-evidence)／[GitLab.com](https://gitlab.com/angeltea01/rea-video-evidence)
- [証拠データの仕様](docs/evidence.md)／[エージェント用スキル](skills/rea-video/SKILL.md)
- [変更履歴](CHANGELOG.md)／[貢献方法](CONTRIBUTING.md)
- [上流と参考資料](UPSTREAM.md)／[ライセンス](LICENSE)／[著作権表示](NOTICE)

所有者は別途ローカル GitLab ミラーを管理できます。利用できる範囲は所有者のネットワークとアクセス方針によります。
