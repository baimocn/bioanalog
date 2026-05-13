/**
 * ai-widget.js — 浮动聊天组件
 * 在任意页面引入后调用 initAIChat(context) 即可挂载
 * 依赖 api.js 中的 callAI 函数
 */

function initAIChat(context = {}) {
  // Avoid duplicate init
  if (document.getElementById('ai-widget-fab')) return;

  // ---- Create FAB button ----
  const fab = document.createElement('button');
  fab.id = 'ai-widget-fab';
  fab.title = 'AI 学术助手';
  fab.textContent = '💬';
  document.body.appendChild(fab);

  // ---- Create chat window ----
  const win = document.createElement('div');
  win.id = 'ai-widget-win';
  win.innerHTML = `
    <div class="ai-header">
      <div class="avatar">🧬</div>
      <div class="info">
        <h2>默存</h2>
        <span>计算生物学与系统组学 · 在线</span>
      </div>
      <button id="ai-widget-close" style="margin-left:auto;background:none;border:none;color:var(--text2);font-size:18px;cursor:pointer;padding:4px 8px;">✕</button>
    </div>
    <div class="w-msgs" id="ai-widget-msgs"></div>
    <div class="ai-input-area">
      <input type="text" id="ai-widget-input" placeholder="输入问题..." autocomplete="off" />
      <button id="ai-widget-send">发送</button>
    </div>
  `;
  document.body.appendChild(win);

  // ---- References ----
  const msgsEl = document.getElementById('ai-widget-msgs');
  const inputEl = document.getElementById('ai-widget-input');
  const sendBtn = document.getElementById('ai-widget-send');
  const closeBtn = document.getElementById('ai-widget-close');

  // ---- Greeting ----
  addMsg('assistant', '你好，我是默存。名字取自"默而存之"——我沉在数据与生命的深处，不喧哗，只回应。请说。');

  // ---- Events ----
  fab.addEventListener('click', () => {
    win.classList.toggle('open');
    if (win.classList.contains('open')) inputEl.focus();
  });

  closeBtn.addEventListener('click', () => win.classList.remove('open'));

  sendBtn.addEventListener('click', doSend);
  inputEl.addEventListener('keydown', e => { if (e.key === 'Enter') doSend(); });

  // ---- Helpers ----
  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = `ai-msg ${role}`;
    div.textContent = text;
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
    return div;
  }

  function setLoading(on) {
    sendBtn.disabled = on;
    sendBtn.textContent = on ? '...' : '发送';
    inputEl.disabled = on;
  }

  async function doSend() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    addMsg('user', text);
    setLoading(true);

    const loader = addMsg('assistant', '');
    loader.innerHTML = '<span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>';

    try {
      const reply = await callAI(text, context);
      loader.textContent = reply;
    } catch (e) {
      loader.className = 'ai-msg system';
      loader.textContent = e.message;
    } finally {
      setLoading(false);
    }
  }
}
