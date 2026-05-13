/**
 * api.js — 通用 AI 接口调用模块
 * 提供 callAI 函数，供 ai.html 和 ai-widget.js 共用
 */

// 开发环境：前端 :8080，后端 :5000；生产环境由 Nginx 代理，同源
const API_BASE = (location.port === '5000')
  ? location.origin
  : `${location.protocol}//${location.hostname}:5000`;

/**
 * 调用后端 AI 接口
 * @param {string} message - 用户消息
 * @param {object} context - 上下文信息，如 { topic: 1, page: "digestion" }
 * @returns {Promise<string>} AI 回复文本
 */
async function callAI(message, context = {}) {
  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context })
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
