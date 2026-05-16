#!/bin/bash
# ============================================
# BioAnalog 4D 一键部署脚本
# 目标：Ubuntu 22.04+，清除旧项目，80端口服务新项目
# 使用方法：sudo bash deploy.sh
# ============================================
set -e

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
step()  { echo -e "\n${CYAN}==== $1 ====${NC}"; }

# ============================================
# 步骤 0：环境检查
# ============================================
step "Step 0: Environment Check"

if [ "$(id -u)" -ne 0 ]; then
    error "Please run as root: sudo bash deploy.sh"
    exit 1
fi

echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "Memory: $(free -h | awk '/Mem:/ {print $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $4 " free"}')"
echo ""

# ============================================
# 步骤 1：清理旧项目（heart_mirror）
# ============================================
step "Step 1: Clean Up Old Project (heart_mirror)"

# 停止旧项目服务
if systemctl is-active --quiet heart_mirror 2>/dev/null; then
    info "Stopping heart_mirror service..."
    systemctl stop heart_mirror
fi

if [ -f /etc/systemd/system/heart_mirror.service ]; then
    info "Disabling and removing heart_mirror service..."
    systemctl disable heart_mirror 2>/dev/null || true
    rm -f /etc/systemd/system/heart_mirror.service
fi

# 删除旧的 Nginx 站点配置
if [ -f /etc/nginx/sites-enabled/heart_mirror ]; then
    info "Removing heart_mirror nginx config..."
    rm -f /etc/nginx/sites-enabled/heart_mirror
fi
if [ -f /etc/nginx/sites-available/heart_mirror ]; then
    rm -f /etc/nginx/sites-available/heart_mirror
fi

# 杀掉旧项目残留进程（gunicorn on 8000）
OLD_PIDS=$(ss -tlnp | grep ':8000' | grep -oP 'pid=\K[0-9]+' | sort -u)
if [ -n "$OLD_PIDS" ]; then
    info "Killing old processes on port 8000: $OLD_PIDS"
    kill -9 $OLD_PIDS 2>/dev/null || true
fi

# 删除旧项目文件（可选，注释掉则保留）
if [ -d /var/www/heart_mirror ]; then
    info "Removing /var/www/heart_mirror..."
    rm -rf /var/www/heart_mirror
fi

# 也清理之前部署在 8080 的 bioanalogy（如果存在）
if systemctl is-active --quiet bioanalogy 2>/dev/null; then
    info "Stopping old bioanalogy service (port 8080)..."
    systemctl stop bioanalogy
fi
if [ -f /etc/nginx/sites-enabled/bioanalogy ]; then
    rm -f /etc/nginx/sites-enabled/bioanalogy
fi
if [ -f /etc/nginx/sites-available/bioanalogy ]; then
    rm -f /etc/nginx/sites-available/bioanalogy
fi

systemctl daemon-reload
info "Old project cleaned up."

# ============================================
# 步骤 2：安装系统依赖
# ============================================
step "Step 2: Install System Dependencies"

apt-get update -qq
apt-get install -y -qq nginx python3-pip python3-venv git curl > /dev/null 2>&1
info "nginx, python3-pip, python3-venv, git, curl installed."

# ============================================
# 步骤 3：获取项目文件
# ============================================
step "Step 3: Get Project Files"

DEPLOY_DIR="/var/www/bioanalog"

if [ -d "$DEPLOY_DIR/backend" ] && [ -f "$DEPLOY_DIR/backend/app.py" ]; then
    info "Project already exists at $DEPLOY_DIR, skipping download."
else
    echo ""
    echo "  How to get the project files:"
    echo "    [1] Clone from GitHub (recommended)"
    echo "    [2] I will upload manually via SCP/SFTP"
    echo ""
    read -p "  Choose (1 or 2): " CHOICE

    if [ "$CHOICE" = "1" ]; then
        info "Cloning from GitHub..."
        rm -rf "$DEPLOY_DIR"
        git clone https://github.com/baimocn/bioanalog.git "$DEPLOY_DIR"
        info "Cloned to $DEPLOY_DIR"
    else
        echo ""
        warn "Please upload your project files to $DEPLOY_DIR"
        echo ""
        echo "  From your local machine, run:"
        echo "    scp -r ./backend/*  root@YOUR_IP:$DEPLOY_DIR/backend/"
        echo "    scp -r ./public/*   root@YOUR_IP:$DEPLOY_DIR/public/"
        echo ""
        echo "  Or use SFTP (FileZilla, WinSCP, etc.)"
        echo ""
        read -p "  Press Enter after uploading files..."
    fi
fi

# 验证关键文件
if [ ! -f "$DEPLOY_DIR/backend/app.py" ]; then
    error "backend/app.py not found! Please check your upload."
    exit 1
fi
if [ ! -f "$DEPLOY_DIR/public/index.html" ]; then
    error "public/index.html not found! Please check your upload."
    exit 1
fi
info "Project files verified."

# ============================================
# 步骤 4：Python 虚拟环境 + 依赖
# ============================================
step "Step 4: Python Virtual Environment"

cd "$DEPLOY_DIR/backend"

if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    python3 -m venv venv
fi

