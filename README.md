# BioAnalogy — 人体生理与生态系统类比学术展示

## 项目结构

```
project/
├── public/                  # 静态文件（Nginx 根目录）
│   ├── index.html           # 落地页（粒子动画，点击进入模块选择）
│   ├── modules.html         # 模块选择页（2×2 卡片网格）
│   ├── q1.html              # 题目一：消化系统 ↔ 土壤固碳
│   ├── q2.html              # 题目二：泌尿系统 ↔ 人工湿地
│   ├── q3.html              # 题目三：呼吸系统 ↔ 大气碳平衡
│   ├── ai.html              # AI 学术助手（全屏聊天）
│   ├── ai_intro.html        # AI 研究员介绍页
│   ├── css/common.css       # 全局样式
│   └── js/
│       ├── api.js           # API 调用模块
│       └── ai-widget.js     # 浮动聊天组件
├── backend/                 # Flask 后端
│   ├── app.py               # 主应用
│   ├── persona.json         # AI 人格设定
│   ├── requirements.txt     # Python 依赖
│   ├── test_skills.py       # 技能库测试脚本
│   └── skills_library/
│       └── registry.yaml    # SciAgent 技能注册表
├── deploy.sh                # 一键部署脚本
├── cleanup.sh               # 清理旧项目脚本
└── README.md
```

## 页面导航流

```
index.html → modules.html → q1/q2/q3.html（带浮动 AI 聊天组件）
                           → ai_intro.html → ai.html（全屏 AI 对话）
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

## 内网穿透配置（cpolar 等）

当您使用内网穿透工具（如 cpolar、ngrok、frp 等）将本地服务暴露到公网时，需要配置前端如何连接到后端 API。

### 方案一：URL 参数配置（推荐）

访问前端页面时，在 URL 中添加 `backend` 参数，指定后端 API 的公网地址：

```
https://your-front.cpolar.com?backend=https://your-back.cpolar.com
```

首次设置后，地址会自动保存到浏览器的 localStorage，后续访问无需重复配置。

### 方案二：页面内配置

1. 打开 AI 聊天页面（ai.html）
2. 点击右上角的 **⚙️ 后端** 按钮
3. 在弹出的对话框中输入后端 API 的公网地址
4. 页面会自动刷新并应用新配置

### 方案三：自动推断

如果不进行任何配置，前端会自动使用 `当前域名:5000` 作为后端地址。这要求：

- 后端服务也通过内网穿透暴露了 5000 端口
- 前端和后端使用相同的域名（不同的端口隧道）

### 配置示例

假设您使用 cpolar 暴露了两个隧道：

- 前端：`https://front123.cpolar.com`（指向本地 8080 端口）
- 后端：`https://back123.cpolar.com`（指向本地 5000 端口）

访问方式：
```
https://front123.cpolar.com?backend=https://back123.cpolar.com
```

### 重置配置

如果需要清除已保存的后端地址配置：

1. 点击 **⚙️ 后端** 按钮
2. 在弹出的对话框中清空输入框，留空直接确定
3. 或者在浏览器开发者工具的 Console 中执行：`localStorage.removeItem('backend_url')`

### 注意事项

- 后端服务必须监听 `0.0.0.0`（已在 app.py 中配置）
- 确保后端已正确配置 CORS（已启用）
- 如果使用 cpolar，需要为前端和后端分别建立两条隧道
- 配置保存在浏览器的 localStorage 中，清除浏览器数据会丢失配置
