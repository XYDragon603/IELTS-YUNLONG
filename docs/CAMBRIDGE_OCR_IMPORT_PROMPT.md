# Cambridge IELTS 4–20 本地 OCR 与结构化导入 Prompt

你是一名本地数据工程与 OCR 工程代理。请在当前 IELTS Studio 项目中，完整整理用户已经拥有的 Cambridge IELTS 4–20 本地资源，并输出可供网页练习系统读取的结构化数据。

这是一个需要实际执行的编码任务。不要只提出建议或示例；请编写脚本、运行脚本、检查结果、修复识别问题，并按批次完成导入。

## 一、不可违反的要求

1. 所有 PDF、音频、视频和文档都只在本地处理。
2. 不要把整本 PDF、整本 OCR 文本或大量页面内容发送到模型上下文。
3. 不要移动、重命名、覆盖或删除 `IELTS/` 内的任何原始文件。
4. 基础提取必须使用本地 Python 或 Node 工具完成，不使用 LLM OCR 整本书。
5. 每页优先检测 text layer；有可靠文字层时直接提取，只有没有文字层或文字层质量不合格时才运行 OCR。
6. OCR 优先使用本机 Tesseract；若已有更可靠的本地 OCR 工具，可增加适配器，但不得依赖云端服务。
7. 规则解析优先。LLM 只允许处理规则无法确定的小片段，而且每次只能提供一个题组或一页的必要片段。
8. 一次只处理一本书、一个 Test、一个 Skill。完成并验证后才进入下一项。
9. 不得根据常识补全无法识别的题目、答案或解析。无法确认时使用 `null` 并加入 `needsReview`。
10. 所有数据都必须保留来源页码和识别方式，以便人工追溯。
11. Cambridge 题目正文保持原文，不要翻译或改写题目。
12. 不要将 OCR 缓存、整页图片或完整正文提交到 Git。缓存必须放入已忽略的 `.cache/` 或 `artifacts/`。
13. 不要破坏项目已有页面、练习记录、本地存储和测试。

## 二、项目现状

- 项目根目录中有 `IELTS/` 原始资源目录。
- PDF page map 工具：`scripts/cambridge_pdf_importer.py`
- 已验证 page map：`resources/page-maps/cambridge-18.json`
- 已有资源扫描器：`scripts/scan-resources.mjs`
- 已有资源清单：`resources/manifest.js`
- 当前试题示例：`resources/c18-t1-listening.js`
- 当前项目是原生 JavaScript 模块、CSS 和 Node.js 本地服务器。
- 目标范围是 Cambridge IELTS 4–20，以 Academic 为主；General Training 文件不要混入 Academic 题库。

现有 `c18-t1-listening.js` 可以作为字段含义参考，但不要假设它的手工内容就是最终导入格式。优先设计统一、可验证、可批量生成的 JSON schema。

## 三、总体处理流程

必须严格按以下阶段执行：

```text
原始资源扫描
→ 选择每册 canonical PDF
→ PDF page map
→ 单个 Test + Skill 文本提取
→ 题组与题目解析
→ 答案提取和交叉核对
→ Audioscript 提取和题号定位
→ 精讲资源提取（存在时）
→ 音频路径映射
→ JSON schema 校验
→ 人工复核清单
```

不要跳过 page map 直接解析整本书。

## 四、原始文件扫描与 canonical 文件选择

先递归扫描 `IELTS/`，生成：

```text
resources/import-manifest.json
```

每一本书记录：

- Cambridge 册次
- Academic 原卷候选文件
- General Training 文件
- 重复文件
- 精讲 PDF
- Audioscript 所在文件或页段
- Answer key 所在文件或页段
- Listening MP3
- 讲解视频
- 缺失文件
- 未下载完成的 `.downloading` 文件
- 文件大小
- SHA-256

canonical 文件选择规则：

1. 优先 Academic 完整原卷。
2. 排除文件名含 `G类`、`General Training` 的文件。
3. 相同 SHA-256 的重复文件只选一个作为 canonical，其他记录为 duplicate，不删除。
4. 如果同一本存在普通版和 `(1)` 版，比较页数、清晰度、文字层质量和文件完整性后选择。
5. Cambridge 20 若每个 Test 是独立 PDF，应记录为 per-test PDF，不能假设是整本文件。
6. `.downloading` 文件一律标记为 incomplete，不读取为有效资源。

