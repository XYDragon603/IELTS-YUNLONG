# 同义替换资料导入与复核

`npm run import:synonyms` 从用户本地的 8 份同义替换整理 PDF 提取资料，不调用 LLM，也不修改原始 PDF。资料位于 `IELTS/剑雅真题【4-19】/真题/剑1-剑16同义词替换PDF/`。这些是学习资料，不能等同于 Cambridge 官方答案或逐题核验的解析。

当前提取 2,074 条原始记录，合并为 2,050 张词卡，生成 `resources/words/ielts-synonyms.json` 与 `resources/synonyms/cambridge-synonyms.json`。所有词卡都保留具体来源 PDF 路径和 1-based PDF 页码；页面上的“查看资料 PDF”打开对应文件与页面。词书整体 `verified: false`，因为自动提取和语义关系尚未逐条核对。

原资料未提供中文释义的 665 张词卡标记为 `meaningStatus: missing-in-source`，界面直接说明，不自动生成释义。41 张词卡进入 `resources/synonyms/review-queue.json`：长度异常 19 条、疑似断词 1 条、提取词组未在来源页中精确匹配 22 条（标记可重叠）。这些标记只提示复核，不自动改写原文。不能仅凭正则或页码匹配断定两种表达在任意语境下等价。

剑 14、剑 15 的 178 个题号有资料条目对应。导入器为现有听力、阅读题目附加 `explanation.paraphraseSources`，包含两个表达、来源 PDF、页码、词卡 ID 和复核标记。听力导入预览与阅读练习在**交卷后**展示这些资料，并可一键收藏到词书；听力同时展示现有听力稿定位，阅读保留题干和原卷页链接。阅读文章只有在替换表达于文章文本中**唯一逐字匹配**时才显示原文片段；没有匹配时不编造定位句。其他册次没有可靠的题号映射，暂不强行关联。题号关联来自整理资料，仍需对照原卷确认，不把它当成官方解析。

重新导入与检查：

```powershell
npm.cmd run import:synonyms
npm.cmd run check
npm.cmd test
```

后续人工复核应优先检查复核清单中的 41 张词卡，再抽样检查题号关联与语境等价性。需要补中文释义时，应记录新增释义的来源和校对者，不要把自动生成内容标为原 PDF 内容。
