/**
 * Tatsu AI — Frontend Controller
 * ================================
 * WebSocket client for real-time chat, system stats polling,
 * message rendering, confirmation handling, and UI interactions.
 */

// ── API Helper ───────────────────────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }
    const res = await fetch(`${baseUrl}${endpoint}`, options);
    if (res.status === 401) {
        handleLogout();
        throw new Error('Unauthorized');
    }
    return res;
}

// ── State & Elements ─────────────────────────────────────────────────────────
let ws = null;
let isConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT = 10;
const RECONNECT_DELAY = 2000;
let pendingConfirmation = null;
let authToken = localStorage.getItem('tatsu_token');

const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const baseUrl = `${window.location.protocol}//${window.location.host}`;

// DOM Elements
const messagesContainer = document.getElementById('messages-container');
const welcomeScreen = document.getElementById('welcome-screen');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const connIndicator = document.getElementById('connection-indicator');
const connText = document.getElementById('conn-text');
const statusText = document.getElementById('status-text');
const modelName = document.getElementById('model-name');
const toolList = document.getElementById('tool-list');
const toolCount = document.getElementById('tool-count');
const activityFeed = document.getElementById('activity-feed');
const confirmOverlay = document.getElementById('confirmation-overlay');
const confirmBody = document.getElementById('confirm-body');
const btnApprove = document.getElementById('btn-approve');
const btnDeny = document.getElementById('btn-deny');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
const newChatBtn = document.getElementById('new-chat-btn');
const historyBtn = document.getElementById('history-btn');
const chatHistoryList = document.getElementById('chat-history-list');

// Login Elements
const loginOverlay = document.getElementById('login-overlay');
const appContainer = document.getElementById('app-container');
const loginPassword = document.getElementById('login-password');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');

// ── WebSocket Connection ─────────────────────────────────────────────────────
function connectWebSocket() {
    if (!authToken) return;
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat?token=${authToken}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        isConnected = true;
        reconnectAttempts = 0;
        setConnectionStatus('connected', 'Connected');
        statusText.textContent = 'ONLINE';
        addActivity('🟢', 'Connected to Tatsu AI');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleServerEvent(data);
        } catch (e) {
            console.error('Failed to parse message:', e);
        }
    };

    ws.onclose = () => {
        isConnected = false;
        setConnectionStatus('error', 'Disconnected');
        statusText.textContent = 'OFFLINE';

        if (reconnectAttempts < MAX_RECONNECT) {
            reconnectAttempts++;
            addActivity('🔄', `Reconnecting (${reconnectAttempts}/${MAX_RECONNECT})...`);
            setTimeout(connectWebSocket, RECONNECT_DELAY * reconnectAttempts);
        }
    };

    ws.onerror = () => {
        setConnectionStatus('error', 'Error');
    };
}

function setConnectionStatus(status, text) {
    connIndicator.className = `connection-indicator ${status}`;
    connText.textContent = text;
}

// ── Send Message ─────────────────────────────────────────────────────────────
function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !isConnected) return;

    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    appendMessage('user', content);
    ws.send(JSON.stringify({ type: 'message', content }));

    messageInput.value = '';
    messageInput.style.height = 'auto';
    messageInput.focus();
}

// ── Handle Server Events ─────────────────────────────────────────────────────
function handleServerEvent(data) {
    switch (data.type) {
        case 'thinking':
            appendSystemMessage('thinking', '🧠 THINKING', data.content);
            addActivity('🧠', data.content);
            break;

        case 'tool_call':
            appendSystemMessage('tool-call', `🔧 TOOL: ${data.tool}`, formatToolCall(data));
            addActivity('🔧', `Using ${data.tool}`);
            break;

        case 'tool_result':
            appendSystemMessage('tool-result', `✅ RESULT: ${data.tool}`, data.content || data.result);
            addActivity('✅', `${data.tool} complete`);
            break;

        case 'response':
            appendMessage('assistant', data.content);
            addActivity('💬', 'Response received');
            break;

        case 'error':
            appendSystemMessage('error', '❌ ERROR', data.content);
            addActivity('❌', data.content);
            break;

        case 'confirmation':
            showConfirmation(data);
            addActivity('⚠️', `Confirmation: ${data.content}`);
            break;

        case 'status':
            addActivity('ℹ️', data.content);
            break;

        default:
            console.log('Unknown event:', data);
    }
}

