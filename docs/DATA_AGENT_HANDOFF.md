# 资料整理 agent 执行任务

请在当前 IELTS Studio 项目继续整理本地 Cambridge IELTS 4–20 题库。另一位 agent 正在实现前端，请严格按以下分工执行。

## 文件分工

你负责 scripts/ 下的导入和数据验证代码、tests/test_*.py、resources/cambridge/、resources/page-maps/、resources/import-*.json，以及 .cache/ 本地缓存。可以新增 docs/DATA_IMPORT_PROGRESS.md 记录进度。

不要修改 app.js、core.js、lib/、features/、ui/、HTML、CSS、package.json、tests/*.js、tests/*.mjs 或此交接文件。需要新增 npm 命令时仅在进度文档列出。原始 IELTS/ 内任何文件不得移动、改名、覆盖或删除。

## 当前接手点

已有 backend/scripts/import_cambridge_skills.py、backend/scripts/skill_parsers.py，C18 T1 reading.json / writing.json / speaking.json 及 assets/ 已首次生成，均待复核。此前导入被中断，不能把已生成文件视为完整交付。

特别注意：reading.json 上一次生成时把“Reading Passage 2 has seven paragraphs”误判为文章标题，造成重复 passage 和题组缺失。skill_parsers.py 已将文章标题正则改为整行匹配，但 reading.json 尚需重新生成、确认三篇文章与全部40题。

阅读 PDF 18–32 页夹有疑似推广页21和23，必须核对后排除。答案页124已做分栏 OCR，仍有不确定答案。写作33–34页，口语35页。写作图表、阅读表格及口语话题卡已有局部 PNG 裁剪。

Listening 的“纯算法已验证”旧报告已被审计推翻。脚本仍有按题号返回固定题干/答案的分支，复核说明也在脚本内。人工校订可使用，但应移入独立、可追溯校订记录，不得伪装成 OCR 直接结果。

## 优先顺序

1. 完成 C18 T1 阅读、写作、口语，逐项修复校验失败；阅读必须3篇文章、题号1–40且不重复。
2. 完成 C18 T1 Listening 的来源复核与可重复生成。
3. 用 C18 T2 验证四科导入器的通用性，不能只改册次后复用固定题号/答案。
4. 逐册逐Test逐科扩展。C12/C17先重新核查文件是否仍为0字节，缺失则记录并跳过；C20采用per-test PDF来源。

## 本地与节省 token

基础提取只用本地 Python/Node。每页先检测可靠文字层，没有可靠文字层再用 Tesseract。复用带源PDF SHA-256、工具版本、DPI的缓存。一次处理一个 Test + Skill。不要把整本书、整套缓存或大量题目打印给模型；只输出进度与异常片段。LLM只处理确有必要的小题组/单页疑难内容。

无法确定的字段写null，加入needsReview。不要用题意推测答案，不要给缺失题号强行挂靠证据，不要自动生成“人工已确认”。真实校订需记录原值、修正值、来源页、截图区域、对应OCR文件哈希、复核方式（human或assistant-visual）与依据。不得声称助手复核为人工复核。

## 前端数据契约（schemaVersion: 1）

每套资源位于 resources/cambridge/c18/test-1/ 等目录；四科文件分别为 listening.json、reading.json、writing.json、speaking.json，图片置于 assets/。

共同字段：schemaVersion、id、book、test、skill、variant、verified、status、sources、needsReview。
status为ready / needs-review / missing-resource。sources.paper至少有path与sha256；source字段保留pdfPage、printedPage、method、lineIds、boundingBox、confidence。坐标格式明确为[ymin,xmin,ymax,xmax]，0–1。未知置信度为null。

阅读：
- passages数组，每篇有number、title、blocks:[{text,source}]、groups。
- group有id、questionRange:[start,end]、type、context（完整题组指令与上下文）、options:[{value,label,source}]、questions；可选asset对象。
- question有id（q1等）、number、prompt（未知可null）、source、answer:{accepted:[字符串]或null,source,needsReview}、needsReview。
- 顶层answerKey按题号索引。同一答案与question.answer保持一致。
- 表格/摘要填空无法抽取独立题干时，保留完整group.context/asset，不要编造prompt。

写作：tasks数组，每项有id、number（1/2）、type、prompt、minimumWords、source、assets数组、sampleAnswer（无则null）、needsReview。图表直接裁剪原PDF，不重画。

口语：parts数组，每项有part（1/2/3）、type、source、topics:[{title,questions:[{text,source}]}]、needsReview。
Part2增加cueCard:{text,source,asset}；可保留instructionText。Part1/3可保留context。

asset对象：{asset:"./assets/name.png",alt,sourcePdfPage,boundingBox,width,height,sha256}。

Listening保持现有格式。多选组保留numbers及orderMatters:false；不得把同一组重复算分。

如需改变以上格式，先写迁移说明，保持兼容字段，不能直接改前端文件。

## 验证与交付

校验真实PDF页数、源文件/缓存/图片哈希、图片存在、题号唯一、题目/答案关联、录音稿引用与原文对应。验证器必须打开证据文件核对，不能只检查字段存在或generationMode字符串。增加错误输入测试：缺题、重复题、错误答案来源、错误哈希、未复核项目应被发现。

先运行每科导入与验证，再运行 npm.cmd test 和 npm.cmd run check。测试通过不等于内容已验证。仍有关键needsReview时禁止verified:true。不要为了绿灯删除复核项或改写断言掩盖问题。

交付 docs/DATA_IMPORT_PROGRESS.md：每科状态、真实题数、答案确认数、复核项、执行命令、未解决问题。首先把C18 T1四科做完整，再批量推进；持续执行，不要只给计划。
