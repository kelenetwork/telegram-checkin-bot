#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="tg-checkin"
APP_DIR="/opt/tg-checkin"
APP_USER="tgcheckin"
PYTHON_BIN="python3"

# Debian/Ubuntu 所需依赖
PKGS_DEBIAN=(
  python3
  python3-venv
  python3-pip
  ca-certificates
  tzdata
  git
  rsync
  build-essential
  libffi-dev
)

# RHEL 系所需依赖
PKGS_RHEL=(
  python3
  python3-virtualenv
  python3-pip
  ca-certificates
  tzdata
  git
  rsync
  gcc
  make
  libffi-devel
)

echo "==> TG Auto Checkin 安装程序（需 root）"
if [[ $EUID -ne 0 ]]; then
  echo "请用 root 运行：sudo bash install.sh"; exit 1
fi

install_sys_deps() {
  if command -v apt >/dev/null 2>&1; then
    apt update
    apt install -y "${PKGS_DEBIAN[@]}" || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y "${PKGS_RHEL[@]}" || true
  elif command -v yum >/dev/null 2>&1; then
    yum install -y "${PKGS_RHEL[@]}" || true
  else
    echo "未检测到 apt/dnf/yum，请自行安装 Python3、pip、git、tzdata（可选 rsync/build-essential）。"
  fi
}
install_sys_deps


# 创建系统用户
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd -r -m -d "$APP_DIR" -s /usr/sbin/nologin "$APP_USER"
fi
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 同步仓库到 /opt（优先 rsync，缺失时用 cp -a）
echo "==> 同步仓库到 $APP_DIR"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude=".git" ./ "$APP_DIR"/
else
  echo "未找到 rsync，使用 cp -a 回退方案（不支持 --delete）"
  # 删除目标目录下除 .venv/session/配置外的旧文件，尽量模拟 --delete
  find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name 'venv' ! -name '*.session' ! -name 'config.json' ! -name 'accounts.json' ! -name 'tasks.json' -exec rm -rf {} +
  cp -a ./ "$APP_DIR"/
  rm -rf "$APP_DIR/.git" || true
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 创建并装 venv 依赖
echo "==> 创建虚拟环境并安装依赖（telethon, apscheduler）"
sudo -u "$APP_USER" bash -lc "
  cd '$APP_DIR'
  $PYTHON_BIN -m venv venv
  source venv/bin/activate
  python -m pip install --upgrade pip
  pip install telethon apscheduler
"

# 写入 systemd 服务
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
Environment=TZ=Asia/Shanghai
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/main.py
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# 首次配置引导（前台运行一次）
echo
echo "==> 首次运行以完成最小配置（api_id/api_hash/bot_token/admin_ids）"
echo "完成后按 Ctrl+C 退出再继续。"
set +e
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR'; ./venv/bin/python main.py"
set -e

echo "==> 启用并启动服务"
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo
echo "✅ 安装完成！"
echo "• 查看日志：journalctl -u ${SERVICE_NAME} -f"
echo "• 修改配置：sudo -u ${APP_USER} nano ${APP_DIR}/config.json"
echo "• 多账号登录：在 Telegram 里给管理 Bot 发 /help → /adduser 开始登录流程"
