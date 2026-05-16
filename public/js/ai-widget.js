/**
 * ai-widget.js — 浮动聊天组件
 * 流式输出 + 对话历史 + 状态指示
 * 依赖 api.js 中的 callAI / callAIStream 函数
 */

function initAIChat(context = {}) {
  if (document.getElementById('ai-widget-fab')) return;

  const fab = document.createElement('button');
  fab.id = 'ai-widget-fab';
  fab.title = 'AI 学术助手';
  fab.textContent = '💬';
  document.body.appendChild(fab);

  const win = document.createElement('div');
  win.id = 'ai-widget-win';
  win.innerHTML = `
    <div class="ai-header">
      <div class="avatar">🧬</div>
      <div class="info">
        <h2>默存</h2>
        <span>计算生物学与系统组学 · 在线</span>
      </div>
      <button id="ai-widget-clear" title="清空对话" style="margin-left:auto;background:none;border:1px solid rgba(255,255,255,.1);border-radius:4px;color:var(--text2);font-size:11px;cursor:pointer;padding:2px 8px;">清空</button>
      <button id="ai-widget-close" style="background:none;border:none;color:var(--text2);font-size:18px;cursor:pointer;padding:4px 8px;">✕</button>
    </div>
    <div class="w-msgs" id="ai-widget-msgs"></div>
    <div class="ai-input-area">
      <input type="text" id="ai-widget-input" placeholder="输入问题..." autocomplete="off" />
      <button id="ai-widget-send">发送</button>
    </div>
  `;
  document.body.appendChild(win);

  const msgsEl = document.getElementById('ai-widget-msgs');
  const inputEl = document.getElementById('ai-widget-input');
  const sendBtn = document.getElementById('ai-widget-send');
  const closeBtn = document.getElementById('ai-widget-close');

  let conversationHistory = [];
  let currentStreamCtrl = null;
  const MAX_HISTORY = 20;

  if (typeof marked !== 'undefined') {
    marked.setOptions({ mangle: false, headerIds: false });
  }

  function renderMarkdown(el, text) {
    if (typeof marked !== 'undefined') {
      el.innerHTML = marked.parse(text);
      el.querySelectorAll('a').forEach(a => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
    } else {
      el.textContent = text;
    }
  }

  function setMsgStatus(group, state, label) {
    const row = group.querySelector('.ai-status-row');
    const badge = group.querySelector('.ai-status-badge');
    const avatar = group.querySelector('.ai-msg-avatar');
    if (!badge || !row) return;
    if (!state) {
      row.style.display = 'none';
      if (avatar) avatar.className = 'ai-msg-avatar';
      return;
    }
    badge.className = 'ai-status-badge ai-status-' + state;
    badge.innerHTML = '<span class="ai-status-dot"><span></span></span><span class="ai-status-label">' + label + '</span>';
    row.style.display = 'flex';
    if (avatar) avatar.className = 'ai-msg-avatar ai-state-' + state;
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function addStreamingMsg() {
    const group = document.createElement('div');
    group.className = 'ai-msg-group';
    group.innerHTML =
      '<div class="ai-status-row" style="display:flex">' +
        '<div class="ai-status-badge ai-status-thinking">' +
          '<span class="ai-status-dot"><span></span></span>' +
          '<span class="ai-status-label">思考中</span>' +
        '</div>' +
      '</div>' +
      '<div class="ai-msg assistant">' +
        '<div class="ai-msg-avatar ai-state-thinking"><span class="ai-avatar-icon">🧬</span></div>' +
        '<div class="ai-msg-content"></div>' +
      '</div>';
    msgsEl.appendChild(group);
    msgsEl.scrollTop = msgsEl.scrollHeight;
    return group;
  }

  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = `ai-msg ${role}`;
    if (role === 'assistant') {
      div.innerHTML = '<div class="ai-msg-avatar ai-state-idle"><span class="ai-avatar-icon">🧬</span></div><div class="ai-msg-content"></div>';
      const content = div.querySelector('.ai-msg-content');
      renderMarkdown(content, text);
    } else {
      div.textContent = text;
    }
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
    return div;
  }

  function setLoading(on) {
    sendBtn.disabled = on;
    sendBtn.textContent = on ? '...' : '发送';
    inputEl.disabled = on;
  }

  // ---- Greeting ----
  addMsg('assistant', '你好，我是默存。名字取自"默而存之"——我沉在数据与生命的深处，不喧哗，只回应。请说。');
  addMsg('system', '回答中标注 [来源: xxx] 的内容来自知识库，[待验证] 的内容需人工核实。');

  // ---- Events ----
  fab.addEventListener('click', () => {
    win.classList.toggle('open');
    if (win.classList.contains('open')) inputEl.focus();
  });

  closeBtn.addEventListener('click', () => win.classList.remove('open'));

  document.getElementById('ai-widget-clear').addEventListener('click', () => {
    if (currentStreamCtrl) { currentStreamCtrl.abort(); currentStreamCtrl = null; }
    conversationHistory = [];
    msgsEl.innerHTML = '';
    addMsg('assistant', '你好，我是默存。名字取自"默而存之"——我沉在数据与生命的深处，不喧哗，只回应。请说。');
  });

  sendBtn.addEventListener('click', doSend);
  inputEl.addEventListener('keydown', e => { if (e.key === 'Enter') doSend(); });

  // ---- Send ----
  function doSend() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    addMsg('user', text);
    conversationHistory.push({ role: 'user', content: text });
    setLoading(true);

    if (typeof callAIStream === 'function') {
      const group = addStreamingMsg();
      const content = group.querySelector('.ai-msg-content');
      let fullText = '';
      let firstToken = true;

      currentStreamCtrl = callAIStream(
        text, context, conversationHistory,
        token => {
          if (firstToken) { firstToken = false; setMsgStatus(group, 'generating', '生成中'); }
          fullText += token;
          renderMarkdown(content, fullText);
          msgsEl.scrollTop = msgsEl.scrollHeight;
        },
        skills => { if (skills && skills.length) setMsgStatus(group, 'skill', '引用：' + skills[0]); },
        () => {
          setMsgStatus(group, null);
          conversationHistory.push({ role: 'assistant', content: fullText });
          if (conversationHistory.length > MAX_HISTORY) conversationHistory = conversationHistory.slice(-MAX_HISTORY);
          setLoading(false); currentStreamCtrl = null;
        },
        e => {
          group.remove(); currentStreamCtrl = null;
          if (e.message.includes('无法连接到 AI 服务') || e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
            doSendFallback(text);
          } else {
            const d = document.createElement('div'); d.className = 'ai-msg system'; d.textContent = e.message; msgsEl.appendChild(d);
            setLoading(false);
          }
        }
      );
    } else {
      doSendFallback(text);
    }
  }

  async function doSendFallback(text) {
    try {
      const reply = await callAI(text, context, conversationHistory);
      addMsg('assistant', reply);
      conversationHistory.push({ role: 'assistant', content: reply });
      if (conversationHistory.length > MAX_HISTORY) conversationHistory = conversationHistory.slice(-MAX_HISTORY);
    } catch (e) {
      const d = document.createElement('div');
      d.className = 'ai-msg system';
      d.textContent = e.message;
      msgsEl.appendChild(d);
    } finally {
      setLoading(false);
    }
  }
}