## 五、Phase A：生成全部 page map

先复用或改进：

```text
scripts/cambridge_pdf_importer.py
```

对 Cambridge 4–20 逐册生成：

```text
resources/page-maps/cambridge-04.json
resources/page-maps/cambridge-05.json
...
resources/page-maps/cambridge-20.json
```

需要识别：

- TEST 1 / TEST 2 / TEST 3 / TEST 4
- LISTENING
- READING
- WRITING
- SPEAKING
- ANSWER KEY / ANSWER KEYS / ANSWERS
- AUDIOSCRIPT / AUDIOSCRIPTS
- Sample Writing Answers

每个页段同时保存：

- 书上印刷页码
- 1-based PDF 页码
- `text-layer` 或 `ocr`
- heading evidence
- confidence

输出示例：

```json
{
  "schemaVersion": 1,
  "book": 18,
  "source": {
    "path": "IELTS/.../剑桥雅思真题18.pdf",
    "sha256": "...",
    "pageCount": 149,
    "originalModified": false
  },
  "tests": {
    "1": {
      "listening": {
        "startPage": 10,
        "endPage": 15,
        "pdfStartPage": 12,
        "pdfEndPage": 17,
        "detectedBy": "ocr",
        "confidence": 1.0
      }
    }
  },
  "landmarks": [],
  "needsReview": []
}
```

只有当一本书的 page map 已识别完整，或者缺失项已明确进入 `needsReview`，才处理其具体题目。

## 六、Phase B：一次提取一个 Test + Skill

实现新的命令，例如：

```powershell
python scripts/cambridge_pdf_importer.py extract-skill `
  --book 18 `
  --test 1 `
  --skill listening `
  --page-map resources/page-maps/cambridge-18.json
```

提取范围必须来自 page map 的 `pdfStartPage` 和 `pdfEndPage`，禁止重新扫描整本 PDF。

中间结果输出到：

```text
.cache/cambridge-importer/<fingerprint>/skills/test-1-listening.json
```

中间结果至少包含：

```json
{
  "book": 18,
  "test": 1,
  "skill": "listening",
  "sourcePages": {
    "pdfStartPage": 12,
    "pdfEndPage": 17
  },
  "pages": [
    {
      "pdfPage": 12,
      "printedPage": 10,
      "method": "ocr",
      "confidence": 0.97,
      "text": "..."
    }
  ],
  "needsReview": []
}
```

这个缓存文件不要提交到 Git，也不要整份复制到模型上下文。

## 七、Phase C：题目结构化 JSON

每个 Test + Skill 输出一个独立 JSON：

```text
resources/cambridge/c18/test-1/listening.json
resources/cambridge/c18/test-1/reading.json
resources/cambridge/c18/test-1/writing.json
resources/cambridge/c18/test-1/speaking.json
```

Listening 和 Reading 的通用结构：

```json
{
  "schemaVersion": 1,
  "id": "c18-t1-listening",
  "book": 18,
  "test": 1,
  "skill": "listening",
  "variant": "academic",
  "title": "Cambridge IELTS 18 · Test 1",
  "verified": false,
  "sources": {
    "paper": {
      "path": "IELTS/...pdf",
      "sha256": "..."
    },
    "questionPdfPages": [12, 13, 14, 15, 16, 17],
    "answerPdfPages": [123],
    "transcriptPdfPages": [103, 104, 105, 106, 107],
    "explanation": null
  },
  "parts": [],
  "answerKey": {},
  "audio": {},
  "needsReview": []
}
```

每个题组结构：

```json
{
  "id": "part-1-group-1",
  "part": 1,
  "questionRange": [1, 10],
  "type": "form-completion",
  "instruction": "Complete the notes below...",
  "title": "Transport survey",
  "context": [],
  "options": [],
  "questions": [],
  "source": {
    "pdfPage": 12,
    "printedPage": 10,
    "boundingBox": [0.1, 0.2, 0.9, 0.8],
    "method": "ocr",
    "confidence": 0.96
  }
}
```

每道题结构：

