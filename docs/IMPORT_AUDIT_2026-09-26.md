# Cambridge C12–20 题库复查与修复

范围：C12–C20 共 9 册、每册 4 个 Test、每 Test 四科，共 144 份结构化 JSON。本次保留所有原始 PDF、音频与其他 `IELTS/` 文件。

## 修复

1. C15 T1–T4 共 46 条听力答案校订坐标曾出现 xmax < xmin。`scripts/repair_c15_curation_boxes.py` 从四册对应原卷答案页以本地 Tesseract 240 DPI 定位题号与答案行，重新填写 `curations.json` 与听力题目的 answer.boundingBox。旧文件原样备份至忽略目录 `.cache/cambridge-importer/c15-curation-box-backup/`。仅修复来源区域；保留原来的答案和内容复核状态。
2. 听力验证器新增校订页码必须在真实 PDF 范围内、坐标必须是 0–1 内且有序的检查；题目的答案框也做相同校验。反例测试覆盖越界页码及倒置框。
3. C13 T1 阅读 Q27–31 原先五道题没有题干、选项、题组说明。对照原卷 PDF 第 29 页文字层和页面图像，补充五题题干、各题四个独立选项、题组说明及来源题号坐标。保留 `verified:false` 和 assistant-visual 待复核标记。前端阅读控件现在支持题目层选项。
4. 阅读验证器及题库入口拒绝没有题干且缺少题组说明/图片的题组，防止同类空题进入练习。
5. C12/C17 已有可用原卷和 page map；更新早期将两册视为缺失的测试，以及旧听力检查项数量断言。`resources/import-report.json` 的 `totalExpectedSections` 从历史 240 改为当前 17 册 × 4 Test × 4 科的 272。C18 T1 听力补齐与 verified:false 一致的 `status: needs-review`，其导入脚本同步生成此字段。

## 验证

- `python artifacts/import-audit/audit.py`：**TOTAL 144 FAIL 0 ISSUES 0**。
- 36 套听力 1,440 题、36 套阅读题号与答案映射完整。2,840 条听力校订记录的页码和坐标边界再次检查：0 条无效；阅读正文无空篇，写作两题题干无空值。
- 前端目录可读取 144 份数据，36 套听力适配器均可读取；没有 unavailable 条目。
- `npm.cmd test`：34 项 Node 测试和 56 项 Python 测试通过；`npm.cmd run check` 通过。
- `node tests/c13-reading-browser.mjs`：真实浏览器确认 C13 T1 Q27–31 题干和独立选项可见、可选。

全部 144 份数据仍为 `verified:false`、`needs-review`。这些检查验证数据结构、来源范围及页面可用性，尚未逐页人工校对全部题目、答案和声音内容。
