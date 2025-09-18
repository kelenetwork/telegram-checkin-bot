#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="tg-checkin"
APP_DIR="/opt/tg-checkin"
APP_USER="tgcheckin"
PYTHON_BIN="python3"
PKGS_DEBIAN=("python3" "python3-venv" "python3-distutils" "ca-certificates" "tzdata" "git")
PKGS_RHEL=("python3" "python3-virtualenv" "ca-certificates" "tzdata" "git")

echo "==> TG Auto Checkin 安装程序（需 root）"
if [[ $EUID -ne 0 ]]; then
  echo "请用 root 运行：sudo bash install.sh"; exit 1
fi

# 1) 装系统依赖
install_sys_deps() {
  if command -v apt >/dev/null 2>&1; then
    apt update
    apt install -y "${PKGS_DEBIAN[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y "${PKGS_RHEL[@]}"
  elif command -v yum >/dev/null 2>&1; then
    yum install -y "${PKGS_RHEL[@]}"
  else
    echo "未检测到 apt/dnf/yum，请自行安装 Python3 与 git、tzdata。"
  fi
}
install_sys_deps

# 2) 创建系统用户
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd -r -m -d "$APP_DIR" -s /usr/sbin/nologin "$APP_USER"
fi
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 3) 复制仓库文件到 /opt（假设当前在仓库根目录）
echo "==> 同步仓库到 $APP_DIR"
rsync -a --delete --exclude=".git" ./ "$APP_DIR"/
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 4) 创建并装 venv 依赖
echo "==> 创建虚拟环境并安装依赖（telethon, apscheduler）"
sudo -u "$APP_USER" bash -lc "
  cd '$APP_DIR'
  $PYTHON_BIN -m venv venv
  source venv/bin/activate
  python -m pip install --upgrade pip
  pip install telethon apscheduler
"

# 5) 生成 systemd 服务
echo "==> 写入 systemd 服务：/etc/systemd/system/${SERVICE_NAME}.service"
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=TG Auto Checkin Manager Bot
Wants=network-online.target
After=network-online.target

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=PYTHONIOENCODING=utf-8
# 让应用使用上海时区（调度也在代码中设为 Asia/Shanghai）
Environment=TZ=Asia/Shanghai
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/main.py
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# 6) 首次配置（交互），随后开机自启并启动
echo
echo "==> 首次运行以完成最小配置（api_id/api_hash/bot_token/admin_ids）"
echo "完成后按 Ctrl+C 退出再继续。"
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR'; ./venv/bin/python main.py" || true

echo "==> 启用并启动服务"
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo
echo "✅ 安装完成！"
echo "• 查看日志：journalctl -u ${SERVICE_NAME} -f"
echo "• 修改配置：sudo -u ${APP_USER} nano ${APP_DIR}/config.json  (或用 Bot 菜单)"
echo "• 多账号登录：在 Telegram 里对管理 Bot 发送 /help 然后 /adduser 开始登录流程"
