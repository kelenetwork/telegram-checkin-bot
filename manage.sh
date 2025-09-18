#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="tg-checkin"
APP_DIR="/opt/tg-checkin"

usage() {
  cat <<EOF
用法: ./manage.sh [start|stop|restart|status|logs|edit|update]
  start     启动服务
  stop      停止服务
  restart   重启服务
  status    查看状态
  logs      实时日志
  edit      编辑配置文件（config.json）
  update    从当前仓库目录同步到 ${APP_DIR} 并重启
EOF
}

cmd="${1:-}"; [[ -z "$cmd" ]] && usage && exit 0

case "$cmd" in
  start) systemctl start "$SERVICE_NAME" ;;
  stop) systemctl stop "$SERVICE_NAME" ;;
  restart) systemctl restart "$SERVICE_NAME" ;;
  status) systemctl status "$SERVICE_NAME" ;;
  logs) journalctl -u "$SERVICE_NAME" -f ;;
  edit) sudo -u tgcheckin ${EDITOR:-nano} ${APP_DIR}/config.json ;;
  update)
    echo "==> 同步当前目录到 ${APP_DIR}"
    rsync -a --delete --exclude=".git" ./ "${APP_DIR}/"
    chown -R tgcheckin:tgcheckin "${APP_DIR}"
    systemctl restart "$SERVICE_NAME"
    ;;
  *) usage ;;
esac