info "Installing Python dependencies..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -q -r requirements.txt
info "Python dependencies installed."

# ============================================
# 步骤 5：环境变量配置
# ============================================
step "Step 5: Environment Variables (.env)"

ENV_FILE="$DEPLOY_DIR/backend/.env"

if [ -f "$ENV_FILE" ] && grep -q "MIMO_API_KEY" "$ENV_FILE" && ! grep -q "your-api-key-here" "$ENV_FILE"; then
    info ".env already configured, skipping."
else
    # 生成模板
    cat > "$ENV_FILE" <<'ENVEOF'
MIMO_API_KEY=your-api-key-here
MIMO_API_URL=https://api.xiaomimimo.com/v1/chat/completions
MIMO_MODEL=mimo-v2.5-pro
ENVEOF

    echo ""
    warn "Please edit the .env file with your real API key:"
    echo ""
    echo "  File: $ENV_FILE"
    echo ""
    echo "  Current content:"
    cat "$ENV_FILE"
    echo ""
    read -p "  Enter your MIMO_API_KEY (or press Enter to skip): " API_KEY

    if [ -n "$API_KEY" ]; then
        sed -i "s|your-api-key-here|$API_KEY|" "$ENV_FILE"
        info "API key saved to .env"
    else
        warn "API key not set. AI features will not work until you edit .env"
    fi
fi

# ============================================
# 步骤 6：Systemd 服务（Gunicorn）
# ============================================
step "Step 6: Systemd Service (Gunicorn)"

cat > /etc/systemd/system/bioanalog.service <<EOF
[Unit]
Description=BioAnalog 4D Flask API (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$DEPLOY_DIR/backend
ExecStart=$DEPLOY_DIR/backend/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 60 app:app
Restart=always
RestartSec=3
EnvironmentFile=$DEPLOY_DIR/backend/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bioanalog
systemctl restart bioanalog
sleep 2

if systemctl is-active --quiet bioanalog; then
    info "Gunicorn started on 127.0.0.1:5000"
else
    error "Gunicorn failed to start! Check: journalctl -u bioanalog -n 20"
    exit 1
fi

# ============================================
# 步骤 7：Nginx 配置（80 端口）
# ============================================
step "Step 7: Nginx Configuration (port 80)"

cat > /etc/nginx/sites-available/bioanalog <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # 前端静态文件
    root $DEPLOY_DIR/public;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API 反向代理（SSE 流式兼容）
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
        proxy_read_timeout 120s;
        proxy_buffering off;
    }

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
}
EOF

# 删除默认站点（避免冲突）
rm -f /etc/nginx/sites-enabled/default

ln -sf /etc/nginx/sites-available/bioanalog /etc/nginx/sites-enabled/

nginx -t
systemctl reload nginx
info "Nginx configured: port 80 -> static files + /api/ -> Gunicorn"

# ============================================
# 步骤 8：文件权限
# ============================================
step "Step 8: File Permissions"

chown -R www-data:www-data "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"
info "Permissions set."

# ============================================
# 步骤 9：防火墙
# ============================================
step "Step 9: Firewall"

if command -v ufw &> /dev/null; then
    ufw allow 22/tcp 2>/dev/null || true
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    info "Firewall rules added (22, 80, 443)."
    warn "Note: If using Alibaba Cloud / Tencent Cloud, also open ports in the Security Group console."
else
    warn "ufw not found. If using cloud server, configure Security Group manually."
fi

# ============================================
# 步骤 10：验证
# ============================================
step "Step 10: Verification"

echo ""

# 检查后端
sleep 1
HEALTH=$(curl -s --max-time 5 http://127.0.0.1:5000/api/health 2>/dev/null)
if echo "$HEALTH" | grep -q '"status"'; then
    info "Backend OK: $HEALTH"
else
    error "Backend not responding on port 5000!"
    echo "  Check logs: journalctl -u bioanalog -n 20 --no-pager"
fi

# 检查 Nginx
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:80/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    info "Nginx OK: http://localhost:80 returns $HTTP_CODE"
else
    error "Nginx returned HTTP $HTTP_CODE"
fi

# 检查代理
PROXY_HEALTH=$(curl -s --max-time 5 http://127.0.0.1:80/api/health 2>/dev/null)
if echo "$PROXY_HEALTH" | grep -q '"status"'; then
    info "Nginx proxy OK: /api/ -> Gunicorn works"
else
    error "Nginx proxy to /api/ not working!"
fi

# ============================================
# 完成
# ============================================
step "Deployment Complete!"

PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo "  Frontend:  http://$PUBLIC_IP/"
echo "  API:       http://$PUBLIC_IP/api/chat"
echo "  Health:    http://$PUBLIC_IP/api/health"
echo ""
echo "  ---- Useful Commands ----"
echo "  View backend logs:    journalctl -u bioanalog -f"
echo "  Restart backend:      systemctl restart bioanalog"
echo "  Restart nginx:        systemctl reload nginx"
echo "  Edit API key:         nano $DEPLOY_DIR/backend/.env"
echo "                        then: systemctl restart bioanalog"
echo "  Edit Nginx config:    nano /etc/nginx/sites-available/bioanalog"
echo "                        then: nginx -t && systemctl reload nginx"
echo ""
