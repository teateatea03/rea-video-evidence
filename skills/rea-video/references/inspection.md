# 補證據、字幕與長片

適用於台詞搜尋、長片摘要、短窗動作／小字檢查或引用驗證。先選需要的模式，不必每次執行全部。

## 台詞與字幕

有可信來源的 UTF-8 SRT/VTT 時先匯入：
~~~powershell
rea-video transcript "./analysis-01" --input "./captions.srt" --origin supplied_subtitles --language zh
rea-video evidence "./analysis-01" --query "台詞" --limit 4
~~~
需新版報告的全檔 SHA-256；不覆寫既有 transcript.json。spoken 與 screen_text 分開，字幕／ASR 也可能是翻譯或誤辨，不能當已聽音或畫面已發生。重要人名與數字需核對原音。

沒有字幕但需要語音內容時，可用本地 faster-whisper 模型：
~~~powershell
rea-video asr "./reference.mp4" --model "/absolute/local/whisper-model" -o "./analysis-01/transcript.json" --language zh
~~~
模型資料夾須已有 model.bin、config.json、tokenizer.json（避免後端補下載 tokenizer）；只用本地 CPU int8，不下載模型、不呼叫雲端。缺少 runtime／模型／音軌就說明缺口。未提供 --language 可自動辨識 ASR 語言；這不代表報告／OCR 已新增該語言。

## 依問題補幀

~~~powershell
rea-video inspect "./reference.mp4" -o "./focus-01" --start 3.5 --end 8 --max-frames 12 --width 1280
rea-video inspect "./reference.mp4" -o "./text-01" --start 3.5 --end 5 --max-frames 4 --crop 0 0.6 1 0.4
~~~
讀 manifest.json 的實際 decoded PTS、失敗、max_sample_gap_seconds，再實際開圖片。最多 64 張，寬 160–1920；crop 是顯示方向的 x/y/w/h 比例。每次用新目錄。先總覽，再對動作、小字、矛盾或使用者關注區間加密；不得將抽樣宣稱連續觀看。

## 長片

~~~powershell
rea-video chapters "./long.mp4" -o "./long-index" --chunk-seconds 600 --overlap 2 --max-frames 16
# 中斷後：保持相同來源與參數
rea-video chapters "./long.mp4" -o "./long-index" --chunk-seconds 600 --overlap 2 --max-frames 16 --resume
~~~
這是分章證據索引，不輸出逐鏡製作分類，也不自動派代理。每章 checkpoint 原子寫入，續跑檢查來源／設定／版本及已完成圖片雜湊。損壞時先調查；不刪舊產物或悄悄換來源重跑。交界有重疊，合併依章節自己的 [start,end) 範圍去重，保持原片時間。

## 結論與引用

重要說法標記 observed／spoken／inferred；支援狀態 supported／conflicted／not_found，保留幀或字幕 segment ID。inferred 附不確定性。可用：
~~~powershell
rea-video validate-claims "./claims.json" --manifest "./focus-01/manifest.json"
~~~
spoken 引用另加 --transcript。格式與完整指令見 [公開工作流文件](https://github.com/teateatea03/rea-video-evidence/blob/main/docs/workflows.md)。
驗證器只檢查來源、時間、引用及影像位元組，不證明說法真實或已實際看／聽。
