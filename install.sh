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

# 首次配置引导（在服务启动之前完成）
echo
echo "==> 首次运行以完成基础配置"
echo "需要配置以下信息："
echo "1. api_id 和 api_hash（从 https://my.telegram.org 获取）"
echo "2. bot_token（从 @BotFather 获取）"
echo "3. 管理员用户ID（可从 @userinfobot 查询）"
echo

# 检查是否已有配置文件
if [[ -f "$APP_DIR/config.json" ]]; then
  echo "检测到已有配置文件，跳过首次配置。"
  echo "如需重新配置，请删除 $APP_DIR/config.json 后重新安装。"
else
  echo "开始交互式配置..."
  # 设置一个超时，避免无限等待
  timeout 300 sudo -u "$APP_USER" bash -lc "cd '$APP_DIR'; ./venv/bin/python main.py" || {
    echo "配置超时或被中断。"
    if [[ ! -f "$APP_DIR/config.json" ]]; then
      echo "❌ 配置未完成！请手动配置或重新运行安装脚本。"
      echo "手动配置方法："
      echo "1. sudo -u $APP_USER nano $APP_DIR/config.json"
      echo "2. 参考格式："
      echo '   {
     "api_id": 你的api_id,
     "api_hash": "你的api_hash",
     "bot_token": "你的bot_token",
     "admin_ids": [你的用户ID]
   }'
      exit 1
    fi
  }
fi

# 验证配置文件是否完整
if [[ -f "$APP_DIR/config.json" ]]; then
  echo "==> 验证配置文件..."
  config_check=$(sudo -u "$APP_USER" python3 -c "
import json
import sys
try:
    with open('$APP_DIR/config.json', 'r') as f:
        cfg = json.load(f)
    required = ['api_id', 'api_hash', 'bot_token', 'admin_ids']
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        print(f'缺少配置项: {missing}')
        sys.exit(1)
    print('配置文件验证通过')
except Exception as e:
    print(f'配置文件验证失败: {e}')
    sys.exit(1)
" 2>&1)
  
  echo "$config_check"
  if echo "$config_check" | grep -q "验证通过"; then
    echo "✅ 配置验证成功"
  else
    echo "❌ 配置验证失败，请检查配置文件"
    echo "手动编辑配置：sudo -u $APP_USER nano $APP_DIR/config.json"
    exit 1
  fi
else
  echo "❌ 配置文件不存在，安装失败"
  exit 1
fi

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

echo "==> 启用并启动服务"
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# 等待几秒检查服务状态
sleep 3
if systemctl is-active --quiet ${SERVICE_NAME}; then
  echo "✅ 服务启动成功"
else
  echo "⚠️ 服务可能启动失败，请检查日志："
  echo "journalctl -u ${SERVICE_NAME} -n 20"
fi

echo
echo "✅ 安装完成！"
echo "• 查看服务状态：systemctl status ${SERVICE_NAME}"
echo "• 查看日志：journalctl -u ${SERVICE_NAME} -f"
echo "• 修改配置：sudo -u ${APP_USER} nano ${APP_DIR}/config.json"
echo "• 管理脚本：bash manage.sh [start|stop|restart|status|logs|edit|update]"
echo "• 多账号登录：在 Telegram 里给管理 Bot 发 /help → /adduser 开始登录流程"
echo
echo "下一步：在 Telegram 中向你的 Bot 发送 /help 开始使用"
