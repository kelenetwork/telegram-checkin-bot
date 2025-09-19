# Telegram Checkin Bot

一个基于 **Telethon** + **Apscheduler** 的 **Telegram 自动签到机器人**。  
支持使用 **个人账号** 完成签到，而不是 Bot API 直接发消息。  

## ✨ 功能特点

- 🤖 **Bot 管理**：所有任务和账号管理都通过一个 Bot 完成
- 👥 **多账号支持**：可同时登录多个 Telegram 个人号
- ⏰ **灵活定时**：基于 Cron 表达式（上海时区）
- 📝 **任务备注**：每个任务可带备注，方便区分
- 📊 **状态监控**：随时查看账号实时状态（在线/离线/最近上线）
- 🔐 **独立运行环境**：自动创建虚拟环境，依赖与系统隔离
- ⚙️ **一键部署**：`install.sh` 安装并注册 systemd 服务，开机自启
- 📦 **干净卸载**：`uninstall.sh` 移除服务与数据

---

## 🚀 安装部署

### 1. 克隆仓库
```bash
git clone https://github.com/kelenetwork/telegram-checkin-bot.git
cd telegram-checkin-bot
```

### 2. 一键安装
```bash
sudo bash install.sh
```

脚本会完成：
- 安装系统依赖（Python3/venv/tzdata/git 等）
- 创建运行用户 `tgcheckin`
- 部署到 `/opt/tg-checkin`
- 创建虚拟环境并安装 `telethon`、`apscheduler`
- 注册 `systemd` 服务，开机自启
- 首次运行 `main.py` 引导你输入：
  - `api_id` / `api_hash`（[my.telegram.org](https://my.telegram.org) 申请）
  - 管理 Bot 的 `bot_token`（@BotFather 获取）
  - 管理员账号 ID（可在 [@userinfobot](https://t.me/userinfobot) 查询）

---

## 🛠 管理脚本

仓库提供 `manage.sh`，简化日常管理：

```bash
bash manage.sh start     # 启动服务
bash manage.sh stop      # 停止服务
bash manage.sh restart   # 重启服务
bash manage.sh status    # 查看状态
bash manage.sh logs      # 实时日志
bash manage.sh edit      # 编辑 config.json
bash manage.sh update    # 从仓库更新到 /opt 并重启
```

---

## 📖 使用说明

在 Telegram 中，用管理员账号向管理 Bot 发送命令。

### 账号管理
```
/adduser 别名 | +8613800138000     # 添加账号（会发送验证码到手机）
/code 别名 | 12345                 # 输入验证码
/pass 别名 | 二步验证密码           # 如需要
/listusers                         # 列出已登录账号
/removeuser 别名                   # 移除账号
```

### 任务管理
```
/addtask 目标 | CRON | 文本 | 账号别名 | 备注
  示例: /addtask @MyCheckinBot | 0 9 * * * | /checkin | myA | 早安签到

/listtasks                         # 列出任务
/deltask ID                        # 删除任务
/toggle ID                         # 启用/停用任务
/test 目标 | 文本 | 账号别名        # 立即测试一次
```

### 状态与查询
```
/status                            # 查看所有账号状态
/me 别名                           # 查看某个账号信息
/whois 目标                        # 解析目标信息
```

---

## ⏱ CRON 表达式

所有定时任务使用 **上海时区 (Asia/Shanghai)**，示例：
- `0 9 * * *` → 每天早上 09:00  
- `*/10 * * * *` → 每 10 分钟执行一次  

---

## 🗂 数据目录

服务安装路径：`/opt/tg-checkin`  

- `main.py`：主程序  
- `config.json`：全局配置  
- `accounts.json`：账号清单（别名 → session 文件）  
- `tasks.json`：任务配置  
- `user-<alias>.session`：个人账号会话  
- `bot.session`：Bot 会话  

---

## 🧰 常见问题

1. **数字 ID 无法发送消息？**  
   - 需确保你的个人号与该对象有过会话；  
   - 否则请使用 `@用户名` 或 `t.me/链接` 或 `-100` 开头的群/频道 ID。

2. **服务日志在哪里看？**  
   ```bash
   journalctl -u tg-checkin -f
   ```

3. **修改配置后如何生效？**  
   - 用 `manage.sh restart` 重启服务。

---

## ❌ 卸载

```bash
sudo bash uninstall.sh
```

会移除 systemd 服务，删除 `/opt/tg-checkin` 与用户 `tgcheckin`。  
如要保留数据，可手动备份 `config.json / tasks.json / accounts.json / *.session`。

---

## 📜 License

MIT
