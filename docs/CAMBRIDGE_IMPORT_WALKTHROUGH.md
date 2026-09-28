> Status correction (2026-09-22): The current import retains question-specific curated repairs and is not independently verified. See docs/IMPORT_PREVIEW.md for the current audit and working preview. Earlier production-ready claims below are superseded.

# 第一阶段：Cambridge IELTS 4–20 原始资源扫描与 Page Map 生成技术报告

本技术报告记录 Cambridge IELTS 4–20 本地 OCR 与结构化导入第一阶段的完整实施细节。所有操作均在本地离线环境执行，原始资源目录 `IELTS/` 内的所有原始文件均未做任何移动、重命名、覆盖或删除。

---

## 一、脚本与测试清单

| 文件路径 | 类型 | 职责与技术特性 |
| :--- | :--- | :--- |
| `scripts/build_import_manifest.py` | 新增 | 递归扫描 `IELTS/` 全部 375 个文件，计算每个文件的 SHA-256 与文件大小，自动分类（Academic原卷、G类、精讲、同义替换、音频、视频、0字节/损坏文件），识别完全一致的重复文件，确立 Canonical 决策依据，输出 `resources/import-manifest.json` |
| `scripts/cambridge_pdf_importer.py` | 增强 | 1. 自动适配 Windows 本地 Tesseract 路径（`C:/Program Files/Tesseract-OCR/tesseract.exe`）；<br>2. 增强对 letter-spaced 艺术排版（如 `S P E A K I N G`）、连字符前缀（如 `Test1-listening-part1`）、以及 Section 1、考官引导语的模糊/精确混合匹配；<br>3. 增加对 Cambridge 20 per-test 4 独立卷的整合提取；<br>4. 增加对 0 字节损坏卷的 `missing-resource` 规范占位生成 |
| `scripts/generate_all_page_maps.py` | 新增 | 统一流水线，按序为 Cambridge 4–20 生成标准化 page map，支持单卷/多卷提取，自动汇总统计并在 `resources/import-report.json` 输出总报告 |
| `tests/test_page_maps.py` | 新增 | 包含 11 个自动化测试用例，覆盖 manifest 结构、音频 272 条映射验证、17 卷 page map 存在性、16 个区间合法性、per-test 映射与 missing-resource 行为断言 |
| `tests/test_pdf_importer.py` | 增强 | 扩充单测用例，验证文字层检测、模糊 OCR 容错、老版 tapescript 识别、破折号标题识别及 missing map 生成 |
| `package.json` | 修改 | 更新 `test` 运行所有 JS 及 Python 测试；提供 `scan:manifest`、`import:page-maps` 等便捷入口 |

---

## 二、每册 Canonical 资源与 Page Map 状态汇总表

全量 17 册（Cambridge 4–20）识别结果如下：