```json
{
  "id": "q1",
  "number": 1,
  "numbers": [1],
  "type": "text",
  "prompt": "Postcode: ____",
  "options": [],
  "maxChoices": 1,
  "wordLimit": "ONE WORD AND/OR A NUMBER",
  "answer": {
    "accepted": ["DW30 7YZ", "DW307YZ"],
    "sourcePdfPage": 123,
    "confidence": 1.0
  },
  "transcriptEvidence": null,
  "explanation": null,
  "source": {
    "pdfPage": 12,
    "printedPage": 10,
    "boundingBox": [0.2, 0.3, 0.8, 0.4],
    "method": "ocr",
    "confidence": 0.95
  },
  "needsReview": []
}
```

必须支持这些题型：

- form-completion
- note-completion
- table-completion
- flow-chart-completion
- sentence-completion
- summary-completion
- short-answer
- single-choice
- multiple-choice
- matching
- map-labelling
- diagram-labelling
- true-false-not-given
- yes-no-not-given
- heading-matching
- matching-information
- matching-features
- writing-task-1
- writing-task-2
- speaking-part-1
- speaking-part-2
- speaking-part-3

如果一个题组包含共用选项，选项放在 group 层，题目只引用 `optionSetId`。不要为每道题重复保存全部选项。

## 八、图片题处理

Map、Plan、Diagram、流程图、表格或无法可靠转为纯文本的视觉题：

1. 不要重新绘制或凭 OCR 猜测。
2. 从原 PDF 页面裁剪最小必要区域。
3. 输出到：

```text
resources/cambridge/c18/test-1/assets/listening-q15-20.webp
```

4. 保留原始宽高比。
5. 清晰度足以阅读，优先 WebP；文字必须清晰。
6. JSON 中记录：

```json
{
  "asset": "./assets/listening-q15-20.webp",
  "alt": "Map used for Questions 15–20",
  "sourcePdfPage": 14,
  "boundingBox": [0.1, 0.2, 0.9, 0.75]
}
```

7. 不要导出整页扫描图，只保留做题所需区域。

## 九、Answer Key 提取与验证

答案必须来自原书 Answer Key，不允许从题意推断。

处理要求：

1. 根据 book、test、skill 和题号提取答案。
2. 保留大小写不敏感的可接受答案。
3. 保留原书明确给出的替代拼写和斜线答案。
4. 多选题必须记录无顺序答案，例如：

```json
{
  "accepted": ["B", "E"],
  "orderMatters": false
}
```

5. 如果 Answer Key 的题号或答案 OCR 置信度不足，不要猜测，加入：

```json
{
  "type": "answer-ocr-low-confidence",
  "question": 27,
  "sourcePdfPage": 123,
  "ocrText": "B/E?",
  "message": "需要人工核对"
}
```

6. 自动检查 Listening 和 Reading 是否各有 40 个计分点。
7. 多选题一组对应多个计分点，不能把两项合并成一个分数。

## 十、Audioscript 与听力证据

Audioscript 只按一个 Test 的范围提取，并按 Part 1–4 分段。

输出：

```text
resources/cambridge/c18/test-1/audioscript.json
```

结构：

```json
{
  "book": 18,
  "test": 1,
  "parts": [
    {
      "part": 1,
      "sourcePdfPages": [103, 104],
      "segments": [
        {
          "speaker": "MAN",
          "text": "...",
          "questionRefs": [1],
          "sourcePdfPage": 103,
          "confidence": 0.96
        }
      ]
    }
  ],
  "needsReview": []
}
```

题目中的 `transcriptEvidence` 必须引用 audioscript segment ID，不要复制整段听力稿到每道题中。

```json
{
  "segmentIds": ["c18-t1-p1-s07"],
  "quote": "It’s DW30 7YZ.",
  "sourcePdfPage": 103
}
```

`quote` 只保留定位答案所需的短句。

## 十一、精讲与解析资源

如果本地存在精讲 PDF：

1. 单独扫描精讲目录，不要把精讲 PDF 当作原卷。
2. 建立书、Test、Skill、题号到精讲页的映射。
3. 优先提取：原文定位、正确原因、错误选项原因、词汇、同义替换。
4. 无法稳定匹配题号时，只建立页码索引并加入 `needsReview`。
5. 必须区分来源：

```json
{
  "kind": "publisher-answer-key"
}
```

```json
{
  "kind": "local-explanation-book"
}
```

```json
{
  "kind": "editorial-generated"
}
```

不要把自动生成的说明伪装成原书解析。

## 十二、Listening 音频映射

扫描全部 MP3，根据路径和文件名规则映射：

```json
{
  "1": {
    "path": "IELTS/.../18-1-1.mp3",
    "sha256": "...",
    "size": 12345678,
    "status": "ready"
  }
}
```

