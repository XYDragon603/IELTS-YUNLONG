# IELTS Studio · 雅思模考

响应式网页原型，无框架和第三方运行时依赖。使用原创学术类缩减示例卷，跑通听力、阅读、写作、口语及复盘流程。

## 启动

需要 Node.js 20 或更新版本。在项目目录运行：

```sh
npm start
```

Windows PowerShell 若禁止运行 npm.ps1，使用 `npm.cmd start`，也可直接运行 `node server.js`。

浏览器打开 http://localhost:4173 。不要直接双击 HTML；模块加载与麦克风需要本地服务器。手机远程访问时需要另行部署到 HTTPS 网站；当前开发服务器仅监听本机。

## 已实现

- 学习概览、目标设置、四科单项练习、完整模考、练习历史。
- 听力 5 分钟 / 阅读 8 分钟 / 写作 10 分钟 / 口语 3 分钟，均为缩减体验时长。
- 答案自动保存、刷新恢复、暂停继续、题目标记、题号跳转、到时自动提交当前科目。
- 提交后下一科等待点击继续；离开考试页会暂停，关闭或刷新考试页不会额外延长计时。
- 听力合成英文语音及文字稿后备；听读自动判题与解析。
- 写作英文词数、作文保存；口语麦克风录音、回放和下载。
- 历史复盘、纯文本报告导出。录音需在报告页单独下载。

文字进度保存在 localStorage，录音保存在 IndexedDB。清理浏览器数据会删除这些内容；不跨设备同步。录音过程中刷新或关闭页面可能丢失当前音频，请先结束录音。

## 范围

当前只包含一套原创 Academic 示例题，并非完整官方题库。听读只显示答对题数，不按短卷比例推算 Band；写作、口语没有接入 AI 或人工评分。首页无虚构练习数据。不包含账户、后端、支付或 General Training 题目。

## 验证

```sh
npm run check
npm test
```

`tests/browser-check.mjs` 使用本机 Chrome 与原生 CDP，执行桌面和移动布局、完整模考、进度恢复、录音模拟、计时提交及导出检查。先启动开发服务器，再运行 `node tests/browser-check.mjs`。该测试会启动隔离的无头 Chrome，使用模拟麦克风，并把截图写入 `artifacts/`，不验证真实硬件录音质量。

## Cambridge PDF Importer

Importer 分三阶段执行，当前只实现第一阶段 `PDF → page map`。它不会修改原 PDF，也不会立即解析所有题目。

剑雅 18：

```sh
npm run import:page-map:c18
```

任意一本：

```sh
python scripts/cambridge_pdf_importer.py page-map --book 19 --pdf "IELTS/你的文件.pdf" --output "resources/page-maps/cambridge-19.json"
```

处理规则：

- 先检测每页是否有可用文字层；有文字层时直接提取。
- 无文字层时才调用本机 Tesseract OCR，全程不使用 LLM。
- 首次 OCR 的页面文本保存在 `.cache/cambridge-importer/`，该目录被 Git 忽略；JSON 只保存章节页码和短标题证据。
- 输出同时记录书上印刷页码和从 1 开始的 PDF 页码。无法可靠推断的页码会保留为 `null`，不会猜测。
- `needsReview` 为空表示识别到了四套 Test 的 Listening、Reading、Writing、Speaking 共 16 个区间；这仍是结构检测结果，不代表题目已经转录。

已验证结果位于 `resources/page-maps/cambridge-18.json`。后续阶段应按一个 Test + 一个 Skill 读取该范围，再输出独立 JSON；不要把整本 OCR 文本加入应用数据或模型上下文。
"# IELTS-YUNLONG" 
