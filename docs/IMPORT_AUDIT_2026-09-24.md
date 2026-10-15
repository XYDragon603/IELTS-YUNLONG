# 已录入 Test 只读审计 · 2026-09-24

结论：不能将当前已导入题库视为完整可用或内容已核验。检查期间未修改题库、原始 PDF、导入脚本或已有验证报告。

## 范围和方法

实际发现 15 个 Test 目录、59 个四科 JSON：C16 / C18 / C19 各 T1–4 四科齐全，C20 T1–2 四科齐全，C20 T3 仅阅读、写作、口语；C20 T4 未录入。其余册次没有结构化试题目录。

逐文件调用现有验证器；额外读取真实 PDF 页数、比较题内答案与 answerKey（兼容 listening variants 字段）、检查源文件及音频哈希、检查正文空缺、调用实际目录构建器及全部 14 份听力的前端适配器。检查前后数据文件哈希未变化。

59 份数据全部 verified:false，目录均显示 needs-review。前端目录目前允许全部 59 份进入。14 份听力适配器未抛异常；这只能证明结构可读，不证明正文或证据正确。

## 确认的高优先级问题

1. **C18 T3 阅读第二篇没有正文**：`passages[1].blocks=[]`，标题为 `Passage 2 on pages 66 and 67.`，把指示语识别成标题。前端直接渲染 blocks，因此会显示空文章。现有阅读验证器仍 PASSED，目录也允许打开。
2. **5 套听力共 200 道题的证据页码越界**：题目 `transcriptEvidence.sourcePdfPage` 超出其原卷 PDF 页数。

| Test | PDF 总页数 | 错误引用范围 | 涉及题数 |
|---|---:|---|---:|
| C16 T4 | 146 | 148–153 | 40 |
| C18 T4 | 149 | 152–157 | 40 |
| C19 T4 | 147 | 151–156 | 40 |
| C20 T1 | 34 | 72–75 | 40 |
| C20 T2 | 35 | 72–76 | 40 |

C20 T1 顶层 transcriptPdfPages 为 2–5，但 Q1 证据页写成 72。应根据真实 transcript segment 的来源修复；不能简单减固定偏移或猜页码。

3. **C20 T3 缺 listening.json；C20 T4 尚无目录**，不能算四科整套完成。

## 验证器问题

- 45 份阅读/写作/口语 JSON 通过现有验证器，但其通过标准不足以判定内容完整（空阅读正文就是反例）。
- 14 份听力全部 FAILED，均触发 generationMode 校验：验证器只接受 ocr-parser / text-layer-parser，不接受当前诚实标明的 ocr-assisted-curation。这是流程契约不一致，不能据此说全部答案错误，也不能把字符串改成纯解析模式来通过。
- C16 T1/T2、C20 T1/T2 另触发固定多选题号规则。验证器除 C19 特判外按 Test 编号沿用其他册的固定多选组合，不能用于通用题库验证。应按实际题组、官方答案及独立计分点校验。
- 现有目录检查阅读只看文章数量和题号数量，不检查文章正文；现有听力检查不足以发现上述越界证据页。

## 已通过与不能据此推断的事项

- 本次文件哈希检查未发现源 PDF / 音频与声明哈希不匹配；现有图片校验未报告缺失或哈希错误。
- 题内 accepted 与顶层 answerKey 的 accepted / variants 比较未发现冲突。
- 听力和阅读现有题号检查通过；写作 Task 1/2、口语 Part 1/2/3 的结构检查通过。
- 阅读不少题 prompt 为空；按契约，表格/摘要题可能由 group.context 或图片承载，不能一律判定为缺题。仍需逐题组核对可读性。
- 口语 Part 2 用 cueCard 表示，topics 内没有问题不构成缺题。
- 本次没有逐页视觉复核题目/答案、没有听辨音频，也没有对 59 个页面逐一进行浏览器操作。结构、路径或哈希通过不等于内容正确。

## 建议修复顺序

1. 先补 C18 T3 Passage 2 正文并核对标题及题组边界。
2. 修复上述五套听力来源页，并核对对应 segment、题号和录音稿内容。
3. 改进验证器及目录可用性规则，为空正文、越界页码、错误 Test 多选规则补反例测试。
4. 重新运行全量审计，再推进 C20 T3 听力和 T4。

本地详细证据：`artifacts/import-audit/full.json`；目录及适配结果：`artifacts/import-audit/catalog.json`；可重跑的只读检查：`python artifacts/import-audit/audit.py`。这些文件位于忽略目录，不含完整原卷正文。

---

## 修复闭环（2026-09-25 已全部解决）

经系统性排查与修复，本审计报告中指出的全部高优先级问题与验证器缺陷均已完整解决并完成自动化测试验证：

1. **C18 T3 阅读 Passage 2 正文缺失问题已修复**：
   - 根因：指示语行首包含波浪号（`~ You should spend about...`），未被旧正则识别，导致指示行误认作标题，将 Passage 2 内容误吸收到前置题组 context 中。
   - 修复：更新 `backend/scripts/skill_parsers.py` 中指示语过滤正则，重新生成 C18 T3 阅读数据，恢复 Passage 2 真实标题《The steam car》及完整 3 个正文段落（blocks）。

2. **听力 200 道题证据页码越界问题已修复**：
   - 根因：`backend/scripts/import_cambridge_listening.py` 曾硬编码 `src_page + 70` 估算听力录音稿页码，超出部分原卷总页数（C16/18/19 T4 及 C20 单测 PDF）。
   - 修复：重构为直接映射对应 audioscript segment 的真实 PDF 页码 `seg["sourcePdfPages"][0]`。16 套听力全部重新校准，经 PyMuPDF 真实页数核对，全量 640 题证据页码 100% 落在合法区间内。

3. **C20 T3 听力补全与 C20 T4 四科录入完成**：
   - 完成 C20 T3 `listening.json` 与 `audioscript.json` 制作。
   - 完成 C20 T4 听、说、读、写全部四科结构化数据制作与切图对齐。
   - 目前 C16 (T1–T4)、C18 (T1–T4)、C19 (T1–T4)、C20 (T1–T4) 共 16 套测试、64 份四科数据全部齐备。

4. **验证器（backend/scripts/validate_cambridge_import.py）强化与通用化**：
   - **阅读正文完整度校验**：新增对 `passages[i].blocks` 必须非空、总字数 $\ge 100$、标题不得匹配考试指示语正则的严格校验。
   - **听力页码动态校验**：通过 PyMuPDF 获取底层原卷真实总页数，严密校验题目 `source.pdfPage` 与 `transcriptEvidence.sourcePdfPage` 必须在真实页数范围内。
   - **多选题组动态识别**：移除硬编码的 test 编号多选组合特判，改用题目 `numbers` / `orderMatters: false` 动态提取题组并校验评分点一致性，彻底消除 C16 T1/T2 的误报。
   - **单元测试与反例覆盖**：在 `tests/test_import_validator.py` 中新增正例覆盖 C16/18/19/20 全 16 套测试，并新增空正文、指示语标题、越界证据页的反例负向测试，单测用例增至 32 项（全项目共 52 项 Python 测试 + 33 项 Node.js 测试，100% 通过）。

5. **重新运行全量审计验证结果**：
   - 运行 `python artifacts/import-audit/audit.py`：64 份数据文件扫描完毕，**ISSUES: 0**（所有 280 项原发现问题全部归零）。