// ── Message Rendering ────────────────────────────────────────────────────────
function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = role === 'user' ? 'U' : 'T';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatContent(content);

    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(contentDiv);
    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

function appendSystemMessage(type, label, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = 'T';
    avatarDiv.style.fontSize = '12px';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const labelDiv = document.createElement('div');
    labelDiv.className = 'message-label';
    labelDiv.textContent = label;

    const textDiv = document.createElement('div');
    textDiv.innerHTML = formatContent(content);

    contentDiv.appendChild(labelDiv);
    contentDiv.appendChild(textDiv);
    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(contentDiv);
    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

function formatContent(text) {
    if (!text) return '';

    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(
        /(https?:\/\/[^\s<]+)/g,
        '<a href="$1" target="_blank" style="color: var(--cyan); text-decoration: underline;">$1</a>'
    );
    html = html.replace(/\n/g, '<br>');

    return html;
}

function formatToolCall(data) {
    let text = `Tool: ${data.tool}\n`;
    if (data.args && Object.keys(data.args).length > 0) {
        text += `Arguments:\n`;
        for (const [key, val] of Object.entries(data.args)) {
            text += `  ${key}: ${val}\n`;
        }
    }
    return text;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

// ── Confirmation Modal ───────────────────────────────────────────────────────
function showConfirmation(data) {
    pendingConfirmation = data.action_id;

    let bodyHtml = `<p>${data.content}</p>`;
    if (data.details && Object.keys(data.details).length > 0) {
        bodyHtml += '<br><strong>Details:</strong><br>';
        for (const [key, val] of Object.entries(data.details)) {
            bodyHtml += `<div>${key}: ${val}</div>`;
        }
    }

    confirmBody.innerHTML = bodyHtml;
    confirmOverlay.classList.add('active');
}

function resolveConfirmation(approved) {
    if (!pendingConfirmation) return;

    ws.send(JSON.stringify({
        type: 'confirm',
        action_id: pendingConfirmation,
        approved: approved,
    }));

    confirmOverlay.classList.remove('active');
    addActivity(approved ? '✅' : '🚫', approved ? 'Action approved' : 'Action denied');
    pendingConfirmation = null;
}

// ── Activity Feed ────────────────────────────────────────────────────────────
function addActivity(icon, text) {
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <span class="activity-icon">${icon}</span>
        <span class="activity-text">${text}</span>
    `;
    activityFeed.appendChild(item);

    while (activityFeed.children.length > 30) {
        activityFeed.removeChild(activityFeed.firstChild);
    }

    activityFeed.scrollTop = activityFeed.scrollHeight;
}

// ── System Stats Polling ─────────────────────────────────────────────────────
async function updateSystemStats() {
    if (!authToken) return;
    try {
        const res = await apiFetch('/api/system');
        const data = await res.json();

        document.getElementById('cpu-val').textContent = data.cpu;
        document.getElementById('ram-val').textContent = data.ram;
        document.getElementById('disk-val').textContent = data.disk;
        document.getElementById('time-val').textContent = data.time;
        document.getElementById('date-val').textContent = data.date;

        document.getElementById('cpu-bar').style.width = `${data.cpu}%`;
        document.getElementById('ram-bar').style.width = `${data.ram}%`;
        document.getElementById('disk-bar').style.width = `${data.disk}%`;

        colorCodeBar('cpu-bar', data.cpu);
        colorCodeBar('ram-bar', data.ram);
        colorCodeBar('disk-bar', data.disk);
    } catch (e) {
    }
}

function colorCodeBar(id, value) {
    const bar = document.getElementById(id);
    if (value > 90) {
        bar.style.background = 'linear-gradient(90deg, var(--red), #ff6b6b)';
    } else if (value > 70) {
        bar.style.background = 'linear-gradient(90deg, var(--amber), #fbbf24)';
    } else {
        bar.style.background = 'linear-gradient(90deg, var(--cyan-dim), var(--cyan))';
    }
}

// ── Load Tools ───────────────────────────────────────────────────────────────
async function loadTools() {
    try {
        const res = await apiFetch('/api/tools');
        const tools = await res.json();

        toolCount.textContent = tools.length;
        toolList.innerHTML = '';

        tools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'tool-item';
            item.innerHTML = `
                <span class="tool-dot"></span>
                <span>${tool.name.replace(/_/g, ' ')}</span>
            `;
            item.title = tool.description;
            toolList.appendChild(item);
        });
    } catch (e) {
        console.error('Failed to load tools:', e);
    }
}

// ── Load Conversations ───────────────────────────────────────────────────────
async function loadConversations() {
    try {
        const res = await apiFetch('/api/conversations');
        const convs = await res.json();
        
        if (!chatHistoryList) return;
        chatHistoryList.innerHTML = '';
        
        convs.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'chat-history-item';
            item.dataset.id = conv.id;
            
            const date = new Date(conv.updated_at);
            const dateStr = !isNaN(date.getTime()) ? date.toLocaleString() : conv.updated_at;
            
            item.innerHTML = `
                <div class="chat-history-header">
                    <div class="chat-history-title">${conv.title || 'New Conversation'}</div>
                    <div class="chat-history-actions">
                        <button class="chat-action-btn edit-btn" title="Edit Title">✎</button>
                        <button class="chat-action-btn del-btn" title="Delete">🗑</button>
                    </div>
                </div>
                <div class="chat-history-date">${dateStr}</div>
            `;
            
            const editBtn = item.querySelector('.edit-btn');
            editBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const newTitle = prompt("Enter new conversation name:", conv.title || "New Conversation");
                if (newTitle && newTitle.trim()) {
                    await apiFetch(`/api/conversations/${conv.id}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({title: newTitle.trim()})
                    });
                    loadConversations();
                }
            });

            const delBtn = item.querySelector('.del-btn');
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm("Are you sure you want to delete this conversation?")) {
                    await apiFetch(`/api/conversations/${conv.id}`, { method: 'DELETE' });
                    if (item.classList.contains('active')) {
                        newChatBtn.click();
                    } else {
                        loadConversations();
                    }
                }
            });
            
            item.addEventListener('click', async () => {
                document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                
                const msgRes = await apiFetch(`/api/conversations/${conv.id}/messages`);
                if (msgRes.ok) {
                    const messages = await msgRes.json();
                    loadConversationMessagesUI(messages, conv.id);
                }
            });
            
            chatHistoryList.appendChild(item);
        });
    } catch (e) {
        console.error('Failed to load conversations:', e);
    }
}

