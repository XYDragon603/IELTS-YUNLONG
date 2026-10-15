# 部署到 Cloudflare（无服务器，私有访问）

本站核心内容是剑桥雅思原卷、音频和精讲材料，**只能私有部署**：整个域名必须先由 Cloudflare Access 保护，只有你允许的邮箱能打开。不要在 Access 配好之前上传任何内容，也不要开启 R2 的公开访问。

## 架构

| 内容 | 放在哪里 | 说明 |
|---|---|---|
| 页面、代码、题库 JSON、题目图片（约 100 MB，800 个文件） | Cloudflare Pages | `npm run build:static` 生成 `dist/` |
| 题库目录 `/api/catalog.json` | Pages 静态文件 | 构建时由 `backend/lib/catalog-server.js` 生成，新增题库后重新构建 |
| `/IELTS/…` 原卷 PDF、听力音频、视频 | R2 存储桶 `ielts-media` | 由 `functions/IELTS/[[path]].js` 按原路径读取，支持 Range，音频可拖动 |
| 访问控制 | Cloudflare Access | 保护整个域名，包括媒体 |

练习记录、生词本、录音仍保存在各自浏览器的本地存储中，换设备不会同步。

## 第一次部署

1. **登录**：`npx wrangler login`（会打开浏览器授权 Cloudflare 账号）。
2. **建 R2 存储桶**（不要开启公开访问）：`npx wrangler r2 bucket create ielts-media`
3. **建 Pages 项目并先部署一次**：`npm run deploy:pages`（项目名取自 `wrangler.toml`，为 `ielts-studio`）。`ielts-studio.pages.dev` 已被占用，Cloudflare 分配的是 `https://ielts-studio-1sh.pages.dev`，并绑定了自定义域名 `https://ielts.xydragon.com`。Access 应用需覆盖这两个域名及 `*.ielts-studio-1sh.pages.dev` 预览地址。
4. **立刻开启 Access**：Cloudflare 控制台 → Workers & Pages → `ielts-studio` → Settings → 开启 *Access policy*（保护 `*.pages.dev` 及预览地址）。然后在 Zero Trust → Access → Applications 里把策略设为 *Include: Emails = 你的邮箱*，登录方式用一次性邮箱验证码（One-time PIN，免费）。
5. **验证 Access 生效**：用无痕窗口打开站点，应先出现 Cloudflare 登录页。
6. **上传媒体**：
   - `npm run upload:media -- --dry-run`：先看清单。默认是在线题库用到的原卷与音频，共 156 个文件，约 3.4 GB，在 R2 免费额度内。
   - `npm run upload:media`：上传。中断后重跑会跳过已上传的文件，记录在 `.cache/r2-uploaded.json`。
   - 如果连精讲 PDF 和视频也要上传，用 `-- --all`（约 8 GB）。其中两份 473 MB 的精讲 PDF 超过 wrangler 单文件上限，需要用 rclone 等 S3 兼容工具单独上传，或者不上传。
7. **自定义域名（可选）**：Pages → Custom domains 绑定域名，并在 Access 应用里加上该域名。

## 之后更新

- **改了代码或题库**：`npm run deploy:pages`
- **新增了原卷或音频**：`npm run upload:media`

## 本地验证

- `npm run build:static` 会检查单文件是否超过 25 MiB、文件总数是否超过 20,000。
- `tests/r2-media-function.test.js` 用模拟的 R2 检查 Range 请求、HEAD 请求、404 和路径越界。
- `dist/` 已在 `.gitignore` 中，因为它包含原卷内容，绝不能提交到公开仓库。
