#!/bin/bash
# ============================================
# 清理旧项目脚本
# 彻底移除 heart_mirror 及其所有残留
# 使用方法：sudo bash cleanup.sh
# ============================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo ""
echo "=========================================="
echo "  Old Project Cleanup Script"
echo "=========================================="
echo ""

# 1. 停止服务
info "Stopping heart_mirror service..."
systemctl stop heart_mirror 2>/dev/null || true
systemctl disable heart_mirror 2>/dev/null || true

# 2. 删除 systemd 服务文件
if [ -f /etc/systemd/system/heart_mirror.service ]; then
    info "Removing heart_mirror.service..."
    rm -f /etc/systemd/system/heart_mirror.service
fi

# 3. 删除 Nginx 配置
info "Removing heart_mirror nginx configs..."
rm -f /etc/nginx/sites-enabled/heart_mirror
rm -f /etc/nginx/sites-available/heart_mirror

# 4. 杀掉残留进程
info "Killing residual processes on port 8000..."
PIDS=$(ss -tlnp | grep ':8000' | grep -oP 'pid=\K[0-9]+' | sort -u)
if [ -n "$PIDS" ]; then
    kill -9 $PIDS 2>/dev/null || true
    info "Killed PIDs: $PIDS"
fi

# 5. 删除项目文件
if [ -d /var/www/heart_mirror ]; then
    info "Removing /var/www/heart_mirror..."
    rm -rf /var/www/heart_mirror
fi

# 6. 重载 systemd 和 nginx
systemctl daemon-reload
nginx -t && systemctl reload nginx 2>/dev/null || true

echo ""
echo "=========================================="
info "Cleanup complete!"
echo "  Port 80 is now free."
echo "  Run deploy.sh to deploy the new project."
echo "=========================================="
