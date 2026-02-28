/**
 * frontend/layout/app.js
 * Synervy AI – Main Application Controller
 *
 * Manages: theme toggle (dark/light, localStorage-persistent),
 *          multi-agent chat (POST /chat), risk-badge updates,
 *          sidebar collapse, activity feed polling, history log,
 *          and graceful error UI when backend is unreachable.
 */

/* ─── Constants ──────────────────────────────────────────── */
const API_BASE = window.location.origin;
const POLL_MS = 8000;   // activity-feed polling interval
const VALID_RISKS = new Set(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
const RISK_LABELS = { LOW: '🟢 Low', MEDIUM: '🟡 Medium', HIGH: '🟠 High', CRITICAL: '🔴 Critical' };

/* ─── Application State ──────────────────────────────────── */
const State = {
  theme: localStorage.getItem('synervy-theme') || 'dark',
  activeAgent: 'CoordinatorAgent',
  riskLevel: 'LOW',
  sidebarOpen: true,
  activityPanelOpen: true,
  currentPage: 'chat',
  typing: false,
  activityTimer: null,
  /** Context forwarded with every /chat request */
  context: {
    hh_size: 4,
    latitude: 18.6298,
    longitude: 73.7997,
    timezone: 'Asia/Kolkata',
    rate_peak: 12.0,
    rate_offpeak: 7.5,
  },
};

/* ─── DOM Cache ──────────────────────────────────────────── */
/** @type {Record<string, HTMLElement|null>} */
const dom = {};

function initDom() {
  const ids = [
    'app', 'topbar', 'sidebar', 'activity-panel',
    'chat-page', 'history-page', 'chat-messages', 'welcome-screen',
    'chat-input', 'send-btn', 'agent-name', 'risk-badge',
    'activity-feed', 'history-panel', 'history-body',
    'toggle-sidebar', 'toggle-activity', 'theme-toggle',
    'nav-chat', 'nav-history', 'apply-context',
    'ctx-hh-size', 'ctx-latitude', 'ctx-longitude', 'ctx-timezone',
  ];
  ids.forEach(id => {
    // Map hyphenated ids to camelCase keys for ergonomic access
    const key = id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    dom[key] = document.getElementById(id);
  });
  // Convenience aliases
  dom.body = document.body;
}

/* ─── Theme ──────────────────────────────────────────────── */
function applyTheme(theme) {
  State.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('synervy-theme', theme);
  // Show sun (☀️) in dark mode to invite switching to light, and vice-versa
  if (dom.themeToggle) dom.themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  applyTheme(State.theme === 'dark' ? 'light' : 'dark');
}

/* ─── Risk Level ─────────────────────────────────────────── */
function updateRiskLevel(level) {
  // Guard: treat unknown levels as LOW to prevent orphaned CSS classes
  const safeLevel = VALID_RISKS.has(level) ? level : 'LOW';
  State.riskLevel = safeLevel;

  if (dom.riskBadge) {
    dom.riskBadge.textContent = RISK_LABELS[safeLevel];
    dom.riskBadge.className = `risk-badge ${safeLevel}`;
  }

  // Body class drives the ambient glow animation defined in animations.css
  dom.body.classList.remove('risk-LOW', 'risk-MEDIUM', 'risk-HIGH', 'risk-CRITICAL');
  dom.body.classList.add(`risk-${safeLevel}`);

  // Sidebar accent border for HIGH / CRITICAL
  if (dom.sidebar) {
    dom.sidebar.classList.remove('risk-HIGH', 'risk-CRITICAL');
    if (safeLevel === 'HIGH' || safeLevel === 'CRITICAL') {
      dom.sidebar.classList.add(`risk-${safeLevel}`);
    }
  }
}

/* ─── Active Agent ───────────────────────────────────────── */
function updateActiveAgent(agentName) {
  State.activeAgent = agentName || 'CoordinatorAgent';
  if (dom.agentName) dom.agentName.textContent = State.activeAgent;
}

/* ─── Sidebar & Panel Toggles ────────────────────────────── */
function toggleSidebar() {
  State.sidebarOpen = !State.sidebarOpen;
  if (dom.sidebar) dom.sidebar.classList.toggle('collapsed', !State.sidebarOpen);
  // Button icon shows what the NEXT click will do (▶ means "open", ◀ means "close")
  if (dom.toggleSidebar) dom.toggleSidebar.textContent = State.sidebarOpen ? '◀' : '▶';
}

function toggleActivity() {
  State.activityPanelOpen = !State.activityPanelOpen;
  if (dom.activityPanel) dom.activityPanel.classList.toggle('hidden', !State.activityPanelOpen);
}

/* ─── Page Navigation ────────────────────────────────────── */
function showPage(page) {
  State.currentPage = page;
  if (dom.chatPage) dom.chatPage.classList.toggle('active', page === 'chat');
  if (dom.historyPage) dom.historyPage.classList.toggle('active', page === 'history');
  if (dom.navChat) dom.navChat.classList.toggle('active', page === 'chat');
  if (dom.navHistory) dom.navHistory.classList.toggle('active', page === 'history');
  if (page === 'history') loadHistory();
}

/* ─── Text Sanitization (prevent XSS) ───────────────────── */
/**
 * Escape HTML special characters in a string.
 * Applied to user-supplied content before rendering via innerHTML.
 */
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Render minimal trusted markdown (AI reply text only).
 * Never call this on user-submitted content. Use escapeHtml() for that.
 */
function renderMarkdown(text) {
  return String(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

/* ─── Chat – Message Rendering ───────────────────────────── */
function appendMessage({ role, content, agentName, recommendedAction, timestamp }) {
  if (!dom.chatMessages) return;

  // Hide welcome screen on first message
  if (dom.welcomeScreen) dom.welcomeScreen.style.display = 'none';

  const isUser = role === 'user';
  const timeStr = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  // User content must be escaped; AI reply is trusted markdown
  const bubbleHtml = isUser ? escapeHtml(content) : renderMarkdown(content);

  const agentTag = (!isUser && agentName)
    ? `<span class="msg-agent-tag">${escapeHtml(agentName)}</span>`
    : '';

  const actionCard = (!isUser && recommendedAction)
    ? `<div class="action-card"><span class="action-icon">💡</span>${escapeHtml(recommendedAction)}</div>`
    : '';

  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-message${isUser ? ' user' : ''}`;
  msgDiv.innerHTML = `
    <div class="msg-avatar ${isUser ? 'user' : 'ai'}">${isUser ? '👤' : '⚡'}</div>
    <div class="msg-body">
      <div class="msg-meta">${agentTag}<span>${timeStr}</span></div>
      <div class="msg-bubble">${bubbleHtml}</div>
      ${actionCard}
    </div>
  `;
  dom.chatMessages.appendChild(msgDiv);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

function showTypingIndicator() {
  if (!dom.chatMessages || State.typing) return;
  State.typing = true;
  if (dom.welcomeScreen) dom.welcomeScreen.style.display = 'none';

  const div = document.createElement('div');
  div.id = 'typing-msg';
  div.className = 'chat-message';
  div.innerHTML = `
    <div class="msg-avatar ai">⚡</div>
    <div class="msg-body">
      <div class="msg-bubble" style="padding:10px 16px;">
        <div class="typing-indicator"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  dom.chatMessages.appendChild(div);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

function removeTypingIndicator() {
  State.typing = false;
  const el = document.getElementById('typing-msg');
  if (el) el.remove();
}

/* ─── API – Chat ─────────────────────────────────────────── */
async function sendChatMessage(message) {
  showTypingIndicator();

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context: State.context }),
    });

    removeTypingIndicator();

    if (!response.ok) {
      throw new Error(`Server responded with HTTP ${response.status}`);
    }

    const data = await response.json();

    // Update topbar state
    updateActiveAgent(data.active_agent);
    updateRiskLevel(data.risk_level);

    appendMessage({
      role: 'assistant',
      content: data.reply || 'Request processed.',
      agentName: data.active_agent,
      riskLevel: data.risk_level,
      recommendedAction: data.recommended_action,
      timestamp: data.timestamp,
    });

  } catch (err) {
    removeTypingIndicator();
    // Show graceful error — never crash the UI
    appendMessage({
      role: 'assistant',
      content: 'System temporarily unavailable. Please retry.',
      agentName: 'SystemAgent',
      recommendedAction: 'Check that the Synervy AI server is running, then try again.',
      timestamp: new Date().toISOString(),
    });
    // Log filtered out in production
  }
}