function loadConversationMessagesUI(messages, id) {
    messagesContainer.innerHTML = '';
    if (welcomeScreen) welcomeScreen.style.display = 'none';
    
    if (ws && isConnected) {
        ws.send(JSON.stringify({ type: 'load_conversation', id: id }));
    }
    
    messages.forEach(msg => {
        if (msg.role === 'user' || msg.role === 'assistant') {
            if (msg.content) appendMessage(msg.role, msg.content);
            if (msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0) {
                const tc = msg.tool_calls[0].function;
                appendSystemMessage('tool-call', `🔧 TOOL: ${tc.name}`, formatToolCall({tool: tc.name, args: tc.arguments}));
            }
        } else if (msg.role === 'tool') {
            appendSystemMessage('tool-result', `✅ RESULT: ${msg.tool_name || 'tool'}`, msg.content);
        }
    });
    addActivity('🔄', 'Loaded previous conversation');
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('open');
    }
}

// ── Auth Logic ───────────────────────────────────────────────────────────────
function handleLogout() {
    authToken = null;
    localStorage.removeItem('tatsu_token');
    appContainer.classList.add('hidden');
    loginOverlay.classList.remove('hidden');
    if (ws) ws.close();
}

async function handleLogin() {
    const pwd = loginPassword.value;
    if (!pwd) return;
    
    loginBtn.disabled = true;
    loginBtn.textContent = 'Verifying...';
    
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pwd})
        });
        
        if (res.ok) {
            const data = await res.json();
            authToken = data.token;
            localStorage.setItem('tatsu_token', authToken);
            
            loginOverlay.classList.add('hidden');
            appContainer.classList.remove('hidden');
            initializeApp();
        } else {
            loginError.textContent = 'Invalid password.';
        }
    } catch (e) {
        loginError.textContent = 'Connection error.';
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
}

