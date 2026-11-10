# 按時間與文字取回證據

Modified for rea-video-evidence, 2026-11-08; see [attribution](https://github.com/teateatea03/rea-video-evidence/blob/main/UPSTREAM.md).

本機新增 `rea-video evidence`，直接讀取既有 `breakdown.json`，不解碼影片、不呼叫模型、不載入 .env／prefs，也不修改分析結果。適合「某一段怎麼做」「找畫面中的文字」「下一批要複核哪些鏡頭」，不取代看圖或聽音。

## 指令

```powershell
# 指定時段（秒）；也可傳入完整 breakdown.json 路徑
rea-video evidence "./analysis-01" --start 3.5 --end 8.0 --limit 4

# 搜尋已有的 OCR、測量證據與已並入的看圖描述
rea-video evidence "./analysis-01" --query "商品名稱" --limit 4

# 未並入 Agent 複核的鏡頭；高優先在前
rea-video evidence "./analysis-01" --pending --limit 4

# 依上一頁 pagination.next_offset 取下一頁
rea-video evidence "./analysis-01" --pending --limit 4 --offset 4
```

- 範圍採 `[start, end)`，包含與時段相交的鏡頭；保留鏡頭原始起迄時間。範圍必須介於 0 與影片總長之間，NaN／Infinity、反向範圍與不合理預算回傳 exit 2。
- `--query` 是不分大小寫的文字子字串搜尋，最多 200 字；不是正規表示式或語意搜尋，也不會即時語音辨識；匯入 transcript.json 後才額外搜尋 spoken，與 OCR 分開。畫面看得到但 OCR 未記錄的文字可能找不到，零結果不證明畫面／聲音沒有該內容。
- 預設每頁 8 鏡，`--limit` 為 1–100；每鏡最多 8 條 OCR 與有限長度的證據摘要。較完整內容仍在原報告；截短的項目會標示，不把前幾筆當全量。
- JSON 寫入檔案時使用 UTF-8。Windows PowerShell 5 的裸 `>` 會轉為 UTF-16；使用 `| Out-File -Encoding utf8 "./evidence.json"`，或由程式直接保存 CLI 的 UTF-8 stdout bytes。

## 如何使用結果

1. `coverage` 以時間範圍內所有鏡頭為分母，統計已有逐鏡 `review` 記錄與尚未複核的高優先鏡頭；不依賴可能過時的整片複核數字。套用 review 不保證實際看過，應和自己的操作紀錄一起說明。
2. `pagination.matched` 是再套用關鍵字／pending 條件的鏡頭數；`returned` 是本頁數，`next_offset` 有值時可繼續。不要混淆影片範圍、命中數與本頁覆蓋。
3. 每鏡有 `citation`（ID＋原始時間）、分類與不確定性、測量證據、Agent 複核、OCR 與圖片絕對路徑。`query_matches.origin` 指出命中來自測量、Agent、OCR 或分類，引用時保留來源。
4. 圖片狀態：`available` 只是檔案存在；`missing` 缺檔；`not_recorded` 未輸出；`outside_report` 拒絕引用報告目錄外的圖片。只檢查本頁列出的圖片，不能據此宣稱整份報告完整。實際開圖後才算視覺複核。
5. `breakdown_sha256` 綁定本次證據包的原始 JSON 快照。apply-review 後 JSON 改變，查詢須重新產生；這不是原影片的完整 SHA-256。新版來源另含完整 `sha256`；`sha256_head` 僅為舊版相容的部分檔案雜湊。
6. `vlm_status` 與 `agent_review.applied` 分開；`audio.listening_verification=not_recorded` 表示報告未記錄聽音驗證，不從有音軌／有複核推定已聽音。OCR 保持為畫面文字，不寫成已核對台詞。

需要複核時，依結果的圖片路徑實際開圖，在既有 review_answers.json 補上有看過的鏡頭，再 apply-review。使用分頁優先完成與使用者問題相關的部分；覆蓋不足時直接說明，不加任意全片通過門檻。

## 參考來源

設計借鏡時間定位、證據來源分離與按需查詢，沒有複製其他專案實作：
- [Grounded Video Agent：claim 與 evidence 關聯檢查](https://github.com/sensniu/grounded-video-agent/blob/fea84c8ccc7f2b77ce1abbc391f0177df282483b/src/grounded_video_agent/agent/verification/verifier.py)
- [timecode-agent：待驗證項目排序](https://github.com/mupozg823/timecode-agent/blob/02f7c5a9ce1c09b4ba49177d2a4dc8e9ee1bbc03/src/video_agent/verify_priority.py)
- [Open Vision：時間範圍、原始圖片與 JSON 交接](https://github.com/michielhdoteth/openvision/blob/084d02957516cd55dd53eee1a6ba720c6f64100a/README.md)