/* ─── API – History ──────────────────────────────────────── */
async function loadHistory() {
  if (!dom.historyBody) return;

  dom.historyBody.innerHTML = `<tr><td colspan="6" class="empty-state">
    <div class="spinner"></div> Loading history…
  </td></tr>`;

  try {
    const response = await fetch(`${API_BASE}/history?limit=50`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (!data.history || data.history.length === 0) {
      dom.historyBody.innerHTML = `<tr><td colspan="6" class="empty-state">
        <div class="empty-icon">📋</div>
        No optimization history yet. Start a conversation to generate entries.
      </td></tr>`;
      return;
    }

    dom.historyBody.innerHTML = data.history.map(entry => {
      const time = new Date(entry.timestamp).toLocaleString();
      const riskLevel = VALID_RISKS.has(entry.risk_level) ? entry.risk_level : 'LOW';
      const approveBtn = entry.approval_status === 'pending'
        ? `<button class="approve-btn" data-id="${escapeHtml(entry.id)}" data-status="approved">Approve</button>`
        : '';
      return `
        <tr>
          <td>${escapeHtml(time)}</td>
          <td>${escapeHtml(entry.agent || '—')}</td>
          <td>${escapeHtml((entry.action || '—').substring(0, 80))}</td>
          <td><span class="risk-pill ${riskLevel}">${riskLevel}</span></td>
          <td><span class="status-chip ${escapeHtml(entry.approval_status || '')}">${escapeHtml(entry.approval_status || '—')}</span></td>
          <td>${approveBtn}</td>
        </tr>`;
    }).join('');

    // Attach approval handlers via event delegation (safer than inline onclick)
    dom.historyBody.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', () =>
        approveEntry(btn.dataset.id, btn.dataset.status)
      );
    });
  } catch (err) {
    dom.historyBody.innerHTML = `<tr><td colspan="6" class="empty-state">
      <div class="empty-icon">⚠️</div>Unable to load history — ${escapeHtml(err.message)}
    </td></tr>`;
    // Log filtered out in production
  }
}

