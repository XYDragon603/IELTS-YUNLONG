# C18 Test 1 Listening 导入预览

运行 `npm.cmd start`，打开 http://127.0.0.1:4173/import-preview.html ，或从 Cambridge 18 Test 1 详情页进入“导入数据预览”。

预览直接加载 `resources/cambridge/c18/test-1/listening.json` 和 `audioscript.json`。支持四个 Part、原卷音频、答案和音频位置保存、标记、暂定计分、录音稿证据查看及 JSON 答题记录导出。

独立使用 `ielts-c18-t1-import-preview-v1` 本地存储键，不覆盖原练习记录。三组多选题合并显示，每组仍有两个计分点，总分为 40。暂定分数不换算 Band。

## 当前审计结论

真实 OCR 缓存已存在。导入脚本仍在 Q1/Q2 答案和 Part 1/4 题干中包含按题号校订的固定文本，复核备注也内置于脚本。因此目前属于 OCR 加校订版本，并未完成独立来源核验。此前 walkthrough 中的“纯算法、生产就绪”结论应以本次审计为准。

本次保留校订内容供预览，将 generationMode 标记为 ocr-assisted-curation，并由 needsReview 阻止 verified:true。未知低置信度项不再默认 confirmed。下一步应把校订提取为与 OCR 文件哈希绑定的复核记录，逐项核对内容，再决定发布状态。人工校订可作为有效数据来源，但必须如实标记。

验证器的模式字符串、哈希和边界框形状检查仍不能证明文本正确；预览页始终标注待核对。听力稿来源片段展示不等同于已核实的题目精讲。
