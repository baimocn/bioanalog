#!/bin/bash
# ============================================
# BioAnalogy 一键部署脚本
# 目标环境：Ubuntu 22.04, 2核2G
# ============================================
set -e

PROJ_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="/var/www/bio"

echo "=== BioAnalogy 部署脚本 ==="
echo "项目目录: $PROJ_ROOT"
echo "部署目标: $DEPLOY_DIR"
echo ""

# ---- 1. 系统依赖 ----
echo "[1/5] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq nginx python3-pip python3-venv > /dev/null

# ---- 2. 部署文件 ----
echo "[2/5] 部署文件..."
mkdir -p "$DEPLOY_DIR"
# 复制前端
cp -r "$PROJ_ROOT/public/"* "$DEPLOY_DIR/"
# 复制后端
cp -r "$PROJ_ROOT/backend" "$DEPLOY_DIR/backend"

# ---- 3. Python 依赖 ----
echo "[3/5] 安装 Python 依赖..."
cd "$DEPLOY_DIR/backend"
python3 -m venv venv
./venv/bin/pip install -q -r requirements.txt

# ---- 4. Systemd 服务 ----
echo "[4/5] 配置 systemd 服务..."
cat > /etc/systemd/system/bioapi.service <<EOF
[Unit]
Description=BioAnalogy Flask API (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$DEPLOY_DIR/backend
ExecStart=$DEPLOY_DIR/backend/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 1 --timeout 60 app:app
Restart=always
RestartSec=3
Environment="MIMO_API_KEY=${MIMO_API_KEY:-}"
Environment="MIMO_API_URL=${MIMO_API_URL:-https://api.ccswitch.com/v1/chat/completions}"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bioapi
systemctl restart bioapi
echo "    Gunicorn 已启动: 127.0.0.1:5000"

# ---- 5. Nginx ----
echo "[5/5] 配置 Nginx..."
cat > /etc/nginx/sites-available/bioanalogy <<EOF
server {
    listen 80;
    server_name _;

    root $DEPLOY_DIR;
    index index.html;

    # 静态文件
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
}
EOF

ln -sf /etc/nginx/sites-available/bioanalogy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=== 部署完成 ==="
echo "  前端: http://YOUR_SERVER_IP/"
echo "  API:  http://YOUR_SERVER_IP/api/chat"
echo ""
echo "如需设置 API Key，请编辑 /etc/systemd/system/bioapi.service"
echo "中的 MIMO_API_KEY 环境变量，然后运行:"
echo "  systemctl daemon-reload && systemctl restart bioapi"