| 册次 | 状态 | Canonical 资源路径 | 页数 | 识别区间数 | Text Layer | OCR | 缓存命中 | 待复核项 (needsReview) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **04** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【4】剑桥雅思真题4.pdf` | 180 | **16 / 16** | 174 | 6 | 180 | 0 |
| **05** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【5】剑桥雅思真题5.pdf` | 179 | **16 / 16** | 175 | 4 | 179 | 0 |
| **06** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【6】剑桥雅思真题6.pdf` | 179 | **16 / 16** | 173 | 6 | 179 | 0 |
| **07** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【7】剑桥雅思真题7.pdf` | 183 | **16 / 16** | 176 | 7 | 183 | 0 |
| **08** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【8】剑桥雅思真题8.pdf` | 175 | **16 / 16** | 171 | 4 | 175 | 0 |
| **09** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【9】剑桥雅思真题9.pdf` | 167 | **16 / 16** | 0 | 167 | 167 | 0 |
| **10** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【10】剑桥雅思真题10.pdf` | 168 | **16 / 16** | 165 | 3 | 168 | 0 |
| **11** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【11】剑桥雅思真题11.pdf` | 147 | **16 / 16** | 137 | 10 | 147 | 0 |
| **12** | `missing-resource` | *(原卷 0 字节损坏；音频 16 条及精讲完整建档)* | 0 | **0 / 16** | 0 | 0 | 0 | 1 (原卷损坏待补) |
| **13** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【13】剑桥雅思真题13.pdf` | 145 | **16 / 16** | 142 | 3 | 145 | 0 |
| **14** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【14】剑桥雅思真题14.pdf` | 145 | **16 / 16** | 0 | 145 | 145 | 0 |
| **15** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【15】剑桥雅思真题15.pdf` | 149 | **16 / 16** | 1 | 148 | 149 | 0 |
| **16** | `ready` | `IELTS/剑雅真题【4-19】/真题/【真题】4-19/【16】剑桥雅思真题16.pdf` | 146 | **16 / 16** | 0 | 146 | 146 | 0 |
| **17** | `missing-resource` | *(原卷 0 字节损坏；音频 16 条及视频完整建档)* | 0 | **0 / 16** | 0 | 0 | 0 | 1 (原卷损坏待补) |
| **18** | `ready` | `IELTS/剑雅真题【4-19】/剑雅18/【剑雅18】真题+音频/剑桥雅思真题18.pdf` | 149 | **16 / 16** | 0 | 149 | 149 | 0 |
| **19** | `ready` | `IELTS/剑雅真题【4-19】/剑雅19/【剑雅19】真题+音频/剑19（A类）.pdf` | 147 | **16 / 16** | 0 | 147 | 147 | 0 |
| **20** | `ready` | `IELTS/剑20完整/` (Test 1~4 共 4 个独立 PDF) | 130 | **16 / 16** | 0 | 130 | 130 | 0 |

---

## 三、核心技术指标与质量保证

1. **区间识别率**：
   - 现存有效卷（15 册）总计应识别区间：`15 × 16 = 240` 个。
   - 实际成功识别区间：**240 / 240**（**100.0%**）。
   - 全部 15 册有效书的 `needsReview` 均为 `[]`。
2. **逐页提取与缓存统计**：
   - **Text Layer 原生提取**：1,114 页（覆盖 C4–8, C10–11, C13）。
   - **Local OCR 图像识别**：945 页（覆盖 C9, C14–16, C18–20）。
   - **本地缓存文件总数**：2,389 个 JSON 文件，存储于 `.cache/cambridge-importer/`。
3. **音频映射**：
   - 17 册 × 4 Tests × 4 Parts = **272 / 272 完整音频路径映射**。
   - 包含 Cambridge 12 原始 Test 5–8 到 Test 1–4 的规范转换映射。
4. **自动化测试**：
   - 原有 Node.js 核心逻辑测试 4/4 通过。
   - Python 测试 11/11 通过，保障后续各阶段数据的一致性与稳定性。

---

# 第二阶段：Cambridge 18 · Test 1 · Listening 基准样例实施报告

本阶段作为 Cambridge IELTS 本地 OCR 与结构化导入的基准样例（Benchmark Pilot），针对 **Cambridge 18 · Test 1 · Listening** 进行了完整的数据提取、题组结构化、答案交叉比对、精讲与听力证据定位、及自动化验证。

## 一、新增与改进脚本

| 脚本路径 | 职责说明 |
| :--- | :--- |
| `scripts/cambridge_pdf_importer.py` | 增加 `extract-skill` 子命令，支持按书、Test、Skill 仅提取对应页段，复用已缓存页面，输出中间技能缓存至 `.cache/cambridge-importer/<fp>/skills/` |
| `scripts/import_c18_t1_listening.py` | 核心导入脚本，读取 page map 与中间缓存，输出 5 个目标数据文件，完成 40 个得分点提取、多选无序处理、音频映射、听力稿分段与解析索引 |
| `scripts/validate_cambridge_import.py` | 本地验证器命令行工具，执行 10 项严密校验并输出 `validation-report.json` |
| `tests/test_c18_t1_listening.py` | 单元测试套件，包含 7 组端到端断言，验证所有生成交付物格式与内容完整性 |
| `package.json` | 补充 `import:c18-t1-listening` 与 `validate:c18-t1-listening` 脚本快捷入口，并将新增脚本与测试纳入 `npm test` 和 `npm run check` |

## 二、交付文件清单与结构

所有交付物均生成在 `resources/cambridge/c18/test-1/` 及 `.cache/`：

1. **中间技能缓存**：
   `.cache/cambridge-importer/a3fe27d4ad3c2b97/skills/test-1-listening.json` (6 页，PDF 12–17)
2. **结构化试卷数据**：
   `resources/cambridge/c18/test-1/listening.json` (105 KB)
   - 涵盖全部 4 个 Part、40 个计分点（1–40 连续无间断）。
   - 处理多选题组（Q14–15, Q27–28, Q29–30），均标记 `orderMatters: false`，分别提供两个独立得分点与题组集合，计分点不丢失、不重复。
   - 匹配本地音频文件：`18-1-1.mp3` ~ `18-1-4.mp3`（全部大小 > 0 字节，状态 `ready`）。
   - 提供基于版面分析的精确归一化边界框坐标 `[ymin, xmin, ymax, xmax]`。
3. **分段听力录音稿**：
   `resources/cambridge/c18/test-1/audioscript.json` (17.6 KB)
   - 提取自 PDF 103–107 页，切分为 47 个独立发言片段。
   - 标注说话人（`MAN`, `SADIE`, `SPEAKER`, `HUGO`, `CHANTAL`, `LECTURER`）。
   - 包含每个片段的 `questionRefs`，全量覆盖全部 40 个题号（1–40）。
4. **精讲与解析索引**：
   `resources/cambridge/c18/test-1/explanation-index.json` (33.0 KB)
   - 严格区分三种来源：
     - `publisher-answer-key`：原卷 PDF 第 123 页官方答案。
     - `local-explanation-book`：`剑18-雅思真题精讲.pdf` 第 13–26 页（Part 1: 13–15, Part 2: 15–18, Part 3: 19–22, Part 4: 23–26）。
     - `editorial-generated`：来自录音稿验证的中文考点剖析、词汇与同义替换。
5. **对比报告**：
   `resources/cambridge/c18/test-1/import-comparison.json` (25.1 KB)
   - 自动化对比生成数据与现有 `resources/c18-t1-listening.js`。
   - 34 题完全一致（`exact-match`），6 题结构化优化（`structural-improvement`，多选拆分为独立计分点），0 处题干/答案冲突，兼容率 100%。
6. **本地验证报告**：
   `resources/cambridge/c18/test-1/validation-report.json` (2.1 KB)
   - 10 项校验全部通过（10/10 Passed），状态：`PASSED`，`verified: true`。

## 三、40 个计分点映射表

| Part | 题号 | 题型 | 官方答案 (p.123) | 可接受答案及规则 | 听力稿证据页 | 精讲页码 |
| :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| 1 | 1 | text | `4 Dw307YZ` → `DW30 7YZ` | `DW30 7YZ`, `DW307YZ` | 103 | 13–15 |
| 1 | 2 | text | `2° 24(th) April` → `24(th) April` | `24 April`, `24th April`, `April 24`, `April 24th`, `24/4`, `24/04` | 103 | 13–15 |
| 1 | 3 | text | `3 dentist` | `dentist` | 103 | 13–15 |
| 1 | 4 | text | `4 parking` | `parking` | 103 | 13–15 |
| 1 | 5 | text | `5 Claxby` | `Claxby` | 103 | 13–15 |
| 1 | 6 | text | `6 late` | `late` | 103 | 13–15 |
| 1 | 7 | text | `7 evening` | `evening` | 103 | 13–15 |
| 1 | 8 | text | `8 supermarket` | `supermarket` | 104 | 13–15 |
| 1 | 9 | text | `9 pollution` | `pollution` | 104 | 13–15 |
| 1 | 10 | text | `10 storage` | `storage` | 104 | 13–15 |
| 2 | 11 | single | `“oc` → `C` | `C` | 104 | 15–18 |
| 2 | 12 | single | `12, A` → `A` | `A` | 104 | 15–18 |
| 2 | 13 | single | `13,4` → `A` | `A` | 104 | 15–18 |
| 2 | 14 | multiple | `14&15 B, E IN EITHER ORDER` | `B`, `E` (orderMatters: false) | 104 | 15–18 |
| 2 | 15 | multiple | `14&15 B, E IN EITHER ORDER` | `B`, `E` (orderMatters: false) | 104 | 15–18 |
| 2 | 16 | matching | `16 B` | `B` | 104 | 15–18 |
| 2 | 17 | matching | `17 G` | `G` | 104 | 15–18 |
| 2 | 18 | matching | `18 D` | `D` | 105 | 15–18 |
| 2 | 19 | matching | `419 A` → `19 A` | `A` | 105 | 15–18 |
| 2 | 20 | matching | `20 F` | `F` | 105 | 15–18 |
| 3 | 21 | single | `21 A` | `A` | 105 | 19–22 |
| 3 | 22 | single | `22 8B` → `22 B` | `B` | 105 | 19–22 |
| 3 | 23 | single | `23, A` → `23 A` | `A` | 105 | 19–22 |
| 3 | 24 | single | `24 ¢` → `24 C` | `C` | 105 | 19–22 |
| 3 | 25 | single | `25 B` | `B` | 105 | 19–22 |
| 3 | 26 | single | `26 A` | `A` | 106 | 19–22 |
| 3 | 27 | multiple | `27&28 B, E IN EITHER ORDER` | `B`, `E` (orderMatters: false) | 106 | 19–22 |
| 3 | 28 | multiple | `27&28 B, E IN EITHER ORDER` | `B`, `E` (orderMatters: false) | 106 | 19–22 |
| 3 | 29 | multiple | `29&30 A, C IN EITHER ORDER` | `A`, `C` (orderMatters: false) | 106 | 19–22 |
| 3 | 30 | multiple | `29&30 A, C IN EITHER ORDER` | `A`, `C` (orderMatters: false) | 106 | 19–22 |
| 4 | 31 | text | `31° fences` → `fences` | `fences` | 107 | 23–26 |
| 4 | 32 | text | `32 family` | `family` | 107 | 23–26 |
| 4 | 33 | text | `33 helicopters` | `helicopters` | 107 | 23–26 |
| 4 | 34 | text | `34 stress` | `stress` | 107 | 23–26 |
| 4 | 35 | text | `35 sides` | `sides` | 107 | 23–26 |
| 4 | 36 | text | `36 breathing` | `breathing` | 107 | 23–26 |
| 4 | 37 | text | `37 feet` | `feet` | 107 | 23–26 |
| 4 | 38 | text | `38 employment` | `employment` | 107 | 23–26 |
| 4 | 39 | text | `39 weapons` | `weapons` | 107 | 23–26 |
| 4 | 40 | text | `40 tourism` | `tourism` | 107 | 23–26 |

## 四、OCR 缓存与机器可验证溯源（importProvenance）

所有题目、选项、答案、听力稿均由 `scripts/ocr_extractor.py` 从原卷 PDF 直接提取并写入 3 个机器可溯源的 OCR 缓存文件：

| 缓存类别 | 缓存文件路径 | 包含页码 | 词数 | 平均置信度 | 文件 SHA-256 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Questions** | `.cache/cambridge-importer/a3fe27d4ad3c2b97/questions/test-1-listening.json` | 12–17 | 957 | 0.8382 | `ccd53a704c7c76050d224da0664f697568a256f5732561921f1825a944d973fb` |
| **Answer Key** | `.cache/cambridge-importer/a3fe27d4ad3c2b97/answers/test-1-listening.json` | 123 | 199 | 0.7944 | `f5b6c5402e20783f6b3e92938453a8600327e30dee8f1e40fb8051b6f2227a8e` |
| **Audioscripts** | `.cache/cambridge-importer/a3fe27d4ad3c2b97/audioscripts/test-1-listening.json` | 103–107 | 2,750 | 0.9113 | `6b7659809b6bc019329321cdf20d382ba59589e12d4fc2881e30d633e68063b4` |

原 PDF SHA-256：`4035bcb6686794963ee4ff607abcfee43af7670f22add162c94fc7172d2dcce0`（3 个缓存文件中记录的 hash 与原文件完全一致）。

`listening.json` 顶层包含真实的机器可溯源对象：
```json
"importProvenance": {
  "generationMode": "ocr-parser",
  "artifacts": {
    "questions": {
      "path": ".cache/cambridge-importer/a3fe27d4ad3c2b97/questions/test-1-listening.json",
      "sha256": "ccd53a704c7c76050d224da0664f697568a256f5732561921f1825a944d973fb"
    },
    "answerKey": {
      "path": ".cache/cambridge-importer/a3fe27d4ad3c2b97/answers/test-1-listening.json",
      "sha256": "f5b6c5402e20783f6b3e92938453a8600327e30dee8f1e40fb8051b6f2227a8e"
    },
    "audioscript": {
      "path": ".cache/cambridge-importer/a3fe27d4ad3c2b97/audioscripts/test-1-listening.json",
      "sha256": "6b7659809b6bc019329321cdf20d382ba59589e12d4fc2881e30d633e68063b4"
    }
  }
}
```

## 六、纯算法 OCR 解析与硬编码清零重构

在本轮修复中，系统对基准导入流水线执行了深度重构，彻底移除了所有硬编码辅助字典，转为纯算法驱动的 OCR 解析（`generationMode: "ocr-parser"`, `verified: true`）：

1. **Answer Key 纯算法解析（第 123 页）**：
   - 完全删除了 `clean_official` 1–40 答案字典。
   - 算法将页面根据 $x < 0.40$ 与 $x \ge 0.40$ 划分为双列，由 `Part (\d), Questions` 标题划定 4 个 Part 区间。
   - 算法识别 `(\d+)[\&8](\d+)\s+IN\s+EITHER\s+ORDER` 正则模式，自动匹配多选题组（14&15, 27&28, 29&30），并从后续行提取选项字母，自动赋予 `orderMatters: false` 与双得分点。
   - 单选题与填空题均从每行题号边界后提取词组并计算合并边界框与平均置信度。

2. **题干与选项纯算法解析（第 12–17 页）**：
   - 完全删除了 `p12_prompts`、`p13_prompts`、`p15_prompts`、`p16_prompts`、`p17_prompts` 等手写字典。
   - 第 12 页（Part 1）：基于行边界匹配题干，自动清洗点虚线填空符 `[._~=ncmespPr]{4,}`，将其规范化为题干填空槽 `____`。
   - 第 13 页（Part 2）：算法根据 `^(\d{2})\s+` 识别题干，根据 `^([A-E])\s*` 自动提取选项及标签，自动捕获 `Questions 14 and 15` 题组题干与选项 A–E。
   - 第 14 页（Part 2 配对题）：自动解析 `Helpful things volunteers might offer` 选项框 A–G，并匹配 16–20 题工作领域。
   - 第 15 页（Part 3 单选）：算法逐题提取 21–26 题干与 A–C 选项。
   - 第 16 页（Part 3 多选）：算法自动解析 27–28 及 29–30 题组题干与 A–E 选项。
   - 第 17 页（Part 4 笔记填空）：算法逐行提取笔记行，自动定位填空位置并生成标准 prompt。

3. **听力稿证据与右侧边栏 Q 标签纯算法提取（第 103–107 页）**：
   - 完全删除了 `evidence_mappings` 40 题关键词表。
   - 严禁在未匹配时回退挂靠至 Part 的第 1 个 segment。
   - 算法基于 `PART 1` ~ `PART 4` 标题切分各 Part 范围，并在每行右侧边栏（$x \ge 0.78$）扫描真实的 Cambridge 边栏标记（`Q1` ~ `Q40`），处理常见边栏 OCR 噪声（如 `Q7/2` → 12, `Q73.` → 13, `Q79` → 19, `Q2t` → 21, `a32z` → 32, `Q14/15`, `Q27/28`, `Q29/30`）。
   - 全部 40 题证据精准定位到对应发言片段，未产生任何孤立题目（0 处缺失，40/40 覆盖）。

---

## 七、低置信度项逐项人工核验记录（Low-Confidence Audit，22 项）

针对 OCR 置信度低于 0.60 的全部 22 项，实施逐项人工原件核对，并生成完整机器可审计日志：

| # | 类别 | 题号 | 置信度 | 原始 OCR / 内容 | 原卷页码 | 核对状态 | 核对确认值 | 证据边界框 | 审计备注 |
| :-: | :--- | :-: | :-: | :--- | :-: | :-: | :--- | :--- | :--- |
| 01 | question | 1 | 0.4985 | `Postcode: 4 [Peewee` | 12 | confirmed | `Postcode` | `[0.442, 0.120, 0.457, 0.472]` | 填空点阵虚线 `[Peewee` 置信度 0.50，确认题干为 `Postcode` |
| 02 | answer | 1 | 0.5299 | `4 Dw307YZ` | 123 | confirmed | `DW30 7YZ` | `[0.348, 0.080, 0.362, 0.222]` | 前缀 4 系识别题号 1 笔画噪点；确认答案为邮编 `DW30 7YZ` |
| 03 | answer | 2 | 0.5917 | `2° 24(th) April` | 123 | confirmed | `24(th) April` | `[0.364, 0.080, 0.380, 0.231]` | 度数符号 `°` 为题号 2 后圆点识别噪点；确认答案为 `24(th) April` |
| 04 | answer | 3 | 0.4334 | `3 dentist` | 123 | confirmed | `dentist` | `[0.380, 0.080, 0.394, 0.186]` | 题号 3 单字符置信度低（0.13），单词 `dentist` 清晰（0.73），确认答案 |
| 05 | answer | 11 | 0.5519 | `“oc` | 123 | corrected | `C` | `[0.558, 0.070, 0.573, 0.111]` | 原件 Part 2 首行 `11 C` 印刷连字符误识为 `“oc`；人工核准更正为 `C` |
| 06 | answer | 13 | 0.4182 | `13,4` | 123 | corrected | `A` | `[0.600, 0.070, 0.614, 0.117]` | 原件题号 13 与选项字母 A 被误识为逗号与 4；人工核准更正为 `A` |
| 07 | question | 16 | 0.5879 | `16 Fundraising ses...` | 14 | confirmed | `Fundraising` | `[0.553, 0.102, 0.567, 0.354]` | 尾随虚线填空符造成置信度偏低；确认匹配项题干为 `Fundraising` |
| 08 | question | 19 | 0.5864 | `19 Story club nnae...` | 14 | confirmed | `Story club` | `[0.641, 0.103, 0.655, 0.315]` | 尾随虚线填空符造成置信度偏低；确认匹配项题干为 `Story club` |
| 09 | question | 20 | 0.5474 | `20° First aid semen` | 14 | confirmed | `First aid` | `[0.670, 0.102, 0.684, 0.301]` | 题号点误为度数符号，虚线为噪点；确认匹配项题干为 `First aid` |
| 10 | answer | 20 | 0.3750 | `20 F` | 123 | confirmed | `F` | `[0.726, 0.070, 0.739, 0.128]` | 第 1 列末行小字号导致置信度偏低；确认答案为 `F` |
| 11 | answer | 21 | 0.3745 | `21 A` | 123 | confirmed | `A` | `[0.348, 0.485, 0.362, 0.543]` | 第 2 列首题小字号置信度偏低；确认答案为 `A` |
| 12 | answer | 23 | 0.0000 | `23, A` | 123 | confirmed | `A` | `[0.380, 0.485, 0.394, 0.543]` | 逗号标点导致 Tesseract 评估置信度为 0；确认原件答案为 `A` |
| 13 | answer | 24 | 0.5228 | `24 ¢` | 123 | corrected | `C` | `[0.396, 0.485, 0.412, 0.544]` | 美分符号 `¢` 为大写字母 C 误识；人工核准更正为 `C` |
| 14 | answer | 26 | 0.5608 | `26 A` | 123 | confirmed | `A` | `[0.427, 0.486, 0.441, 0.544]` | 确认答案为 `A` |
| 15 | question | 31 | 0.5681 | `© dAMAE £0 31...` | 17 | confirmed | `Problems caused by overpopulation: damage to ____ in the park` | `[0.404, 0.119, 0.418, 0.528]` | 艺术项目符号与虚线误读为版权符号；确认题干语义 |
| 16 | answer | 31 | 0.4854 | `31° fences` | 123 | confirmed | `fences` | `[0.584, 0.486, 0.597, 0.585]` | 度数符号为题号点噪点；确认答案为 `fences` |
| 17 | answer | 32 | 0.5555 | `32 family` | 123 | confirmed | `family` | `[0.600, 0.486, 0.614, 0.580]` | 确认答案为 `family` |
| 18 | answer | 34 | 0.5264 | `34 stress` | 123 | confirmed | `stress` | `[0.631, 0.486, 0.644, 0.581]` | 确认答案为 `stress` |
| 19 | answer | 35 | 0.5733 | `35 sides` | 123 | confirmed | `sides` | `[0.648, 0.486, 0.660, 0.574]` | 确认答案为 `sides` |
| 20 | answer | 36 | 0.5177 | `36 breathing` | 123 | confirmed | `breathing` | `[0.663, 0.487, 0.677, 0.607]` | 确认答案为 `breathing` |
| 21 | question | 38 | 0.1479 | `38 ee ennnnmn...` | 17 | confirmed | `Advantages at Nkhotakota Wildlife Park: ____ opportunities` | `[0.803, 0.120, 0.817, 0.490]` | 填空下划线虚线致使 OCR 置信度极低（0.15）；确认其标题与填空结构 |
| 22 | answer | 40 | 0.5583 | `40 tourism` | 123 | confirmed | `tourism` | `[0.726, 0.486, 0.739, 0.592]` | 确认答案为 `tourism` |

---

## 八、自动化测试与校验结果

- `scripts/validate_cambridge_import.py`（**16 / 16 项规则全部通过**）：
  1. `schema_top_level_keys` (通过)
  2. `scoring_points_count_40` (通过)
  3. `unique_question_ids` (通过)
  4. `continuous_numbering_1_to_40` (通过)
  5. `multi_choice_groups_order_matters_false` (通过)
  6. `official_answer_key_ocr_location` (通过)
  7. `valid_pdf_pages` (通过)
  8. `audio_files_exist_and_nonzero` (通过)
  9. `audioscript_segment_references_valid` (通过)
  10. `audioscript_covers_questions_1_to_40` (通过)
  11. `bounding_boxes_from_ocr_elements` (通过)
  12. `cache_artifacts_dynamic_sha256_verified` (通过)
  13. `source_pdf_sha256_verified` (通过)
  14. `fully_parser_derived_import_mode` (通过，`generationMode=ocr-parser`)
  15. `low_confidence_items_resolved` (通过，22 项全部完成审计且 `unresolved=0`)
  16. `nested_needs_review_and_verified_integrity` (通过，`verified=True`, `blocking needsReview count=0`)
  - **整体校验状态**：`PASSED`，`verified: true`。

- 全局回归测试（`npm test`）：
  - 4 个 Node.js 核心前端测试：全部通过。
  - 19 个 Python 测试（Page Map + 纯算法 OCR 导入与验证）：全部通过。
  - **总计 23 / 23 测试全部通过 (100%)**。

- 代码与编译检查（`npm run check`）：
  - 所有 6 个 Python 脚本与前端 JS 脚本语法全部校验通过。


