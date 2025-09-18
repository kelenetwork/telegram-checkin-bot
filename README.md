# Telegram Auto Check-in Bot

一个功能强大的 Telegram 自动签到机器人，支持多账号多任务管理，具有完善的权限控制系统。

## 功能特性

- 🤖 **多任务支持**: 支持群组签到和 Bot 签到
- 👥 **多账号管理**: 可管理多个签到任务
- 🔐 **权限控制**: 完善的用户授权系统
- ⏰ **定时执行**: 自定义签到时间（上海时区 UTC+8）
- 💬 **Bot 交互**: 通过 Telegram Bot 管理所有任务
- 📊 **任务统计**: 记录签到成功/失败次数

## 一键安装

### 方式一：在线安装（推荐）

```bash
curl -sSL https://raw.githubusercontent.com/kelenetwork/telegram-checkin-bot/main/install.sh | bash


### 方式二：本地安装

```BASH
git clone https://github.com/kelenetwork/telegram-checkin-bot.git
cd telegram-checkin-bot
chmod +x install.sh
./install.sh

安装脚本会自动：

检测您的系统类型
安装必要的系统依赖
安装 Python 3.8+（如果需要）
创建虚拟环境
安装所有 Python 依赖
配置启动脚本
获取必要凭据
在运行机器人之前，您需要获取以下信息：

1. Bot Token
在 Telegram 中找到 @BotFather
发送 /newbot 创建新机器人
获取 Bot Token
2. Telegram ID
在 Telegram 中找到 @userinfobot
发送任意消息获取您的 ID
3. API ID 和 Hash
访问 https://my.telegram.org
使用手机号登录
创建应用获取 API 凭据
快速开始
安装完成后，选择以下任一方式启动：
1. 直接运行
BASH
./start.sh
2. Screen 后台运行
BASH
screen -S telegram-bot
./start.sh
# 按 Ctrl+A 然后 D 分离会话
3. Systemd 服务（推荐）
BASH
sudo systemctl start telegram-checkin-bot
sudo systemctl enable telegram-checkin-bot  # 开机自启
sudo systemctl status telegram-checkin-bot   # 查看状态
使用指南
Bot 命令
基础命令
/start - 开始使用
/help - 显示帮助
任务管理
/add_task - 添加签到任务
/list_tasks - 查看任务列表
/test_task - 测试签到
管理员命令
/add_user - 添加授权用户
/list_users - 查看所有用户
/status - 系统状态
添加签到任务
发送 /add_task
选择签到类型（群组/Bot）
输入目标信息
输入签到命令
设置签到时间
管理用户
BASH
# 添加普通用户
/add_user 123456789

# 添加管理员
/add_user 987654321 admin
常见问题
Q: 安装失败怎么办？
A: 查看错误信息，确保系统有网络连接和 sudo 权限。

Q: 如何查看日志？
A: tail -f bot.log 或 sudo journalctl -u telegram-checkin-bot -f

Q: 如何更新程序？
A:

BASH
git pull
