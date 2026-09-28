# IELTS-Studio 风格改造

参考本地 `IELTS-Studio/frontend/src/assets/main.css`、首页与考试页代码，以及 `docs/images/preview-reading1.png`。在现有原生 JS 项目中实现相近的暖白、深绿、圆角卡片与紧凑机考布局，未迁移 Vue / Spring Boot，也未改参考仓库。

## 已实现

- 首页使用顶部导航与四科入口；示例体验放到页脚，阅读、写作、口语直接打开本地 C18 T1。
- 三科练习页顶部显示试卷、计时与提交；资料异常仍可查看，阅读工具及历史折叠。
- 桌面端文章和题目独立滚动，题目使用独立卡片和输入焦点边框。
- 阅读答题卡显示实际已导入题数、完成状态与标记；点击题号可跨 Passage 跳转并聚焦输入框，手机自动切换题目面板。
- 原文显示时自然换行，保留源文本与高亮偏移；已有独立题干的题组将重复上下文折叠，无题干时继续显示上下文。
- 草稿键、历史快照、录音存储沿用原实现。

## 文件

`studio.css`、`exam-workspace.css`、`ui/studio-home.js`、`lib/exam-workspace.js` 为主要新增文件；入口与现有渲染函数接入这些模块。

## 范围与后续

这次是首页和三科练习页的第一轮改造。听力内部界面、题库的文件资源区和复盘页仍需继续统一。参考项目中的 AI 翻译、写作批改与词库服务尚未接入；没有创建不可用的 AI 按钮。

未修改资料导入脚本、题库 JSON、OCR 缓存或 IELTS 原件。识别错误仍由资料整理流程处理，界面改造不代表题目内容已核验。

前端浏览器测试新增桌面双栏、答题卡跨文章跳转、手机首页检查，保留写作与口语回归。旧版示例流程测试通过页脚对应的专项练习路由开始；首页不再显示 Band 目标卡，因此移除该首页目标卡断言，继续覆盖完整四科示例流程。

验证结果：`node --test tests/*.test.js` 14 / 14 通过；`node tests/practice-browser.mjs` 和 `node tests/browser-check.mjs` 均通过。桌面及手机截图见 `artifacts/studio-home-desktop.png`、`artifacts/studio-home-mobile.png`、`artifacts/studio-reading-desktop.png`。
