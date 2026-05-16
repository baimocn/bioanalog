/**
 * api.js — 通用 AI 接口调用模块
 * 提供 callAI 函数，供 ai.html 和 ai-widget.js 共用
 */

/**
 * 获取后端 API 地址
 * 优先级：
 * 1. URL 参数 ?backend=xxx（首次设置后保存到 localStorage）
 * 2. localStorage 中已保存的地址
 * 3. 自动推断：本地环境用 localhost:5000，公网环境用当前 hostname:5000
 */
function getBackendURL() {
  // 1. 检查 URL 参数
  const urlParams = new URLSearchParams(window.location.search);
  const backendParam = urlParams.get('backend');
  if (backendParam) {
    localStorage.setItem('backend_url', backendParam);
    return backendParam;
  }

  // 2. 检查 localStorage
  const saved = localStorage.getItem('backend_url');
  if (saved) return saved;

  // 3. 自动推断
  const hostname = window.location.hostname;

  // 本地开发环境（无 Nginx，前后端分离）
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5000';
  }

  // 公网环境（Nginx 反向代理 /api/ → 后端）：使用相对路径，同源访问
  return '';
}

const API_BASE = getBackendURL();

/**
 * 调用后端 AI 接口
 * @param {string} message - 用户消息（单轮模式）
 * @param {object} context - 上下文信息，如 { topic: 1, page: "digestion" }
 * @param {Array}  messages - 可选，多轮对话历史 [{role, content}]
 * @returns {Promise<string>} AI 回复文本
 */
async function callAI(message, context = {}, messages = null) {
  try {
    const payload = messages
      ? { messages, context }
      : { message, context };
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    return data.reply || '未收到有效回复。';
  } catch (e) {
    if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
      throw new Error('无法连接到 AI 服务，请确认后端已启动。');
    }
    throw e;
  }
}

/**
 * 流式调用后端 AI 接口（SSE）
 * @param {string} message - 用户消息
 * @param {object} context - 上下文信息
 * @param {Array}  messages - 多轮对话历史
 * @param {function} onToken - 每收到一个 token 时的回调 (token: string)
 * @param {function} onSkill - 收到技能引用时的回调 (skillNames: string[])
 * @param {function} onDone - 流结束时的回调 ()
 * @param {function} onError - 错误回调 (error: Error)
 * @returns {AbortController} 可用于取消请求
 */
function callAIStream(message, context, messages, onToken, onSkill, onDone, onError) {
  const controller = new AbortController();

  const payload = messages
    ? { messages, context }
    : { message, context };

  fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal,
  }).then(async resp => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.reply || err.error || `HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let eventType = 'message';
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
          continue;
        }
        if (!line.startsWith('data:')) continue;
        const dataStr = line.slice(5).trim();
        if (dataStr === '[DONE]') {
          onDone();
          return;
        }
        try {
          const data = JSON.parse(dataStr);
          if (eventType === 'skill_info' && data.skills) {
            onSkill(data.skills);
          } else if (data.error) {
            throw new Error(data.error);
          } else if (data.token) {
            onToken(data.token);
          }
        } catch (parseErr) {
          if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr;
        }
        eventType = 'message';
      }
    }
    onDone();
  }).catch(e => {
    if (e.name === 'AbortError') return;
    if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
      onError(new Error('无法连接到 AI 服务，请确认后端已启动。'));
    } else {
      onError(e);
    }
  });

  return controller;
}
