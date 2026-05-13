# BioAnalogy — 人体生理与生态系统类比学术展示

## 项目结构

```
project/
├── public/                  # 静态文件（Nginx 根目录）
│   ├── index.html           # 导航页
│   ├── q1.html              # 题目一：消化系统 ↔ 土壤固碳（替换为你的页面）
│   ├── q2.html              # 题目二：泌尿系统 ↔ 人工湿地（替换为你的页面）
│   ├── q3.html              # 题目三：呼吸系统 ↔ 大气碳平衡（替换为你的页面）
│   ├── ai.html              # AI 学术助手（全屏聊天）
│   ├── css/common.css       # 全局样式
│   └── js/
│       ├── api.js           # API 调用模块
│       └── ai-widget.js     # 浮动聊天组件
├── backend/                 # Flask 后端
│   ├── app.py               # 主应用
│   ├── persona.json         # AI 人格设定
│   └── requirements.txt     # Python 依赖
├── deploy.sh                # 一键部署脚本
└── README.md
```

## 快速开始

### 本地开发

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 设置环境变量
export MIMO_API_KEY="your-api-key-here"
export MIMO_API_URL="https://api.ccswitch.com/v1/chat/completions"

# 3. 启动后端
python app.py

# 4. 打开 public/index.html（或用任意静态服务器托管 public/）
```

### 服务器部署

```bash
# 设置环境变量后执行
export MIMO_API_KEY="your-api-key"
sudo -E bash deploy.sh
```

部署完成后：
- 前端访问: `http://YOUR_SERVER_IP/`
- API 地址: `http://YOUR_SERVER_IP/api/chat`

## 替换题目页面

将你的三个题目页面分别重命名并放入 `public/` 目录：

```bash
cp your-question-1.html public/q1.html
cp your-question-2.html public/q2.html
cp your-question-3.html public/q3.html
```

**注意：**
- 替换后的页面如需 AI 聊天功能，在 `</body>` 前添加：
  ```html
  <script src="js/api.js"></script>
  <script src="js/ai-widget.js"></script>
  <script>initAIChat({ topic: 1, page: "your-page-name" });</script>
  ```
- `common.css` 提供了通用样式，你的页面可以引入使用

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MIMO_API_KEY` | 小米 MIMO API Key | (必填) |
| `MIMO_API_URL` | API 端点 | `https://api.ccswitch.com/v1/chat/completions` |
| `MIMO_MODEL` | 模型名称 | `mimo-v2.5-pro` |

## API 接口

### POST /api/chat

请求：
```json
{
  "message": "土壤有机碳的三步模型是什么？",
  "context": { "topic": 1, "page": "digestion" }
}
```

响应：
```json
{
  "reply": "土壤有机碳的三步模型由 Paul (2016) 提出..."
}
```

### GET /api/health

响应：
```json
{
  "status": "ok",
  "api_configured": true
}
```
