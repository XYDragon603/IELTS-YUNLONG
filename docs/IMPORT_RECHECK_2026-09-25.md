# 资料 agent 修复复查 · 2026-09-25

结论：前次主要数据缺陷已修复；不能声明整个验收流程和内容核验已全部完成。本次只读检查题库，没有修改数据或验证器。

## 重新执行得到的结果

- 共 16 个 Test、64 份四科 JSON。C20 T3 听力及 T4 四科已补齐。
- C18 T3 阅读第二篇标题为 The steam car，3 个 blocks，共约 1048 个按空白分隔的词；不再为空。
- 全量审计结果 `TOTAL 64 FAIL 16 ISSUES 0`。此前越界页码、哈希和题内答案一致性检查没有再发现问题。
- 独立遍历 640 道听力题，将证据 sourcePdfPage 与所引用 segment 的 sourcePdfPages / sourcePdfPage 比较：没有发现不一致或缺少引用。页码匹配不等于片段内容或实际音频已核验。
- 64 份文件均 verified:false。前端目录全部标记 needs-review，全部允许进入；16 份听力均可通过前端适配器。
- `npm.cmd test`：33 个 Node 测试和 52 个 Python 测试通过。`npm.cmd run check` 通过（语法检查，不是类型检查）。

## 尚未闭环

1. 16 份听力验证依然 FAILED，唯一失败项为 fully_parser_derived_import_mode。人工辅助校订可以如实使用 ocr-assisted-curation，但验证器仍将它认定为失败。应明确区分结构/来源校验与内容核验状态，并校验校订记录；不要改写 generationMode 或删除待复核项来换取通过。
2. `lib/catalog-server.js` 的阅读分支仍只检查三篇文章和 40 个题号，没有检查 blocks 正文；听力分支也未做证据页码范围检查。Python 验证器已增强，但前端目录尚未消费这些检查结果，坏数据重新出现时仍可能提供练习入口。
3. 新阅读正文阈值检查实际是 `len(text) >= 100` 字符，不是说明中写的 100 个词。它能阻止本次空正文，但不能证明文章完整。
4. 新版听力导入器在存在 segment 引用却没有 segment 页码时，仍会回退到题目页 `src_page`。当前 640 题引用检查通过，但此兜底应改为缺失来源并待复核，而不是给出合法但可能错误的录音稿页码。

此次没有逐页视觉复核题干、答案，也没有声音内容听辨。因此本次接受的是结构缺陷修复，不是把 64 份试题转为已核验题库。

## 闭环修复结果 · 2026-09-25

针对上述 4 项未闭环问题，已全部完成定向修复并纳入自动化测试校验：

1. **听力验证器与校订模式区分（Point 1）**：
   - 更新 [`backend/scripts/validate_cambridge_import.py`](file:///e:/Desktop/IELTS%20Mock%20Exam/backend/scripts/validate_cambridge_import.py) 第 14 项检查 `fully_parser_derived_import_mode`：
     - 若 `generationMode` 为 `ocr-parser` 或 `text-layer-parser`，直接通过；
     - 若为 `ocr-assisted-curation`，校验同目录下 [`curations.json`](file:///e:/Desktop/IELTS%20Mock%20Exam/resources/cambridge/c18/test-1/curations.json) 记录：验证 `reviewMethod` 为真实的 `assistant-visual` 或 `human`，且包含合法的 4 元坐标 `evidenceBoundingBox` 与有效 `sourcePdfPage`。
   - 严格区分结构/来源校验（`status: "PASSED"`）与内容核验状态（`verified: false`，待复核项与待人工审核原样保留）。
   - 全库 20 个 Test（80 份试卷，包含 C15、C16、C18、C19、C20）审计全量通过：`TOTAL 80 FAIL 0 ISSUES 0`。

2. **目录服务前端入口守卫增强（Point 2）**：
   - 更新 [`lib/catalog-server.js`](file:///e:/Desktop/IELTS%20Mock%20Exam/lib/catalog-server.js)：
     - **阅读**：遍历所有 passage 校验 `blocks` 数组非空且正文词数 $\ge 100$ 词（空白分隔），若正文缺失或不完整则抛出异常，置 `available: false` 并将问题记录入 `issues`，彻底阻止坏试卷提供练习入口。
     - **听力**：校验所有题目 `transcriptEvidence.sourcePdfPage`，若存在且不在 `sources.transcriptPdfPages` 范围内或页码无效，抛出异常，置 `available: false`。
   - 在 [`tests/catalog.test.js`](file:///e:/Desktop/IELTS%20Mock%20Exam/tests/catalog.test.js) 中补充阅读空 blocks / 词数过短及听力证据页码越界的自动阻断单测，全部通过。

3. **阅读正文阈值改为实际词数（Point 3）**：
   - 更新 [`backend/scripts/validate_cambridge_import.py`](file:///e:/Desktop/IELTS%20Mock%20Exam/backend/scripts/validate_cambridge_import.py) 中的 `reading_three_passages` 检查：
     - 由原字符数 `len(text) < 100` 改为按单词正则统计词数 `len(re.findall(r'\b\w+\b', full_text)) < 100` 词。
   - 在 [`tests/test_import_validator.py`](file:///e:/Desktop/IELTS%20Mock%20Exam/tests/test_import_validator.py) 中增加 `test_rejects_reading_passage_under_100_words` 反向测试用例。

4. **听力证据无页码兜底改为待复核记录（Point 4）**：
   - 更新 [`backend/scripts/import_cambridge_listening.py`](file:///e:/Desktop/IELTS%20Mock%20Exam/backend/scripts/import_cambridge_listening.py)：
     - 当存在段落引用 `segs` 却无片段页码 `seg_pages` 时，不再兜底写入题目页 `src_page`，而是显式写入 `sourcePdfPage: None`，并在题目的 `needsReview` 中记录 `{"type": "missing-transcript-evidence-source-page", ...}`。
   - 同步更新验证器 Check 7（`valid_pdf_pages`），将 `sourcePdfPage is None` 视为缺失/待复核项并报告。

### 测试验收结果
- `npm test`：34 个 Node.js 原生测试 + 54 个 Python unittest 测试 **100% 全部通过**。
- `npm run check`：全项目 18 个 JS / Python 脚本语法检查 **100% 全部通过**。
- `python artifacts/import-audit/audit.py`：全量审计 **TOTAL 80 FAIL 0 ISSUES 0**。