async function approveEntry(id, status) {
  try {
    const response = await fetch(`${API_BASE}/history/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    // Reload to reflect updated status
    loadHistory();
  } catch (err) {
    // Log filtered out in production
  }
}

/* ─── API – Activity Feed ────────────────────────────────── */
async function refreshActivityFeed() {
  if (!dom.activityFeed) return;
  try {
    const response = await fetch(`${API_BASE}/agents/activity`);
    if (!response.ok) return;
    const data = await response.json();

    if (!data.activity || data.activity.length === 0) return;

    dom.activityFeed.innerHTML = data.activity.map(item => {
      const statusClass = item.status === 'active' ? 'active' : 'idle';
      return `
        <div class="activity-item">
          <div class="act-agent">${escapeHtml(item.agent)}</div>
          <div class="act-action">${escapeHtml(item.action)}</div>
          <div class="act-time">${escapeHtml(item.timestamp)}</div>
          <span class="act-status ${statusClass}">${statusClass}</span>
        </div>`;
    }).join('');
  } catch {
    // Activity feed is non-critical — silently skip on error
  }
}

/* ─── Quick Actions & Context ────────────────────────────── */
/**
 * Send a pre-built query string from a sidebar button or welcome chip.
 * Exposed on window so inline onclick="sendQuick(...)" in HTML still works.
 */
function sendQuick(msg) {
  if (!dom.chatInput || !msg) return;
  dom.chatInput.value = msg;
  handleSend();
}
window.sendQuick = sendQuick;  // required for inline HTML onclick

/** Apply sidebar configuration form values and sync to backend. */
function applyContext() {
  if (dom.ctxHhSize) State.context.hh_size = parseInt(dom.ctxHhSize.value, 10) || 4;
  if (dom.ctxLatitude) State.context.latitude = parseFloat(dom.ctxLatitude.value) || 18.6298;
  if (dom.ctxLongitude) State.context.longitude = parseFloat(dom.ctxLongitude.value) || 73.7997;
  if (dom.ctxTimezone) State.context.timezone = dom.ctxTimezone.value || 'Asia/Kolkata';

  // Fire-and-forget sync to backend
  fetch(`${API_BASE}/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(State.context),
  }).catch(err => { });

  // Momentary feedback on the button
  if (dom.applyContext) {
    const original = dom.applyContext.textContent;
    dom.applyContext.textContent = '✅ Applied';
    dom.applyContext.disabled = true;
    setTimeout(() => {
      dom.applyContext.textContent = original;
      dom.applyContext.disabled = false;
    }, 1800);
  }
}

/* ─── Input Handling ─────────────────────────────────────── */
function handleSend() {
  if (!dom.chatInput) return;
  const msg = dom.chatInput.value.trim();
  if (!msg || State.typing) return;

  dom.chatInput.value = '';
  dom.chatInput.style.height = '';  // reset auto-resize

  appendMessage({ role: 'user', content: msg, timestamp: new Date().toISOString() });
  sendChatMessage(msg);
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

/** Auto-grow textarea up to 120 px as the user types. */
function autoResize() {
  if (!dom.chatInput) return;
  dom.chatInput.style.height = 'auto';
  dom.chatInput.style.height = `${Math.min(dom.chatInput.scrollHeight, 120)}px`;
}

/* ─── Initialization ─────────────────────────────────────── */
function init() {
  initDom();

  // Apply persisted theme BEFORE painting (avoids flash-of-wrong-theme)
  applyTheme(State.theme);
  updateRiskLevel('LOW');

  // ── Event listeners ──────────────────────────────────────
  dom.themeToggle?.addEventListener('click', toggleTheme);
  dom.toggleSidebar?.addEventListener('click', toggleSidebar);
  dom.toggleActivity?.addEventListener('click', toggleActivity);
  dom.sendBtn?.addEventListener('click', handleSend);
  dom.chatInput?.addEventListener('keydown', handleKeydown);
  dom.chatInput?.addEventListener('input', autoResize);
  dom.navChat?.addEventListener('click', () => showPage('chat'));
  dom.navHistory?.addEventListener('click', () => showPage('history'));
  dom.applyContext?.addEventListener('click', applyContext);

  // ── Activity feed ────────────────────────────────────────
  refreshActivityFeed();
  State.activityTimer = setInterval(refreshActivityFeed, POLL_MS);

  // ── Default view ─────────────────────────────────────────
  showPage('chat');
}

// Run after the DOM is fully parsed
document.addEventListener('DOMContentLoaded', init);
