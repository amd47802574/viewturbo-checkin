# ViewTurbo 每日自动签到

GitHub Actions 定时任务，每天自动签到领 100MB 流量。

## 原理

| 步骤 | 接口 | 方法 |
|------|------|------|
| 登录 | `POST /appuser/reglogin` | `{"email":"…","password":"<MD5>"}` |
| 签到 | `POST /appuser/checkin` | `{}` |

- API 域名：`api.viewturbo.info`（多域名自动降级）
- 密码前端 MD5 加密后传输
- 认证靠 `token` query 参数

## 配置

仓库 Secrets 已设置：
- `VT_EMAIL` — 登录邮箱
- `VT_PASSWORD` — 登录密码（明文，脚本自动 MD5）

## 手动触发

在 GitHub 仓库 → Actions → ViewTurbo Daily Checkin → Run workflow

## 执行时间

每天 UTC 00:00（北京时间 08:00）自动执行。