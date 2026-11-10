# REA Video Evidence

[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

提供 CLI 與 Agent 技能，用證據拆解影片的分鏡、畫面文字、聲音訊號與製作方式，再按問題取回相關片段，減少交給模型的報告資料量。

本專案獨立維護，衍生自 [JuneYaooo/rea-video](https://github.com/JuneYaooo/rea-video)，基準 commit 為 `d2fb1e06373a7ecc9379545591ac3904f154b8c9`，保留 Apache-2.0 授權與原作者署名。修改範圍見 [UPSTREAM.md](UPSTREAM.md)。

## 這個版本增加什麼

- **局部證據查詢**：按秒數範圍或文字關鍵字，取得帶時間戳與來源的 JSON。
- **待複核佇列**：找出尚未套用 Agent 複核的鏡頭，優先列出疑問較多的部分，並支援分頁。
- **清楚呈現狀態**：分開標示 OCR、工具證據、Agent 複核、外部 VLM、缺圖與未記錄的聽音驗證。
- **Windows 中文路徑修正**：避免總分鏡圖、元素聯絡表與貼紙裁圖讀寫失敗。
- **可攜技能安裝**：支援 Codex、Claude Code 或其他 Agent 技能目錄，不覆寫既有技能。

底層切鏡、製作分類、OCR、報告與重製規劃承自上游；分類分數是推測，不是製作來源的鑑定證明。

## 0.2 新增補強

複核答案綁定來源、分鏡與圖片，拒絕錯片及無效機率；OCR 共用硬性呼叫預算並回報失敗狀態。支援 SRT/VTT 匯入及選配本地 ASR，台詞與畫面 OCR 分開查詢。新增 `doctor`、`inspect`、`chapters --resume`、`validate-claims`，提供環境診斷、按需補幀、可續跑的長片索引與引用檢查；限制同時保留的完整鏡頭影格，並移植上游英文格式修正。

[指令、相容性與限制](docs/workflows.md)：chapters 是抽樣證據索引，不是完整分類的續跑；ASR 需已有本地模型，不會自行下載。原生報告語言仍為 zh/en。

## 安裝

需要 Python 3.10+，以及 PATH 中可用的 FFmpeg／FFprobe。請使用獨立環境；本專案與上游共用 `rea_video` 模組與 `rea-video` 指令。

```sh
git clone https://github.com/teateatea03/rea-video-evidence.git
cd rea-video-evidence
python -m venv .venv
```

macOS／Linux：`source .venv/bin/activate`；Windows PowerShell：`.venv\Scripts\Activate.ps1`。若啟用腳本受阻，直接用環境內 Python／CLI 的完整路徑，不需變更系統原則。

```sh
python -m pip install -e ".[dev]"
rea-video --help
python scripts/install_skill.py --agent codex
```

Python 套件名稱為 `rea-video-evidence`，CLI 保留 `rea-video`。安裝腳本只複製技能，不修改 PATH、不安裝 CLI，目的地已存在時會拒絕覆寫。可用 `--agent claude`、`--agent agents` 或明確指定 `--dest`。

OCR 為選配。RapidOCR 會額外要求與 headless OpenCV 共用檔案的 `opencv-python`，請只在上述獨立環境內處理：

```sh
python -m pip install -e ".[ocr]"
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
```

這個上游相容方式仍會留下 `pip check` 的 RapidOCR metadata 警告；headless 提供的 `cv2` 可供實際 OCR 使用，但不能宣稱依賴檢查完全通過。

## 使用

```sh
rea-video decompose "reference.mp4" -o "out/reference-01" --no-vlm --lang zh
rea-video summary "out/reference-01/breakdown.json"
rea-video evidence "out/reference-01" --start 3.5 --end 8 --limit 4
rea-video evidence "out/reference-01" --query "商品" --limit 4
rea-video evidence "out/reference-01" --pending --limit 4
```

`evidence` 只讀取既有報告，不重新解碼、不呼叫模型、不載入憑證、不寫長期記憶。關鍵字搜尋已有 OCR／工具／複核文字及已匯入的字幕段落；查詢時不做語音辨識或畫面語意搜尋；零結果不代表片中沒有。時間採 `[start,end)`，用 `pagination.next_offset` 與 `--offset` 接續。

能看圖的 Agent 可執行：

```sh
rea-video review "out/reference-01"
# 實際開圖，只填入看過的鏡頭至 review_answers.json。
rea-video apply-review "out/reference-01" --by your-agent
```

輸出包括 HTML／Markdown 報告、JSON、分鏡與逐鏡圖片，以及可用的字幕／音軌產物。首次人聲分離會下載約 67 MB UVR ONNX 模型至本機快取。外部 VLM 可選配，需另行設定且可能計費；憑證不可放進專案。

## 限制與驗證

原生工具報告語言為 `zh`／`en`；四語說明不代表工具已原生支援日韓文報告。Agent 回覆可依使用者語言。

幀率不能單獨證明 AI；OCR 不是逐字稿；圖片存在不等於看過；音訊訊號／可解碼不證明台詞可懂度或音樂來源。已套用複核只代表抽樣畫面的記錄，不代表連續看完整片。本版本不宣稱新的分類準確率。

```sh
python -m pytest -q
```

測試使用程式生成素材與隔離記憶。發布內容不包含參考影片、使用者報告、模型權重、憑證或電腦維護紀錄。

## 專案與來源

- [GitHub](https://github.com/teateatea03/rea-video-evidence)／[GitLab.com](https://gitlab.com/angeltea01/rea-video-evidence)
- [證據查詢契約](docs/evidence.md)／[Agent 技能](skills/rea-video/SKILL.md)
- [變更紀錄](CHANGELOG.md)／[貢獻方式](CONTRIBUTING.md)
- [上游與參考來源](UPSTREAM.md)／[授權](LICENSE)／[署名](NOTICE)

擁有者另可維護本地 GitLab 鏡像；可用範圍由其網路與存取政策決定。
