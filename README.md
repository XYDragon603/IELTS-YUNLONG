# IELTS Studio · 雅思模考

剑桥雅思 4–20 真题的网页练习站：单项练习、整套模考、错题复盘、记单词和精听收藏。纯前端，无框架和第三方运行时依赖；本地用一个 Node 服务器运行，线上部署为 Cloudflare 上的私有静态网站。

> **仓库公开，题库不公开。** 原卷、音频和由真题整理的题目数据受版权保护，只保存在本机，不进入 Git；线上站点必须由 Cloudflare Access 保护，只允许名单里的邮箱登录。

## 页面

| 页面 | 内容 |
|---|---|
| `index.html` 首页 | 题库书架、学习概览、目标设置 |
| `practice.html` 单项练习 | 听力、阅读、写作、口语按 Test 练习；可重做 |
| `mock.html` 整套练习 | 按书和 Test 进行完整模考 |
| `review.html` 错题复盘 | 已做题目的对错与解析 |
| `words.html` 记单词 | 词书与同义替换 |
| `listening-clips.html` 精听收藏 | 收藏的听力片段 |
| `import-preview.html` 导入预览 | 检查导入后的题目数据 |

练习功能：
- 听力和阅读自动判分。表格、笔记、流程图、摘要题按原卷版式排成可直接填写的结构。
- 阅读时文章固定，题目区单独滚动；可以高亮文本、记笔记。
- 写作统计词数；口语可以录音、回放和下载。

## 本地运行

需要 Node.js 20 或更新版本，以及本地资料（见下文）。在项目目录运行：

```sh
npm start
```

然后打开 http://localhost:4173 。Windows PowerShell 若禁止运行 `npm.ps1`，改用 `npm.cmd start`。不要直接双击 HTML，模块加载和麦克风都需要通过服务器访问。

## 目录结构

```
frontend/   网页根目录：页面 HTML、样式、字体；features/ 页面逻辑，ui/ 界面组件，lib/ 浏览器端模块，data/ 资源索引
backend/    server.js 本地服务器与题库接口；lib/ 服务端模块；scripts/ 导入、校验、构建、上传脚本
functions/  Cloudflare Pages Function：从 R2 读取 /IELTS/ 下的原卷与音频
resources/  题库与词书数据（版权部分只在本机）
tests/      Node 与 Python 单元测试、浏览器端到端测试
docs/       设计、数据导入、复核与部署记录
```

### 只在本机、不进仓库的资料

以下内容见 `.gitignore`：
- `IELTS/`：原版 PDF、音频和视频；
- `WORD/`：词书原始资料；
- `resources/cambridge/`：由真题整理的题目数据、版式和图片；
- `resources/words/`、`resources/synonyms/`、`resources/page-maps/`；
- `dist/`：构建产物，里面含有题库内容；
- 少数内嵌题干的修复脚本。

新克隆的仓库需要自己放入原始资料，再用 `backend/scripts/` 里的导入脚本生成数据。缺少这些资料时，依赖题库数据的测试会失败。

## 线上部署（Cloudflare，私有）

线上网站全部托管在 Cloudflare，本机关机也能访问：

| 内容 | 放在哪里 |
|---|---|
| 网页、题库 JSON、题目图片（约 800 个文件，100 MB） | Cloudflare Pages，项目名 `ielts-studio` |
| 题库目录 | 构建时生成为静态文件 `/api/catalog.json` |
| 原卷 PDF、听力音频（156 个文件，3.4 GB） | R2 存储桶 `ielts-media`，由 `functions/IELTS/[[path]].js` 按原路径读取，支持拖动进度 |
| 登录 | Cloudflare Access：名单内邮箱通过一次性验证码登录 |

更新网站：

```sh
npm run upload:media   # 有新的原卷或音频时：只上传新增文件
npm run deploy:pages   # 改了页面、代码或题库后：重新构建 dist/ 并发布
```

- 两样都改了时，先运行 `upload:media`，再运行 `deploy:pages`。
- 命令提示未登录时，先运行 `npx wrangler login`。
- 加人、删人不需要运行命令，在 Cloudflare Zero Trust 的 Access 策略里修改邮箱名单即可。
- 发布有问题时，可以在 Pages 控制台的 Deployments 里回滚到之前的版本。

首次部署步骤、上传范围和限制见 [docs/CLOUDFLARE_DEPLOY.md](docs/CLOUDFLARE_DEPLOY.md)。

## 数据保存

练习记录、生词本和笔记保存在浏览器的 localStorage，录音保存在 IndexedDB。这些数据都不上传服务器，所以换浏览器或换设备不会同步；清理浏览器数据会把它们一起删掉。

## 验证

```sh
npm run check   # 语法检查
npm test        # Node 与 Python 单元测试
```

浏览器端到端测试（`tests/*.mjs`）使用本机 Chrome 和原生 CDP。运行前先 `npm start`，再执行例如 `node tests/practice-browser.mjs`。截图写入 `artifacts/`。

## 题库导入

Cambridge PDF 的导入分几步：
1. 生成页码映射（`npm run import:page-maps`）；
2. 按「一个 Test + 一个科目」提取题目，写成独立 JSON；
3. 校验，并与原卷做人工或辅助的视觉核对。

全程不使用 LLM 生成题目内容。有文字层的 PDF 直接提取文字，没有文字层时才调用本机 Tesseract OCR。

导入和复核的进度、方法记录在 [docs/DATA_IMPORT_PROGRESS.md](docs/DATA_IMPORT_PROGRESS.md) 及 `docs/` 下的各份审计记录中。
