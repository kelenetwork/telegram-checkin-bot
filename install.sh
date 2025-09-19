#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="tg-checkin"
APP_DIR="/opt/tg-checkin"
APP_USER="tgcheckin"
PYTHON_BIN="python3"

echo "==> TG Auto Checkin 安装程序（需 root）"
if [[ $EUID -ne 0 ]]; then
  echo "请用 root 运行：sudo bash install.sh"; exit 1
fi

# 检测 Python 主次版本，例如 3.13
PY_MAJMIN="$($PYTHON_BIN -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
PY_VENV_PKG="python${PY_MAJMIN}-venv"   # 例如 python3.13-venv

# 基础依赖（不再安装 python3-distutils）
PKGS_DEBIAN=("python3" "ca-certificates" "tzdata" "git" "rsync")
PKGS_RHEL=("python3" "ca-certificates" "tzdata" "git" "rsync")

install_sys_deps() {
  if command -v apt >/dev/null 2>&1; then
    apt update
    apt install -y "${PKGS_DEBIAN[@]}" || true
    # 安装与当前 python3 匹配的 venv 包（例如 python3.13-venv）
    apt install -y "$PY_VENV_PKG" || apt install -y python3-venv || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y "${PKGS_RHEL[@]}" || true
    dnf install -y python3-virtualenv || true
  elif command -v yum >/dev/null 2>&1; then
    yum install -y "${PKGS_RHEL[@]}" || true
    yum install -y python3-virtualenv || true
  else
    echo "未检测到 apt/dnf/yum，请自行确保已安装：Python3、tzdata、git（可选 rsync）。"
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
  find "$APP_DIR" -mindepth 1 -maxdepth 1 \
    ! -name 'venv' \
    ! -name '*.session' \
    ! -name 'config.json' \
    ! -name 'accounts.json' \
    ! -name 'tasks.json' \
    -exec rm -rf {} +
  cp -a ./ "$APP_DIR"/
  rm -rf "$APP_DIR/.git" || true
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 创建 venv 并安装依赖（失败则用 virtualenv 兜底）
echo "==> 创建虚拟环境并安装依赖（telethon, apscheduler）"
sudo -u "$APP_USER" bash -lc "
  set -e
  cd '$APP_DIR'
  if ! $PYTHON_BIN -m venv venv 2>/dev/null; then
    echo 'python -m venv 失败，尝试使用 virtualenv 兜底……'
    $PYTHON_BIN -m pip install --user --upgrade pip || true
    $PYTHON_BIN -m pip install --user virtualenv || true
    $PYTHON_BIN -m virtualenv venv
  fi
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

# 首次配置引导（前台一次，Ctrl+C 后继续）
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
echo '✅ 安装完成！'
echo "• 查看日志：journalctl -u ${SERVICE_NAME} -f"
echo "• 修改配置：sudo -u ${APP_USER} nano ${APP_DIR}/config.json"
echo "• 多账号登录：在 Telegram 里给管理 Bot 发 /help → /adduser 开始登录流程"
