# IELTS Studio 部署到 ielts.xydragon.com

目标是让所有人通过 `https://ielts.xydragon.com` 访问。当前项目由 Node 服务提供网页、题库 JSON、原卷 PDF 与音频；发布后，这些 PDF 与音频也会公开可访问。上线前需确认你拥有相应的公开分发权限。用户的练习记录仍只存在各自浏览器中。

## 部署前

1. 在项目目录运行 `npm.cmd test`、`npm.cmd run check`，再运行 `npm.cmd start`。
2. 在本机打开 `http://127.0.0.1:4173/`，检查题库、整套练习、音频与原卷链接。
3. 确认 `xydragon.com` 已由同一个 Cloudflare 账户管理。不要把 Tunnel token、账户密钥或个人复核导出文件放进项目目录。

## 建立公开子域名

1. 在 Cloudflare Zero Trust 的 **Networks → Connectors → Cloudflare Tunnel** 创建 remotely-managed Tunnel，例如 `ielts-studio`，选择 Windows 连接器。按控制台提供的命令安装 `cloudflared`；管理员终端执行其 `cloudflared.exe service install <TUNNEL_TOKEN>`。不要把实际 token 贴到聊天或保存到仓库。
2. 给 Tunnel 添加 published application route：Hostname `ielts.xydragon.com`，Service type `HTTP`，Service URL `http://127.0.0.1:4173`。Cloudflare 控制台会为该主机名建立/提示 CNAME，目标为 Tunnel 的 `<UUID>.cfargotunnel.com`。若没有自动建立，在 DNS 记录中添加 Name `ielts`、Target `<UUID>.cfargotunnel.com` 的 CNAME。
3. 不给这个主机名添加 Cloudflare Access 登录限制，网站即对所有人开放。不要在同一子域名下托管管理页面、复核 CSV 或其他私人文件。
4. 保持 `node server.js` 运行。若希望电脑重启后仍能访问，可用 Windows 任务计划程序开机启动 `node.exe`，参数为 `E:\Desktop\IELTS Mock Exam\server.js`，工作目录为 `E:\Desktop\IELTS Mock Exam`。电脑关机或离线时网站不可用；长期稳定运行可把项目迁到始终在线的服务器后保持同一 Tunnel 配置。

## 上线核验

- 用未登录的浏览器打开 `https://ielts.xydragon.com/`，应能直接看到首页。
- 检查首页、`/mock.html`、`/words.html`、`/api/catalog`，并分别播放一段 MP3、打开一个 PDF。口语麦克风需要 HTTPS 或 localhost；子域名应使用 HTTPS。
- 检查 `/artifacts/pending-review-items.csv`、`/scripts/export-review-items.mjs`、`/WORD/` 均返回 404。服务器只对外提供网页运行所需文件以及题库 PDF、音频和图片。
- 练习数据仍保存在每个浏览器的 localStorage/IndexedDB。子域名与 localhost 不是同一存储来源，旧进度不会自动迁移；切换设备也不会同步。

官方文档：[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/)、[Published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)、[Access 自托管应用](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)、[Tunnel DNS 记录](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/)。