规则：

- 兼容 `C4T1S1.mp3`
- 兼容 `Test1.Section1.mp3`
- 兼容 `Test 1 Section 1.mp3`
- 兼容 `IELTS11_Test1_Section1.mp3`
- 兼容 `18-1-1.mp3`
- 兼容 `Test1 Part1.mp3`
- 兼容 `T1S1.mp3`
- Cambridge 12 若资源使用 Test 5–8 编号，需要明确映射到书内 Test 1–4，并记录 `originalTest`。
- 文件大小为 0、扩展名为 `.downloading` 或打不开的 MP3，状态必须是 incomplete。
- 不要因为文件名相似就覆盖已有映射；冲突应进入 `needsReview`。

## 十三、Writing 与 Speaking

Writing 需要输出：

- Task 1 instruction
- Task 1 prompt
- 图表或图片裁剪资源
- Task 2 instruction
- Task 2 prompt
- 字数要求
- Sample Writing Answer 页码映射（若存在）

Speaking 需要输出：

- Part 1 topics 与 questions
- Part 2 cue card
- Part 3 discussion topics 与 questions
- source page 与 OCR confidence

Writing 和 Speaking 不生成虚构答案或分数。

## 十四、验证器

实现本地验证命令，例如：

```powershell
python scripts/validate_cambridge_import.py resources/cambridge/c18/test-1/listening.json
```

至少检查：

- JSON schema 合法
- ID 唯一
- 题号连续
- Listening / Reading 计分点为 40
- 每道可判分题都有 Answer Key 来源
- 多选题的选项数量与计分点一致
- 所有 PDF 页码在原文件范围内
- 所有音频路径存在且文件大小大于 0
- 所有图片资源存在
- 所有 transcript segment 引用存在
- 不允许空字符串伪装成已识别内容
- 不允许 `verified: true` 且仍有关键 `needsReview`

只有全部校验通过并完成抽样检查后，才能将某个 Test + Skill 标记为：

```json
"verified": true
```

## 十五、处理顺序

按以下顺序推进：

1. 扫描所有原始文件，生成 import manifest。
2. 为 Cambridge 4–20 生成 page map。
3. 汇报 page map 完整度，不解析题目。
4. 完整处理 Cambridge 18 · Test 1 · Listening，作为基准样例。
5. 校验样例并与现有 `resources/c18-t1-listening.js` 对比，列出字段差异和 OCR 差异，不直接覆盖已验证数据。
6. 样例稳定后，按以下循环逐项处理：

```text
Book 20 → Test 1 → Listening
Book 20 → Test 1 → Reading
Book 20 → Test 1 → Writing
Book 20 → Test 1 → Speaking
Book 20 → Test 2 → ...
...
Book 4 → Test 4 → Speaking
```

每完成一个 Test + Skill：运行验证器，输出一条简短状态记录，再继续下一项。

如果批处理需要很长时间，可以持续执行，但不要一次把所有 OCR 文本打印到终端。终端只输出：

- 当前 book / test / skill
- 页数进度
- text layer 或 OCR
- 识别题数
- 校验是否通过
- `needsReview` 数量

## 十六、失败处理

遇到以下情况必须停止当前项目并记录，不得猜测：

- 页码区间无法确定
- Test 或 Skill 标题缺失
- OCR 无法稳定识别题号
- 地图或图表题缺少必要图片
- Answer Key 缺页
- 音频文件不完整
- A 类与 G 类来源无法区分
- 两个候选答案来源互相冲突

记录到：

```text
resources/import-report.json
```

然后继续处理不依赖该问题的下一个 Test + Skill。

## 十七、最终交付

完成后提供：

1. 新增或修改的脚本清单。
2. 每册 page map 状态。
3. 每个 Test + Skill 的状态：`ready / needs-review / missing-resource`。
4. OCR 页数、text-layer 页数和缓存命中数。
5. 已识别题目数与已验证题目数。
6. 缺失或损坏的 PDF、MP3、图片和解析资源。
7. 所有自动测试和数据校验结果。
8. 明确说明没有移动、删除或修改任何 `IELTS/` 原始文件。

先执行文件扫描和 Cambridge 4–20 page map。完成并验证 page map 后，再开始 Cambridge 18 · Test 1 · Listening 样例。不要在 page map 尚未确认前批量解析题目。