loginBtn.addEventListener('click', handleLogin);
loginPassword.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleLogin();
});

// ── Status Updates ───────────────────────────────────────────────────────────
async function loadStatus() {
    try {
        const res = await apiFetch('/api/status');
        const data = await res.json();

        modelName.textContent = data.model;

        if (data.llm_connected) {
            addActivity('🤖', `LLM connected: ${data.model}`);
        } else {
            addActivity('⚠️', `LLM not connected. Run: ollama pull ${data.model}`);
        }
    } catch (e) {
        console.error('Failed to load status:', e);
    }
}

// ── Event Listeners ──────────────────────────────────────────────────────────

// Send button
sendBtn.addEventListener('click', sendMessage);

// Enter to send, Shift+Enter for new line
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

// Confirmation buttons
btnApprove.addEventListener('click', () => resolveConfirmation(true));
btnDeny.addEventListener('click', () => resolveConfirmation(false));

// Sidebar toggle
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    sidebar.classList.toggle('open');
}

sidebarToggle.addEventListener('click', toggleSidebar);
if (historyBtn) historyBtn.addEventListener('click', () => {
    toggleSidebar();
    // Scroll sidebar to history list
    if (chatHistoryList) {
        chatHistoryList.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});

// New chat
newChatBtn.addEventListener('click', () => {
    // Clear messages
    messagesContainer.innerHTML = '';
    if (welcomeScreen) {
        messagesContainer.appendChild(welcomeScreen);
        welcomeScreen.style.display = '';
    }
    
    // Deselect active chat in sidebar
    document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
    
    addActivity('✦', 'New conversation started');
    
    // Switch context without reconnecting WebSocket
    if (ws && isConnected) {
        ws.send(JSON.stringify({ type: 'new_conversation' }));
    }
    
    // Refresh conversation list to show the new empty conversation
    setTimeout(loadConversations, 500);
});

// Quick actions
document.querySelectorAll('.quick-action').forEach(btn => {
    btn.addEventListener('click', () => {
        const msg = btn.dataset.msg;
        if (msg) {
            messageInput.value = msg;
            sendMessage();
        }
    });
});

// ── Initialize ───────────────────────────────────────────────────────────────
function initializeApp() {
    connectWebSocket();
    loadStatus();
    loadTools();
    loadConversations();
    updateSystemStats();
}

document.addEventListener('DOMContentLoaded', async () => {
    // Check if we need to show login or if we are already authenticated
    try {
        if (authToken) {
            // Verify token by calling status
            const res = await apiFetch('/api/status');
            if (res.ok) {
                appContainer.classList.remove('hidden');
                initializeApp();
            }
        } else {
            loginOverlay.classList.remove('hidden');
        }
    } catch (e) {
        // Handled by apiFetch
    }
    
    // Poll system stats every 2 seconds
    setInterval(updateSystemStats, 2000);
});
