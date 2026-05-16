# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BioAnalog 4D — A comparative physiology and ecology academic presentation platform that draws analogies between human body systems and ecosystem processes:
- Digestive system ↔ Soil carbon cycling
- Urinary system ↔ Artificial wetland purification
- Respiratory system ↔ Atmospheric carbon balance

The AI assistant persona is "默存" (MoCun), a computational biology and systems omics research assistant powered by Xiaomi MIMO 2.5 Pro API.

## Architecture

**Frontend (vanilla HTML/CSS/JS, no build tools):**
- `public/` — Static files served by Nginx
- `index.html` — Landing page with particle animation background, click-to-enter flow
- `modules.html` — Module selection page (hero digestion card + centered AI card below)
- `q1.html`, `q2.html`, `q3.html` — Three topic pages (q1 has no floating AI widget; q2/q3 may have it)
- `ai_intro.html` — AI researcher introduction page
- `ai.html` — Full-page AI chat interface with sidebar persona card
- `js/api.js` — Backend URL resolution (`getBackendURL()`) and `callAI`/`callAIStream` functions
- `js/ai-widget.js` — Floating chat widget (FAB button + popup window) used on topic pages
- `css/common.css` — Global styles with CSS custom properties

**Backend (Flask + Gunicorn):**
- `backend/app.py` — Single-file Flask app with all routes
- `backend/persona.json` — AI persona configuration (name, system prompt, greeting)
- `backend/requirements.txt` — Python dependencies
- `backend/skills_library/` — SciAgent-Skills knowledge base
  - `registry.yaml` — Skills registry index
- `backend/test_skills.py` — Skills library test script

**Deployment:**
- `deploy.sh` — Ubuntu one-click deployment (Nginx + Gunicorn systemd service)
- `cleanup.sh` — Remove legacy heart_mirror project from server

**Navigation flow:**
```
index.html → modules.html → q1.html (main content, no floating AI widget)
            │                └→ bottom折叠区 → q2.html / q3.html (new window)
            └→ ai_intro.html → ai.html (full-page chat)
```
q2.html and q3.html are not linked from modules.html; they are accessible via the folded expansion section at the bottom of q1.html.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Non-streaming chat, supports single `message` or multi-turn `messages` array |
| `/api/chat/stream` | POST | Streaming SSE chat (returns `text/event-stream`) |
| `/api/health` | GET | Health check with skill count |
| `/api/skills` | GET | Debug: list all registered skills |

Request format uses `{ message, context }` or `{ messages, context }`. Context carries `topic` and `page` identifiers.

## Key Design Decisions

- **No build system**: All frontend code is vanilla JS/CSS. No npm, no bundler.
- **Backend URL resolution**: `api.js:getBackendURL()` uses a priority chain: URL param `?backend=xxx` → localStorage `backend_url` → auto-infer from hostname. This supports both local dev (localhost:5000) and reverse proxy deployments (same-origin `/api/`).
- **SSE streaming**: The `/api/chat/stream` endpoint uses Server-Sent Events with custom `event: skill_info` for metadata and standard `data:` for token chunks. Frontend attempts streaming first; on connection failure, automatically falls back to non-streaming `/api/chat`. Both `ai.html` and `ai-widget.js` maintain a `conversationHistory` array trimmed to `MAX_HISTORY=20` messages.
- **Nginx SSE requirements**: The `/api/` location block must include `proxy_http_version 1.1;`, `proxy_set_header Connection "";`, and `proxy_buffering off;` for SSE to work through the reverse proxy. The backend sets `X-Accel-Buffering: no` header as a fallback signal.
- **Skill injection**: `SciAgentSkillIndexer` does BM25-based retrieval over `skills_library/registry.yaml`, injecting the single most relevant SKILL.md content into the system prompt at query time. AI responses include `[来源: 技能名称]` citation tags. `load_persona()` reads `persona.json` from disk per request with graceful fallback on missing/corrupt file.
- **MIMO API auth**: Uses `api-key` header (not `Authorization: Bearer`).

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `MIMO_API_KEY` | Yes | — |
| `MIMO_API_URL` | No | `https://api.xiaomimimo.com/v1/chat/completions` |
| `MIMO_MODEL` | No | `mimo-v2.5-pro` |

Load via `.env` file in `backend/` directory (python-dotenv) or export before running.

## Development Commands

```bash
# Backend setup
cd backend
pip install -r requirements.txt
export MIMO_API_KEY="your-key"
python app.py  # Starts on 0.0.0.0:5000

# Frontend with Nginx (recommended, enables SSE proxy)
cd nginx && ./nginx.exe          # Windows: starts on :8080
# or: python -m http.server 8080 --directory public  (no SSE proxy)

# Server deployment
sudo -E bash deploy.sh  # Requires MIMO_API_KEY in environment
```

Local Nginx config is at `nginx/conf/nginx.conf`, proxying `/api/` to `127.0.0.1:5000` with SSE-compatible settings.

## Frontend Integration Pattern

To add AI widget to a new page, include before `</body>`:
```html
<script src="js/api.js"></script>
<script src="js/ai-widget.js"></script>
<script>initAIChat({ topic: "digestion", page: "your-page-name" });</script>
```
The `topic` value should match the page's subject area (e.g. `"digestion"`, `"urinary"`, `"respiratory"`). This is passed to the backend to bias skill retrieval.

## Tech Stack

- Frontend: Vanilla HTML/CSS/JS, SVG with CSS keyframe particle animations, marked.js for Markdown rendering
- Backend: Python 3, Flask 2.3, Gunicorn, PyYAML, requests, python-dotenv
- AI: Xiaomi MIMO 2.5 Pro via OpenAI-compatible API (streaming + non-streaming)
- Deploy: Nginx reverse proxy, systemd service, Ubuntu 22.04+

## Cloud Server Deployment

Production server: 8.136.152.54 (root). Memory files store credentials and deploy workflow.
To update: use Python paramiko to SFTP upload changed files to `/var/www/bioanalog/`, then `systemctl restart bioanalog && systemctl reload nginx`. The `deploy.sh` script is interactive and cannot be automated — always use paramiko directly.

## SVG Diagrams in q1.html

Three SVG illustrations in the parallels section (soil ecosystem cards) use CSS keyframe animations to visualize scientific processes:
- **Cascade degradation** (木质素→纤维素→单糖): molecule clusters fragmenting, enzyme attack particles, bond-breaking visualization
- **Feedback cycle** (凋落物→微生物→团聚体): nutrient flow particles along circular path, microbe division, aggregate bond formation
- **Carbon funnel** (新鲜凋落物→木质素→黑碳): CO₂ escape particles rising (mineralization), carbon settle particles sinking (sequestration), mineral bond formation

All SVGs use `width="100%"` for responsive centering within cards.

## Internal Tunneling (cpolar etc.)

When using tools like cpolar/ngrok to expose local services, configure backend URL via:
1. **URL param** (recommended): `https://your-front.cpolar.com?backend=https://your-back.cpolar.com`
2. **Page UI**: Click ⚙️ button on ai.html to set backend URL
3. **Auto-infer**: Falls back to `current-hostname:5000` if no config

Config persists in browser localStorage. Clear with `localStorage.removeItem('backend_url')`.

## Memory System

Persistent memory files are stored at `~/.claude/projects/D--Desktop-tridemo/memory/`:
- `reference_cloud_server.md` — Server SSH credentials and deploy path
- `feedback_deploy_workflow.md` — How to handle deployments (paramiko, overwrite, restart)
