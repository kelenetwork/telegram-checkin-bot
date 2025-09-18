#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="tg-checkin"
APP_DIR="/opt/tg-checkin"
APP_USER="tgcheckin"

if [[ $EUID -ne 0 ]]; then
  echo "请用 root 运行：sudo bash uninstall.sh"; exit 1
fi

systemctl stop ${SERVICE_NAME} || true
systemctl disable ${SERVICE_NAME} || true
rm -f /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload

# 如需保留数据，请注释下一行
rm -rf "${APP_DIR}"

# 删除系统用户（若无其它用途）
id -u "${APP_USER}" >/dev/null 2>&1 && userdel -r "${APP_USER}" || true

echo "✅ 已卸载（如保留了 ${APP_DIR}，会话与配置仍在）。"
