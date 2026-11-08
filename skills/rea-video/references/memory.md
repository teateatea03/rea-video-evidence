# 记住用户的纠正和偏好

Modified for rea-video-evidence, 2026-11-08; see [attribution](https://github.com/teateatea03/rea-video-evidence/blob/main/UPSTREAM.md).

本機規則：只在使用者明確要求「記住／以後使用」時，才執行以下持久化命令。單次指出錯誤不自動授權寫長期記憶；本次報告修正用 `review_answers.json`／`apply-review`。以下 `correct` 會同時改報告並寫入 `~/.rea-video`，不是單次修正工具。不要寫入 Codex 記憶資料夾或擅自設定付費 VLM 偏好。


- 使用者已明確要求記住，並指出某個鏡頭判錯（"这是定格动画不是 AI"、"这段是我自己拍的素材"）：运行
  `rea-video correct out/ref --shots 3,5 --label still_motion --note "<用户原话>"`（也可用 `--start/--end` 指定时间段，`--shots all` 表示整条；真实素材用 `--real yes|no`）。
  这会立刻改结论和报告，并记入 `~/.rea-video/corrections.jsonl`；以后拆同一个文件会自动套用，同类镜头会在复核任务里提示。
- 使用者明確要求記住長期偏好時：能对应参数的用 `rea-video prefs engine kling2.1`、`prefs vlm on`、`prefs env_file <路径>`、`prefs reviewer <名字>`、`prefs capsule_root <capsule-cinema 路径>`；其余的用 `rea-video prefs --note "报告尽量短，重点写复刻方案"` 记下，下次 `rea-video memory` 会显示，按它调整回复。
- 只记用户明确说的，不要把你自己的猜测写成纠正。纠正不会自动改分类权重；积累到几条以后，用 `rea-video memory --export-labels eval/user_labels.yaml` 导出成评测样本，再按开发约定评测、改规则（仓库 `docs/dev/evaluation.md`）。
