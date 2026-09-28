# 第二次复查 · 2026-09-25

本次重新运行全量审计及测试，并直接核查当前代码和全部听力证据引用。

- 当前 C15、C16、C18、C19、C20 各 4 个 Test，共 80 份四科数据。
- `python artifacts/import-audit/audit.py`：TOTAL 80 FAIL 0 ISSUES 0。
- 800 道听力题的证据页码均在所引用 audioscript segment 的来源页集合内。
- 80 份均 verified:false，结构校验通过不代表内容已核验。
- `npm.cmd test`：34 项 Node 测试及 54 项 Python 测试通过；`npm.cmd run check` 通过。
- 前次要求的阅读正文入口检查、按词数统计、听力范围检查、缺少证据页码不再回退到题目页，均已加入代码。

## 仍存在的验证器漏洞

`scripts/validate_cambridge_import.py` 对 ocr-assisted-curation 的校订记录只检查 reviewMethod 枚举、坐标数组长度为 4、sourcePdfPage 非空；没有校验页码真实范围和坐标值/顺序。

本次只在内存中替换 C18 T1 的 curations.json 读取结果，将其中 60 条听力校订记录改为 sourcePdfPage=999999、evidenceBoundingBox=[-5,2,9,-1]。原文件没有写入或修改。验证器仍返回整体 PASSED，fully_parser_derived_import_mode 也通过。

因此这项修复只能算部分完成。应补充真实页数范围、数值类型、归一化坐标与先后顺序检查，并加入该反例测试。此反例说明检查能力不足，不表示实际题库包含上述注入值。

本次未进行逐页视觉内容验收或声音听辨；不应将题库转为 verified:true。

## 进一步检查发现的实际数据问题

独立检查全部 1560 条听力校订记录的页码和坐标边界后，发现 **C15 的 46 条记录坐标不符合约定的 [ymin,xmin,ymax,xmax]**：T1 10 条、T2 10 条、T3 16 条、T4 10 条。

例如 C15 T1 Q31 的 evidenceBoundingBox 为 [0.46,0.488,0.475,0.22]，xmax=0.22 小于 xmin=0.488，区域左右颠倒。这是实际文件中的值，不是反例注入值。应依据来源图像重新确认，不能直接交换数值后宣称已核验。

明细：`artifacts/import-audit/invalid-curation-bounds.json`。因此当前自动审计的 ISSUES 0 存在漏检，不能作为所有来源坐标正确的证明。
