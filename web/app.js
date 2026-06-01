/* ═══════════════════════════════════════════════════
   NexusMind — Client-Side JavaScript
   Features: Chat, Neural Network Viz, Settings,
   Personalization, Message Actions, Themes
   ═══════════════════════════════════════════════════ */

// ─── State ──────────────────────────────────────────
let sessionId = localStorage.getItem('nexusmind_sid') || 'session_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('nexusmind_sid', sessionId);

let ws = null;
let isConnected = false;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 30000;
let etaTimer = null;
let avgGenTime = 5;
const uploadedFiles = [];
let nnState = null; // Fix for Send/Connect issues

let isNNActive = false;
// User settings
let userSettings = {
    username: 'User',
    avatar: '🧑‍💻',
    theme: 'midnight',
    custom_instructions: '',
    show_thinking: true,
    auto_scroll: true,
};

// ─── DOM Elements ───────────────────────────────────
const messageInput = document.getElementById('messageInput');
const messagesContainer = document.getElementById('messagesContainer');
const openSidebar = document.getElementById('openSidebar');
const sidebar = document.getElementById('sidebar');
const newChatBtn = document.getElementById('newChatBtn');
const sessionList = document.getElementById('sessionList');
const setWorkspaceBtn = document.getElementById('setWorkspaceBtn');
const workspacePathDisplay = document.getElementById('workspacePath');
const projectExplorer = document.getElementById('projectExplorer');
const modelProfileSelect = document.getElementById('modelProfileSelect');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const toolsList = document.getElementById('toolsList');
const toolCount = document.getElementById('toolCount');
const wsStatus = document.getElementById('wsStatus');
const modelStatus = document.getElementById('modelStatus');
const lastConfidence = document.getElementById('lastConfidence');
const sidebarToggle = document.getElementById('toggleSidebar');
const mobileMenu = document.getElementById('mobileMenu');
const fileUpload = document.getElementById('fileUpload');
const uploadedFilesEl = document.getElementById('uploadedFiles');
const wifiIndicator = document.getElementById('wifiIndicator');
const performanceBars = document.getElementById('performanceBars');
const dbSizeEl = document.getElementById('dbSize');
const toolsOverlay = document.getElementById('toolsOverlay');

let toolsLoaded = false;
let toolsByName = {};
let selectedToolName = null;
let scoutFindings = [];
let activeTools = new Set();

// ─── Classes ─────────────────────────────────────────

// Neural Cache 3D Visualization
class NeuralCacheSphere3D {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;
        if (typeof THREE === 'undefined') {
            console.error('Three.js not loaded. 3D Visualization disabled.');
            return;
        }

        this.steps = [];
        this.nodes = [];
        this.links = [];

        // Settings
        this.baseRadius = 40;
        this.zoom = 1.0;
        this.speed = 1.0;
        this.isPaused = false;

        try {
            this.initThreeJS();
            this.animate = this.animate.bind(this);
            this.animate();
        } catch (e) {
            console.error('Failed to initialize 3D visualization:', e);
        }
    }

    initThreeJS() {
        this.scene = new THREE.Scene();

        const width = this.container.clientWidth || 600;
        const height = this.container.clientHeight || 400;

        this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
        this.camera.position.z = 150;

        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0xab68ff, 1);
        pointLight.position.set(50, 50, 50);
        this.scene.add(pointLight);

        const pointLight2 = new THREE.PointLight(0x00f2fe, 1);
        pointLight2.position.set(-50, -50, 50);
        this.scene.add(pointLight2);

        // Group to hold nodes and rotate
        this.group = new THREE.Group();
        this.scene.add(this.group);

        // Handle resize
        window.addEventListener('resize', () => {
            if (!this.container) return;
            const w = this.container.clientWidth;
            const h = this.container.clientHeight;
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(w, h);
        });
    }

    addStep(stepText) {
        if (!stepText || stepText.trim() === '' || !this.group) return;

        this.steps.push(stepText);

        // Create new node
        const geometry = new THREE.SphereGeometry(1.5, 16, 16);

        // Color based on depth/step count
        const colors = [0x00f2fe, 0xab68ff, 0xf97316, 0x22c55e];
        const color = colors[this.nodes.length % colors.length];

        const material = new THREE.MeshPhongMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.5,
            shininess: 100
        });

        const mesh = new THREE.Mesh(geometry, material);

        // Position on a sphere using Fibonacci lattice
        const n = this.nodes.length;
        const total = Math.max(n + 10, 50);
        const phi = Math.acos(1 - 2 * (n + 0.5) / total);
        const theta = Math.PI * (1 + Math.sqrt(5)) * n;

        mesh.position.x = this.baseRadius * Math.cos(theta) * Math.sin(phi);
        mesh.position.y = this.baseRadius * Math.sin(theta) * Math.sin(phi);
        mesh.position.z = this.baseRadius * Math.cos(phi);

        // Add to group
        this.group.add(mesh);
        this.nodes.push(mesh);

        // Create links to recent nodes
        if (this.nodes.length > 1) {
            const material = new THREE.LineBasicMaterial({
                color: 0xffffff,
                transparent: true,
                opacity: 0.15
            });

            const numConnections = Math.min(Math.floor(Math.random() * 3) + 1, this.nodes.length - 1);
            for (let i = 0; i < numConnections; i++) {
                const targetIdx = this.nodes.length - 1 - Math.floor(Math.random() * Math.min(5, this.nodes.length - 1)) - 1;
                if (targetIdx >= 0) {
                    const points = [];
                    points.push(mesh.position);
                    points.push(this.nodes[targetIdx].position);

                    const geometry = new THREE.BufferGeometry().setFromPoints(points);
                    const line = new THREE.Line(geometry, material);
                    this.group.add(line);
                    this.links.push(line);
                }
            }
        }

        this.updateStats();

        // Add status dot activity
        const indicator = document.getElementById('neuralCacheIndicator');
        if (indicator) {
            indicator.classList.add('active');
            clearTimeout(this.indicatorTimeout);
            this.indicatorTimeout = setTimeout(() => {
                indicator.classList.remove('active');
            }, 500);
        }
    }

    updateStats() {
        const stats = document.getElementById('cacheStats');
        if (stats) {
            stats.textContent = `Nodes: ${this.nodes.length} | Depth: ${Math.floor(this.nodes.length / 3)}`;
        }
    }

    setZoom(value) {
        if (this.group) {
            this.zoom = value;
            this.group.scale.set(this.zoom, this.zoom, this.zoom);
        }
    }

    setSpeed(value) {
        this.speed = value;
    }

    togglePause() {
        this.isPaused = !this.isPaused;
    }

    clear() {
        this.steps = [];
        if (!this.group) return;

        for (const node of this.nodes) {
            this.group.remove(node);
            node.geometry.dispose();
            node.material.dispose();
        }

        for (const link of this.links) {
            this.group.remove(link);
            link.geometry.dispose();
            link.material.dispose();
        }

        this.nodes = [];
        this.links = [];
        this.updateStats();
    }

    animate() {
        this.animationFrameId = requestAnimationFrame(this.animate);
        if (!this.renderer || !this.scene || !this.camera) return;

        // Only render if visible
        const overlay = document.getElementById('neuralCacheOverlay');
        if (this.container && overlay && overlay.style.display !== 'none') {
            if (!this.isPaused && this.group) {
                // Auto rotate
                this.group.rotation.y += 0.005 * this.speed;
                this.group.rotation.x += 0.002 * this.speed;

                // Pulse effect on most recent node
                if (this.nodes.length > 0) {
                    const lastNode = this.nodes[this.nodes.length - 1];
                    const scale = 1 + 0.5 * Math.sin(Date.now() * 0.005);
                    lastNode.scale.set(scale, scale, scale);
                }
            }

            this.renderer.render(this.scene, this.camera);
        }
    }

    stop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
    }
}

// ─── Initialize ─────────────────────────────────────
// Utility logic moved to bottom

// ─── Tools Playground ─────────────────────────────────

async function loadToolsIfNeeded() {
    if (toolsLoaded) return;
    try {
        const resp = await fetch('/api/tools');
        const data = await resp.json();
        const pane = document.getElementById('toolsListPane');
        if (!pane) return;
        pane.innerHTML = '';

        toolsByName = {};
        const byCategory = data.categories || {};
        const schemas = data.tools || [];
        for (const t of schemas) {
            toolsByName[t.name] = t;
        }

        Object.keys(byCategory).sort().forEach(cat => {
            const label = document.createElement('div');
            label.className = 'tools-category-label';
            label.textContent = cat;
            pane.appendChild(label);

            byCategory[cat].sort().forEach(name => {
                const item = document.createElement('div');
                item.className = 'tools-list-item';
                item.dataset.toolName = name;
                const title = document.createElement('span');
                title.textContent = name;
                const chevron = document.createElement('span');
                chevron.textContent = '›';
                chevron.style.opacity = '0.5';
                item.appendChild(title);
                item.appendChild(chevron);
                item.onclick = () => selectTool(name);
                pane.appendChild(item);
            });
        });

        toolsLoaded = true;
    } catch (e) {
        console.error('Failed to load tools:', e);
    }
}

function openToolsOverlay() {
    if (!toolsOverlay) return;
    toolsOverlay.classList.add('active');
    loadToolsIfNeeded();
}

function selectTool(name) {
    selectedToolName = name;
    const detailEmpty = document.getElementById('toolsDetailEmpty');
    const detail = document.getElementById('toolsDetail');
    const nameEl = document.getElementById('toolDetailName');
    const catEl = document.getElementById('toolDetailCategory');
    const schemaEl = document.getElementById('toolSchemaJson');
    const argsInput = document.getElementById('toolArgsInput');
    const resultEl = document.getElementById('toolResultJson');
    const statusEl = document.getElementById('toolRunStatus');

    document.querySelectorAll('.tools-list-item').forEach(it => {
        it.classList.toggle('active', it.dataset.toolName === name);
    });

    const tool = toolsByName[name];
    if (!tool) return;

    if (detailEmpty) detailEmpty.style.display = 'none';
    if (detail) detail.style.display = 'flex';

    if (nameEl) nameEl.textContent = tool.name;
    if (catEl) catEl.textContent = tool.category || '';
    if (schemaEl) schemaEl.textContent = JSON.stringify(tool.parameters || {}, null, 2);
    if (argsInput) {
        const props = (tool.parameters && tool.parameters.properties) || {};
        const initial = {};
        Object.keys(props).forEach(k => {
            if ('default' in props[k]) {
                initial[k] = props[k].default;
            }
        });
        argsInput.value = Object.keys(initial).length ? JSON.stringify(initial, null, 2) : '{}';
    }
    if (resultEl) resultEl.textContent = '';
    if (statusEl) statusEl.textContent = '';
}

async function runSelectedTool() {
    const statusEl = document.getElementById('toolRunStatus');
    if (!selectedToolName) {
        if (statusEl) statusEl.textContent = 'Select a tool first.';
        return;
    }
    const argsInput = document.getElementById('toolArgsInput');
    const resultEl = document.getElementById('toolResultJson');
    let args = {};
    try {
        args = argsInput.value.trim() ? JSON.parse(argsInput.value) : {};
    } catch (e) {
        if (statusEl) statusEl.textContent = 'Invalid JSON in arguments.';
        return;
    }
    if (statusEl) statusEl.textContent = 'Running...';
    try {
        const resp = await fetch('/api/tools/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: selectedToolName, args }),
        });
        const data = await resp.json();
        if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
        if (statusEl) statusEl.textContent = data.success ? 'Success' : 'Error';
    } catch (e) {
        console.error('Tool run failed:', e);
        if (statusEl) statusEl.textContent = 'Request failed.';
    }
}


// ─── User Settings ──────────────────────────────────

async function loadUserSettings() {
    try {
        const resp = await fetch('/api/user/settings');
        const data = await resp.json();
        userSettings = { ...userSettings, ...data };
    } catch (e) {
        // Use defaults from localStorage
        const saved = localStorage.getItem('nexusmind_settings');
        if (saved) userSettings = { ...userSettings, ...JSON.parse(saved) };
    }
    applySettings();
}

function applySettings() {
    document.documentElement.setAttribute('data-theme', userSettings.theme || 'midnight');
    const headerAvatar = document.getElementById('headerAvatar');
    const headerUsername = document.getElementById('headerUsername');
    if (headerAvatar) headerAvatar.textContent = userSettings.avatar || '🧑‍💻';
    if (headerUsername) headerUsername.textContent = userSettings.username || 'User';
}

function populateSettingsForm() {
    document.getElementById('settingsUsername').value = userSettings.username || '';
    document.getElementById('settingsInstructions').value = userSettings.custom_instructions || '';
    document.getElementById('settingsShowThinking').checked = userSettings.show_thinking !== false;
    document.getElementById('settingsAutoScroll').checked = userSettings.auto_scroll !== false;

    // Select current avatar
    document.querySelectorAll('.avatar-option').forEach(opt => {
        opt.classList.toggle('selected', opt.dataset.avatar === userSettings.avatar);
    });

    // Select current theme
    document.querySelectorAll('.theme-option').forEach(opt => {
        opt.classList.toggle('selected', opt.dataset.theme === userSettings.theme);
    });
}

async function saveSettings() {
    const selectedAvatar = document.querySelector('.avatar-option.selected');
    const selectedTheme = document.querySelector('.theme-option.selected');

    userSettings = {
        username: document.getElementById('settingsUsername').value || 'User',
        avatar: selectedAvatar?.dataset.avatar || '🧑‍💻',
        theme: selectedTheme?.dataset.theme || 'midnight',
        custom_instructions: document.getElementById('settingsInstructions').value,
        show_thinking: document.getElementById('settingsShowThinking').checked,
        auto_scroll: document.getElementById('settingsAutoScroll').checked,
    };

    localStorage.setItem('nexusmind_settings', JSON.stringify(userSettings));
    applySettings();

    try {
        await fetch('/api/user/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userSettings),
        });
    } catch (e) {
        console.error('Failed to save settings to server:', e);
    }

    document.getElementById('settingsOverlay').classList.remove('active');
}


// ─── Project & Workspace ────────────────────────────

function initProject(template) {
    const payload = { template };
    fetch('/api/workspace/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).then(r => r.json()).then(data => {
        if (data.success) fetchFileTree();
    }).catch(e => console.error('Init project failed:', e));
}

function switchModelProfile(profile) {
    fetch('/api/model/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile }),
    }).then(r => r.json()).then(data => {
        if (data.status === 'success') fetchStatus();
    }).catch(e => console.error('Switch model failed:', e));
}

async function loadSessions() {
    try {
        const resp = await fetch('/api/sessions');
        const data = await resp.json();
        if (data.sessions) renderSessionList(data.sessions);
    } catch (e) { console.error('Failed to load sessions:', e); }
}

async function loadWorkspace() {
    try {
        const files = await fetchFileTree();
    } catch (e) { }
}

async function fetchFileTree() {
    try {
        const resp = await fetch('/api/workspace/files');
        const data = await resp.json();
        if (data.files && projectExplorer) {
            projectExplorer.innerHTML = '';
            renderFileTree(data.files, projectExplorer);
        }
    } catch (e) { }
}

function renderFileTree(files, container = projectExplorer) {
    if (!files || !container) return;
    files.forEach(item => {
        const div = document.createElement('div');
        div.className = `tree-item ${item.type === 'directory' ? 'folder' : 'file'}`;
        div.innerHTML = `<span class="item-icon">${item.type === 'directory' ? '📁' : '📄'}</span> ${item.name}`;
        container.appendChild(div);
        if (item.children && item.children.length > 0) {
            const subContainer = document.createElement('div');
            subContainer.style.paddingLeft = '12px';
            container.appendChild(subContainer);
            renderFileTree(item.children, subContainer);
        }
    });
}

function renderSessionList(sessions) {
    if (!sessionList) return;
    sessionList.innerHTML = '';
    sessions.forEach(s => {
        const item = document.createElement('div');
        item.className = `session-item-minimal ${s.session_id === sessionId ? 'active' : ''}`;
        item.innerHTML = `
            <i class="fas fa-message"></i>
            <div class="session-title">${s.title || 'Untitled Chat'}</div>
            <button class="delete-session-btn" title="Delete Chat" onclick="event.stopPropagation(); deleteSession('${s.session_id}')">
                <i class="fas fa-trash"></i>
            </button>
        `;
        item.onclick = () => switchSession(s.session_id);
        sessionList.appendChild(item);
    });
}


// ─── Session Management ─────────────────────────────

let lastLoadedSession = null;
// activeTools is already declared at the top

function sanitizeText(text) {
    if (!text) return '';
    return text.replace(/\\\[|\\\]|\\\(|\\\)/g, '')
        .replace(/\$\$[\s\S]*?\$\$/g, m => m.replace(/\$/g, ''))
        .replace(/\$/g, '');
}

function activateTool(name) {
    activeTools.add(name);
    document.querySelectorAll('.tool-tag').forEach(tag => {
        if (tag.textContent.trim() === name) tag.classList.add('glowing');
    });
}

function deactivateTool(name) {
    if (name) {
        activeTools.delete(name);
    } else {
        activeTools.clear();
    }
    document.querySelectorAll('.tool-tag').forEach(tag => {
        if (!name || tag.textContent.trim() === name) tag.classList.remove('glowing');
    });
}

async function deleteSession(id) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    try {
        await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
        if (id === sessionId) {
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('nexusmind_sid', sessionId);
            messagesContainer.innerHTML = '';
            clearChat();
            reconnectWebSocket();
        }
        loadSessions();
    } catch (e) { console.error("Failed to delete session", e); }
}

function createNewChat() {
    sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('nexusmind_sid', sessionId);
    messagesContainer.innerHTML = '';
    currentStreamingMsg = null;
    currentStreamingContent = "";
    lastLoadedSession = null;
    clearChat();
    reconnectWebSocket();
    loadSessions();
}

async function switchSession(id) {
    if (id === lastLoadedSession) return;
    sessionId = id;
    lastLoadedSession = id;
    localStorage.setItem('nexusmind_sid', sessionId);

    messagesContainer.innerHTML = '';
    reconnectWebSocket();
    loadSessions();

    try {
        const resp = await fetch(`/api/sessions/${id}`);
        const data = await resp.json();
        messagesContainer.innerHTML = '';
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(m => {
                appendMessage(m.role, m.content, { skip_anim: true });
            });
        } else {
            clearChat();
        }
    } catch (e) { console.error("Failed to switch session", e); }
}


// ─── WebSocket ──────────────────────────────────────

function reconnectWebSocket() {
    if (ws) {
        ws.onclose = null;
        ws.close();
    }
    connect();
}

function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/chat/${sessionId}`);

    ws.onopen = () => {
        isConnected = true;
        reconnectDelay = 1000;
        if (wsStatus) wsStatus.classList.add('connected');
        if (wifiIndicator) wifiIndicator.classList.add('active');
        console.log('[NexusMind] Connected');
        fetchStatus();
    };

    ws.onclose = () => {
        isConnected = false;
        if (wsStatus) wsStatus.classList.remove('connected');
        if (wifiIndicator) wifiIndicator.classList.remove('active');
        console.log(`[NexusMind] Disconnected, reconnecting in ${reconnectDelay / 1000}s...`);
        setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
    };

    ws.onerror = (e) => {
        console.error('[NexusMind] WebSocket error:', e);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (err) {
            console.error('[NexusMind] Failed to parse message:', err, event.data);
        }
    };
}


// ─── Message Handling ───────────────────────────────

async function loadHistory() {
    try {
        const resp = await fetch(`/api/history/${sessionId}`);
        const data = await resp.json();
        if (data.history && data.history.length > 0) {
            const welcome = document.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            data.history.forEach(msg => {
                appendMessage(msg.role, msg.content, { skipHistory: true });
            });
            if (window.MathJax) MathJax.typesetPromise();
            document.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el));
        }
    } catch (err) { console.error('[NexusMind] Failed to load history:', err); }
}

function handleMessage(data) {
    switch (data.type) {
        case 'reasoning_step':
            if (neuralCache) neuralCache.addStep(data.step);
            if (neuralCacheViz) neuralCacheViz.addStep(data.step);
            showStatus(data.step);
            break;
        case 'chunk':
            if (performanceBars) performanceBars.classList.add('active');
            handleChunk(data.content);
            break;

        case 'message':
            if (performanceBars) performanceBars.classList.remove('active');
            deactivateTool();
            hideStatus();
            finalizeMessage('assistant', data.content, {
                confidence: data.confidence,
                confidence_score: data.confidence_score,
                cached: data.cached,
                tools: data.tools_used || [],
                gen_time: data.gen_time,
                tps: data.tps
            });
            updateConfidence(data.confidence_score);
            if (data.gen_time) {
                avgGenTime = (avgGenTime * 0.7) + (data.gen_time * 0.3);
            }
            stopBattery();
            break;

        case 'status':
            showStatus(data.content);
            break;

        case 'scout_alert':
            handleScoutAlert(data);
            break;

        case 'tool_call':
            activateTool(data.tool);
            appendToolCall(data.tool, data.args, 'executing');
            break;

        case 'tool_result':
            deactivateTool(data.tool);
            updateToolCall(data.tool, data.result);
            break;

        case 'error':
            hideStatus();
            appendMessage('assistant', `⚠️ ${data.content}`, { isError: true });
            stopBattery();
            break;
    }
}


// ─── Battery / ETA ──────────────────────────────────

function startBattery() {
    const container = document.getElementById('etaContainer');
    const level = document.getElementById('batteryLevel');
    const text = document.getElementById('etaText');
    if (!container || !level || !text) return;

    container.style.display = 'flex';
    const startTime = Date.now();
    const duration = avgGenTime * 1000;
    level.style.width = '2%';
    level.style.background = '#ff4b4b';

    if (etaTimer) clearInterval(etaTimer);
    etaTimer = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(95, (elapsed / duration) * 100);
        level.style.width = `${progress}%`;
        if (progress > 40) level.style.background = '#ffaa00';
        if (progress > 80) level.style.background = '#00f2fe';
        const remaining = Math.max(1, Math.round((duration - elapsed) / 1000));
        text.textContent = progress < 90 ? `ETA: ${remaining}s` : "Wrapping up...";
    }, 100);
}

function stopBattery() {
    const container = document.getElementById('etaContainer');
    const level = document.getElementById('batteryLevel');
    if (!container || !level) return;
    level.style.width = '100%';
    level.style.background = '#00f2fe';
    setTimeout(() => {
        container.style.display = 'none';
        if (etaTimer) clearInterval(etaTimer);
    }, 1000);
}


// ─── Send Message ───────────────────────────────────

function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    if (!isConnected) {
        showToast('NexusMind is connecting... please wait.', 'warning');
        reconnectWebSocket();
        return;
    }

    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.style.display = 'none';

    appendMessage('user', text);
    ws.send(JSON.stringify({ type: 'message', content: text }));

    messageInput.value = '';
    messageInput.style.height = 'auto';
    startBattery();
}

function sendQuick(text) {
    messageInput.value = text;
    sendMessage();
}

function exportChat() {
    window.location.href = `/api/export/${sessionId}`;
}


// ─── Message Rendering ─────────────────────────────

let currentStreamingMsg = null;
let currentStreamingContent = "";
let isThinking = false;
let streamingThinkBlock = null;
let streamingAnswerBubble = null;

function handleChunk(content) {
    if (!currentStreamingMsg) {
        currentStreamingMsg = appendMessage('assistant', '', { isStreaming: true });
        currentStreamingMsg.classList.add('streaming-active');

        // Ensure thinking block is initialized if it starts with <think>
        streamingThinkBlock = null;
        streamingAnswerBubble = currentStreamingMsg.querySelector('.message-content');
    }
    currentStreamingContent += content;

    const { thinkContent, cleanContent } = parseThinkBlock(currentStreamingContent);

    // Live update thinking block if present
    if (thinkContent && userSettings.show_thinking) {
        let thinkDiv = currentStreamingMsg.querySelector('.thinking-block');
        if (!thinkDiv) {
            thinkDiv = document.createElement('div');
            thinkDiv.className = 'thinking-block stylish expanded';
            thinkDiv.innerHTML = `
                <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span class="thinking-chevron">▶</span> <span class="thinking-label">Pensiero (Thinking)...</span>
                </div>
                <div class="thinking-body"></div>
            `;
            currentStreamingMsg.prepend(thinkDiv);
        }
        thinkDiv.querySelector('.thinking-body').textContent = thinkContent;
    }

    const contentEl = currentStreamingMsg.querySelector('.message-content');
    contentEl.innerHTML = renderMarkdown(sanitizeText(cleanContent || currentStreamingContent));

    if (userSettings.auto_scroll) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function finalizeMessage(role, content, meta = {}) {
    if (currentStreamingMsg) {
        currentStreamingMsg.classList.remove('streaming-active');
        setTimeout(loadSessions, 500);

        const metaDiv = currentStreamingMsg.querySelector('.message-meta');
        if (metaDiv) {
            let metaHtml = '';
            if (meta.gen_time) {
                let timeStr = `⏱️ ${meta.gen_time}s`;
                if (meta.tps) timeStr += ` (${meta.tps} t/s)`;
                metaHtml += `<span class="meta-tag">${timeStr}</span>`;
            }
            if (meta.confidence) metaHtml += `<span class="meta-confidence">${meta.confidence}</span>`;
            if (meta.cached) metaHtml += `<span class="meta-tag cached">⚡ Cached</span>`;
            if (meta.tools && meta.tools.length > 0) {
                meta.tools.forEach(t => metaHtml += `<span class="meta-tag">🔧 ${t}</span>`);
            }
            metaDiv.innerHTML = metaHtml;
        }

        currentStreamingMsg.classList.remove('streaming', 'draft-token');
        currentStreamingMsg.classList.add('new');

        const { thinkContent, cleanContent } = parseThinkBlock(content);
        const bubble = currentStreamingMsg.querySelector('.message-content');
        bubble.innerHTML = renderMarkdown(cleanContent || content);

        // Ensure thinking block is finalized
        if (thinkContent && userSettings.show_thinking) {
            let thinkDiv = currentStreamingMsg.querySelector('.thinking-block');
            if (thinkDiv) {
                thinkDiv.classList.remove('expanded'); // Collapse on finish
                thinkDiv.querySelector('.thinking-body').textContent = thinkContent;
            } else {
                // Fallback if it wasn't created during streaming
                const thinkBlock = document.createElement('div');
                thinkBlock.className = 'thinking-block stylish';
                thinkBlock.innerHTML = `
                    <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                        <span class="thinking-chevron">▶</span> <span class="thinking-label">Pensiero (Thinking)...</span>
                    </div>
                    <div class="thinking-body">${thinkContent}</div>
                `;
                currentStreamingMsg.prepend(thinkBlock);
            }
        }

        currentStreamingMsg = null;
        currentStreamingContent = "";
        isThinking = false;
        streamingThinkBlock = null;
        streamingAnswerBubble = null;
    } else {
        appendMessage(role, content, meta);
    }
    loadSessions();
}

function parseThinkBlock(text) {
    if (!text) return { thinkContent: null, cleanContent: '' };

    // Check for complete block first
    const thinkMatch = text.match(/<think>([\s\S]*?)<\/think>/i);
    if (thinkMatch) {
        const thinkContent = thinkMatch[1].trim();
        const cleanContent = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
        return { thinkContent, cleanContent };
    }

    // Check for unclosed block (streaming)
    const openMatch = text.match(/<think>([\s\S]*)$/i);
    if (openMatch) {
        return {
            thinkContent: openMatch[1].trim(),
            cleanContent: text.substring(0, text.indexOf('<think>')).trim()
        };
    }

    return { thinkContent: null, cleanContent: text };
}

function appendMessage(role, content, meta = {}) {
    content = sanitizeText(content);
    const { thinkContent, cleanContent } = parseThinkBlock(content);

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    if (!meta.skip_anim) msgDiv.classList.add('new');

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? (userSettings.avatar || '👤') : '🧠';

    const contentDiv = document.createElement('div');
    contentDiv.style.maxWidth = '100%';

    // Thinking block
    if (role === 'assistant' && thinkContent && userSettings.show_thinking) {
        const thinkBlock = document.createElement('div');
        thinkBlock.className = 'thinking-block stylish';
        const header = document.createElement('div');
        header.className = 'thinking-header';
        header.innerHTML = '<span class="thinking-chevron">▶</span> <span class="thinking-label">Pensiero (Thinking)...</span>';
        header.onclick = () => thinkBlock.classList.toggle('expanded');
        const body = document.createElement('div');
        body.className = 'thinking-body';
        body.textContent = thinkContent;
        thinkBlock.appendChild(header);
        thinkBlock.appendChild(body);
        contentDiv.appendChild(thinkBlock);
    }

    const bubble = document.createElement('div');
    bubble.className = 'message-content';
    bubble.innerHTML = renderMarkdown(cleanContent || content);
    contentDiv.appendChild(bubble);

    // Message Actions (copy, regenerate)
    if (role === 'assistant' && !meta.isError && !meta.isStreaming) {
        const actions = document.createElement('div');
        actions.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'msg-action-btn';
        copyBtn.title = 'Copy';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(cleanContent || content);
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => copyBtn.innerHTML = '<i class="fas fa-copy"></i>', 1500);
        };

        const regenBtn = document.createElement('button');
        regenBtn.className = 'msg-action-btn';
        regenBtn.title = 'Regenerate';
        regenBtn.innerHTML = '<i class="fas fa-rotate"></i>';
        regenBtn.onclick = () => {
            // Find the last user message and resend
            const msgs = messagesContainer.querySelectorAll('.message.user');
            if (msgs.length > 0) {
                const lastUser = msgs[msgs.length - 1].querySelector('.message-content');
                if (lastUser) {
                    sendQuick(lastUser.textContent);
                }
            }
        };

        actions.appendChild(copyBtn);
        actions.appendChild(regenBtn);
        contentDiv.appendChild(actions);
    }

    // Meta info for assistant messages
    if (role === 'assistant' && !meta.isError) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';

        if (meta.gen_time) {
            const timeTag = document.createElement('span');
            timeTag.className = 'meta-tag';
            let timeStr = `⏱️ ${meta.gen_time}s`;
            if (meta.tps) timeStr += ` (${meta.tps} t/s)`;
            timeTag.textContent = timeStr;
            metaDiv.appendChild(timeTag);
        }

        if (meta.confidence) {
            const confSpan = document.createElement('span');
            confSpan.className = 'meta-confidence';
            confSpan.textContent = meta.confidence;
            metaDiv.appendChild(confSpan);
        }

        if (meta.cached) {
            const cacheTag = document.createElement('span');
            cacheTag.className = 'meta-tag cached';
            cacheTag.textContent = '⚡ Cached';
            metaDiv.appendChild(cacheTag);
        }

        if (meta.tools && meta.tools.length > 0) {
            meta.tools.forEach(t => {
                const tag = document.createElement('span');
                tag.className = 'meta-tag';
                tag.textContent = `🔧 ${t}`;
                metaDiv.appendChild(tag);
            });
        }

        contentDiv.appendChild(metaDiv);
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);

    // Apply syntax highlighting to new code blocks
    msgDiv.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el));
    if (window.MathJax) MathJax.typesetPromise([msgDiv]);

    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function appendToolCall(toolName, args, status) {
    const div = document.createElement('div');
    div.className = 'tool-call';
    div.id = `tool-${toolName}-${Date.now()}`;

    const header = document.createElement('div');
    header.className = 'tool-call-header';
    header.innerHTML = `<span>🔧</span> ${toolName} <span style="font-weight:normal;color:var(--warning)">executing...</span>`;

    const body = document.createElement('div');
    body.className = 'tool-call-body';

    // Special loading indicator for image_generate
    if (toolName === 'image_generate') {
        body.innerHTML = `
            <div style="padding: 20px; text-align: center;">
                <div style="margin-bottom: 12px;">
                    <div class="loading-spinner" style="display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(0, 242, 254, 0.2); border-top-color: #00f2fe; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                </div>
                <div style="color: #9ca3af; font-size: 0.9rem;">
                    <div>🎨 Generating image...</div>
                    <div style="margin-top: 8px; font-size: 0.8rem; opacity: 0.7;">
                        <strong>Prompt:</strong> ${args.prompt?.substring(0, 60)}${args.prompt?.length > 60 ? '...' : ''}
                    </div>
                    <div style="margin-top: 4px; font-size: 0.8rem; opacity: 0.6;">
                        ⏱️ First image may take 30-120s on free tier
                    </div>
                </div>
            </div>
            <style>
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
        `;
    } else {
        body.textContent = JSON.stringify(args, null, 2);
    }

    div.appendChild(header);
    div.appendChild(body);

    const msgs = messagesContainer.querySelectorAll('.message.assistant');
    if (msgs.length > 0) {
        const last = msgs[msgs.length - 1];
        last.querySelector('.message-content')?.appendChild(div) || messagesContainer.appendChild(div);
    } else {
        messagesContainer.appendChild(div);
    }
    scrollToBottom();
}

function updateToolCall(toolName, result) {
    const toolDivs = document.querySelectorAll('.tool-call');
    for (const div of toolDivs) {
        const header = div.querySelector('.tool-call-header');
        if (!header || !header.textContent.includes(toolName)) continue;

        const success = result?.success !== false && !result?.error;
        const color = success ? 'var(--success)' : 'var(--error)';
        const label = success ? '✓ done' : '✗ failed';
        header.innerHTML = `<span>🔧</span> ${toolName} <span style="font-weight:normal;color:${color}">${label}</span>`;

        const body = div.querySelector('.tool-call-body');

        // Special handling for image_generate results
        if (toolName === 'image_generate' && result?.output) {
            const output_path = result.output;
            body.innerHTML = `
                <div style="padding: 10px; background: rgba(0, 242, 254, 0.05); border-radius: 8px;">
                    <img src="${output_path}" style="max-width: 100%; max-height: 400px; border-radius: 8px; margin: 10px 0;">
                    <div style="color: #9ca3af; font-size: 0.85rem; margin-top: 8px;">
                        <div>📊 Size: ${(result.size_bytes / 1024).toFixed(1)} KB</div>
                        <div>⚡ Model: ${result.model}</div>
                        ${result.tier ? `<div>🎯 Tier: ${result.tier}</div>` : ''}
                        ${result.attempts ? `<div>🔄 Attempts: ${result.attempts}</div>` : ''}
                    </div>
                </div>
            `;
        } else if (result?.error) {
            // Error handling
            body.innerHTML = `
                <div style="color: #ff6b6b; padding: 10px; background: rgba(255, 107, 107, 0.1); border-radius: 6px;">
                    <strong>Error:</strong> ${result.error}
                    ${result.tip ? `<div style="margin-top: 8px; font-size: 0.85rem; opacity: 0.8;">💡 ${result.tip}</div>` : ''}
                    ${result.tier ? `<div style="margin-top: 4px; font-size: 0.85rem; opacity: 0.7;">Tier: ${result.tier}</div>` : ''}
                </div>
            `;
        } else {
            const resultStr = JSON.stringify(result?.result || result, null, 2);
            body.textContent = resultStr.substring(0, 1000) + (resultStr.length > 1000 ? '\n...' : '');
        }
        break;
    }
}


// ─── Markdown Rendering ─────────────────────────────

function renderMarkdown(text) {
    if (!text) return '';

    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

    // Lists
    html = html.replace(/^\- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Links
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" style="color:var(--accent-light)">$1</a>');

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    if (!html.startsWith('<')) html = `<p>${html}</p>`;

    return html;
}


// ─── UI Helpers ─────────────────────────────────────

function showStatus(text) {
    statusBar.classList.add('active');
    statusText.textContent = text;
}

function hideStatus() {
    statusBar.classList.remove('active');
}

function scrollToBottom() {
    if (userSettings.auto_scroll !== false) {
        requestAnimationFrame(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });
    }
}

function updateConfidence(score) {
    if (score === undefined || score === null) return;
    const dot = lastConfidence.querySelector('.conf-dot');
    const text = lastConfidence.querySelector('.conf-text');
    if (score < 5) {
        dot.style.background = 'var(--error)';
    } else if (score < 8) {
        dot.style.background = 'var(--warning)';
    } else {
        dot.style.background = 'var(--success)';
    }
    text.textContent = `${score}/10`;
}

function clearChat() {
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">🧠</div>
            <h2>Welcome to NexusMind</h2>
            <p>Your local, unfiltered AI assistant with 50+ integrated tools & a live neural network.</p>
            <div class="prompts-carousel">
                <button class="quick-btn" onclick="sendQuick('Solve x² + 5x + 6 = 0')">
                    <span class="quick-icon">🔢</span><span class="quick-text">Solve Math</span>
                </button>
                <button class="quick-btn" onclick="sendQuick('Use chain-of-thought to explain quantum computing')">
                    <span class="quick-icon">🧠</span><span class="quick-text">Chain of Thought</span>
                </button>
                <button class="quick-btn" onclick="sendQuick('Search GitHub for trending AI projects')">
                    <span class="quick-icon">🔍</span><span class="quick-text">GitHub Search</span>
                </button>
                <button class="quick-btn" onclick="sendQuick('Generate an image of a cyberpunk city')">
                    <span class="quick-icon">🎨</span><span class="quick-text">Generate Image</span>
                </button>
            </div>
            <div class="feature-cards">
                <div class="feature-card"><span class="feature-icon">🧬</span><h4>Neural Network</h4><p>Train & visualize live</p></div>
                <div class="feature-card"><span class="feature-icon">🔗</span><h4>RAG & Knowledge</h4><p>Vector search, graphs</p></div>
                <div class="feature-card"><span class="feature-icon">🌳</span><h4>Reasoning</h4><p>CoT, ToT, debate</p></div>
                <div class="feature-card"><span class="feature-icon">⚙️</span><h4>50+ Tools</h4><p>ML, eval, workflow</p></div>
            </div>
        </div>`;
}

async function clearMemory() {
    try {
        await fetch('/api/memory/clear', { method: 'POST' });
        fetchStatus();
    } catch (e) { console.error('Failed to clear memory:', e); }
}


// ─── Fetch System Status ────────────────────────────

let statusFetchPending = false;
async function fetchStatus() {
    if (statusFetchPending) return;
    statusFetchPending = true;
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();

        modelStatus.className = `status-dot ${data.model_loaded ? 'connected' : ''}`;

        if (data.profiles && modelProfileSelect) {
            const currentVal = modelProfileSelect.value;
            modelProfileSelect.innerHTML = '';
            for (const [id, name] of Object.entries(data.profiles)) {
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = name;
                modelProfileSelect.appendChild(opt);
            }
            if (data.current_profile) modelProfileSelect.value = data.current_profile;
            else modelProfileSelect.value = currentVal;

            const footerText = document.querySelector('.footer-text');
            if (footerText && data.current_profile) {
                footerText.textContent = `NexusMind • ${data.profiles[data.current_profile]} • Local & Unfiltered`;
            }
        }

        toolCount.textContent = data.tool_count;
        toolsList.innerHTML = '';
        const fragment = document.createDocumentFragment();
        data.tools.forEach(name => {
            const tag = document.createElement('span');
            tag.className = 'tool-tag';
            if (activeTools.has(name)) tag.classList.add('glowing');
            tag.textContent = name;
            fragment.appendChild(tag);
        });
        toolsList.appendChild(fragment);

        if (data.memory) {
            document.getElementById('stMemory').textContent = data.memory.short_term_messages || 0;
            document.getElementById('ltMemory').textContent = data.memory.long_term_entries || 0;
            if (dbSizeEl) {
                const size = data.memory.db_size_mb ?? 0;
                dbSizeEl.textContent = `${size} MB`;
            }
        }
    } catch (e) {
        console.error('Status fetch failed:', e);
    } finally {
        statusFetchPending = false;
    }
}


// ═══════════════════════════════════════════════════
// NEURAL NETWORK VISUALIZER
// ═══════════════════════════════════════════════════

async function trainNeuralNetwork() {
    const dataset = document.getElementById('nnDataset').value;
    const lr = parseFloat(document.getElementById('nnLR').value);
    const epochs = parseInt(document.getElementById('nnEpochs').value);
    const btn = document.getElementById('nnTrainBtn');

    if (btn.classList.contains('training')) return;

    btn.classList.add('training');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Training...';

    try {
        const resp = await fetch('/api/neural/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset, learning_rate: lr, epochs }),
        });
        const data = await resp.json();

        if (data.state) {
            nnState = data.state;
            drawNeuralNetwork(nnState);
            updateNNStats(nnState);
        }

    } catch (e) {
        console.error('Neural network training failed:', e);
    }
}

async function pollNNState() {
    if (!isNNActive) return;
    try {
        const resp = await fetch('/api/neural/state');
        const data = await resp.json();
        if (data.state) {
            nnState = data.state;
            drawNeuralNetwork(nnState);
            updateNNStats(nnState);

            const btn = document.getElementById('nnTrainBtn');
            if (nnState.is_training) {
                btn.classList.add('training');
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Training...';
            } else {
                btn.classList.remove('training');
                btn.innerHTML = '<i class="fas fa-play"></i> Train';
            }
        }
    } catch (e) { }
    if (isNNActive) setTimeout(pollNNState, 500);
}
function updateNNStats(state) {
    if (!state) return;
    document.getElementById('nnEpochDisplay').textContent = state.epoch || 0;
    document.getElementById('nnLossDisplay').textContent = state.loss !== null ? state.loss.toFixed(6) : '—';
    document.getElementById('nnAccDisplay').textContent = state.accuracy !== null ? (state.accuracy * 100).toFixed(1) + '%' : '—';
    document.getElementById('nnLayersDisplay').textContent = state.layer_sizes?.join(' → ') || '—';
}

async function resetNeuralNetwork() {
    try {
        await fetch('/api/neural/reset', { method: 'POST' });
        const resp = await fetch('/api/neural/state');
        const data = await resp.json();
        if (data.state) {
            nnState = data.state;
            drawNeuralNetwork(nnState);
            drawLossChart(nnState);
            updateNNStats(nnState);
        } else {
            const canvas = document.getElementById('nnCanvas');
            if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
            const chart = document.getElementById('nnChartCanvas');
            if (chart) chart.getContext('2d').clearRect(0, 0, chart.width, chart.height);
        }
        document.getElementById('nnEpochDisplay').textContent = '0';
        document.getElementById('nnLossDisplay').textContent = '—';
        document.getElementById('nnAccDisplay').textContent = '—';
        document.getElementById('nnLayersDisplay').textContent = '—';
    } catch (e) {
        console.error('Neural network reset failed:', e);
    }
}

function drawLossChart(state) {
    const canvas = document.getElementById('nnChartCanvas');
    if (!canvas || !state.loss_history) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    canvas.width = 800 * dpr;
    canvas.height = 200 * dpr;
    canvas.style.width = '800px';
    canvas.style.height = '200px';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.scale(dpr, dpr);

    const history = state.loss_history;
    if (history.length < 2) return;

    const maxLoss = Math.max(...history);
    const minLoss = Math.min(...history);
    const range = maxLoss - minLoss || 1;

    ctx.beginPath();
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';

    for (let i = 0; i < history.length; i++) {
        const x = (i / (history.length - 1)) * 780 + 10;
        const y = 190 - ((history[i] - minLoss) / range) * 170;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Area fill
    ctx.lineTo(790, 200);
    ctx.lineTo(10, 200);
    const grad = ctx.createLinearGradient(0, 0, 0, 200);
    grad.addColorStop(0, 'rgba(16, 185, 129, 0.2)');
    grad.addColorStop(1, 'rgba(16, 185, 129, 0)');
    ctx.fillStyle = grad;
    ctx.fill();
}


// ─── Draw Neural Network ────────────────────────────

function drawNeuralNetwork(state) {
    const canvas = document.getElementById('nnCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    canvas.width = 800 * dpr;
    canvas.height = 500 * dpr;
    canvas.style.width = '800px';
    canvas.style.height = '500px';
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear raw pixels
    ctx.scale(dpr, dpr);

    const layers = state.layer_sizes;
    if (!layers || layers.length === 0) return;

    const numLayers = layers.length;
    const maxNeurons = Math.max(...layers);
    const layerSpacing = numLayers > 1 ? 700 / (numLayers - 1) : 0;
    const startX = 50;
    const canvasH = 500;
    const neuronRadius = Math.min(18, 200 / maxNeurons);

    const positions = [];

    // Calculate neuron positions
    for (let l = 0; l < numLayers; l++) {
        const layerPositions = [];
        const n = layers[l];
        const totalH = n * (neuronRadius * 2 + 15) - 15;
        const startY = (canvasH - totalH) / 2;

        for (let i = 0; i < n; i++) {
            const x = startX + l * layerSpacing;
            const y = startY + i * (neuronRadius * 2 + 15) + neuronRadius;
            layerPositions.push({ x, y });
        }
        positions.push(layerPositions);
    }

    // Deterministic pseudo-random for stable organic shapes
    const seededRandom = (seed) => {
        const x = Math.sin(seed) * 10000;
        return x - Math.floor(x);
    };

    // Draw organic connections (Synapses)
    for (let l = 0; l < numLayers - 1; l++) {
        const weights = state.weights[l];
        for (let i = 0; i < positions[l].length; i++) {
            for (let j = 0; j < positions[l + 1].length; j++) {
                const from = positions[l][i];
                const to = positions[l + 1][j];

                let w = 0;
                if (weights && weights[i] && weights[i][j] !== undefined) {
                    w = weights[i][j];
                }

                const absW = Math.min(Math.abs(w), 3);
                // Skip very weak connections to reduce clutter
                if (absW < 0.1) continue;

                const alpha = Math.max(0.05, absW * 0.3);
                const lineWidth = 0.5 + absW * 1.5;

                ctx.beginPath();
                ctx.moveTo(from.x, from.y);

                // Bezier curve for organic look
                const cp1x = from.x + layerSpacing * 0.5;
                const cp1y = from.y;
                const cp2x = from.x + layerSpacing * 0.5;
                const cp2y = to.y;

                ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, to.x, to.y);

                const grad = ctx.createLinearGradient(from.x, from.y, to.x, to.y);
                if (w > 0) {
                    grad.addColorStop(0, `rgba(16, 185, 129, ${alpha * 0.2})`);
                    grad.addColorStop(0.5, `rgba(16, 185, 129, ${alpha})`);
                    grad.addColorStop(1, `rgba(16, 185, 129, ${alpha * 0.2})`);
                } else {
                    grad.addColorStop(0, `rgba(239, 68, 68, ${alpha * 0.2})`);
                    grad.addColorStop(0.5, `rgba(239, 68, 68, ${alpha})`);
                    grad.addColorStop(1, `rgba(239, 68, 68, ${alpha * 0.2})`);
                }

                ctx.strokeStyle = grad;
                ctx.lineWidth = lineWidth;
                ctx.stroke();
            }
        }
    }

    // Draw organic neurons (Somas & Dendrites)
    for (let l = 0; l < numLayers; l++) {
        for (let i = 0; i < positions[l].length; i++) {
            const pos = positions[l][i];

            let activation = 0.5;
            if (state.activations && state.activations[l]) {
                const act = state.activations[l][i];
                activation = act !== undefined ? act : 0.5;
            }

            const neuronSeed = l * 1000 + i;

            // Draw Dendrites (little organic branches)
            const numDendrites = 4 + Math.floor(seededRandom(neuronSeed) * 4);
            ctx.beginPath();
            for (let d = 0; d < numDendrites; d++) {
                const dSeed = neuronSeed * 10 + d;
                const angle = (Math.PI * 2 / numDendrites) * d + seededRandom(dSeed) * 0.5;
                const length = neuronRadius * (1.5 + seededRandom(dSeed + 1));
                const dx = Math.cos(angle) * length;
                const dy = Math.sin(angle) * length;

                ctx.moveTo(pos.x, pos.y);

                const cpX = pos.x + dx * 0.5 + (seededRandom(dSeed + 2) - 0.5) * 15;
                const cpY = pos.y + dy * 0.5 + (seededRandom(dSeed + 3) - 0.5) * 15;

                ctx.quadraticCurveTo(cpX, cpY, pos.x + dx, pos.y + dy);
            }
            ctx.strokeStyle = `rgba(124, 92, 252, ${0.15 + activation * 0.25})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Glow around soma
            const glowRadius = neuronRadius * (1.5 + activation * 0.8);
            const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, glowRadius);
            gradient.addColorStop(0, `rgba(124, 92, 252, ${0.4 + activation * 0.5})`);
            gradient.addColorStop(1, 'rgba(124, 92, 252, 0)');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, glowRadius, 0, Math.PI * 2);
            ctx.fill();

            // Soma (Neuron body) - organic uneven circle
            ctx.beginPath();
            const segments = 8;
            for (let a = 0; a <= segments; a++) {
                const angle = (Math.PI * 2 / segments) * a;
                // Add slight wobble, but ensure the shape closes smoothly
                const wobble = (a === segments) ? seededRandom(neuronSeed * 2) : seededRandom(neuronSeed * 2 + a);
                const r = neuronRadius * (0.85 + wobble * 0.3);
                const x = pos.x + Math.cos(angle) * r;
                const y = pos.y + Math.sin(angle) * r;

                if (a === 0) ctx.moveTo(x, y);
                else {
                    // Smooth curve between edge points
                    const prevAngle = (Math.PI * 2 / segments) * (a - 1);
                    const prevWobble = seededRandom(neuronSeed * 2 + a - 1);
                    const prevR = neuronRadius * (0.85 + prevWobble * 0.3);
                    const prevX = pos.x + Math.cos(prevAngle) * prevR;
                    const prevY = pos.y + Math.sin(prevAngle) * prevR;
                    ctx.quadraticCurveTo(prevX, prevY, x, y);
                }
            }
            ctx.closePath();

            const bioHue = 260 - (activation * 80); // Purple (260) to Cyan/Blue (180)
            ctx.fillStyle = `hsl(${bioHue}, 80%, ${30 + activation * 40}%)`;
            ctx.fill();

            ctx.strokeStyle = `rgba(255, 255, 255, ${0.4 + activation * 0.6})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Nucleus
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, neuronRadius * 0.35, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${0.6 + activation * 0.4})`;
            ctx.fill();
        }

        // Layer labels
        if (positions[l].length > 0) {
            const topNeuron = positions[l][0];
            ctx.fillStyle = '#8e8ea0';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            let label = l === 0 ? 'Input Segment' : l === numLayers - 1 ? 'Output Segment' : `Hidden Cortex ${l}`;
            ctx.fillText(label, topNeuron.x, canvasH - 25);
            ctx.font = '10px Inter';
            ctx.fillText(`${layers[l]} Somas`, topNeuron.x, canvasH - 10);
        }
    }
}


// ─── Draw Loss Chart ────────────────────────────────

function drawLossChart(state) {
    const canvas = document.getElementById('nnChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    canvas.width = 800 * dpr;
    canvas.height = 200 * dpr;
    canvas.style.width = '800px';
    canvas.style.height = '200px';
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, 800, 200);

    const losses = state.loss_history || [];
    const accs = state.accuracy_history || [];
    if (losses.length < 2) return;

    const padding = { top: 20, right: 60, bottom: 30, left: 50 };
    const chartW = 800 - padding.left - padding.right;
    const chartH = 200 - padding.top - padding.bottom;

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + chartW, y);
        ctx.stroke();
    }

    // Loss line
    const maxLoss = Math.max(...losses);
    const xStep = chartW / (losses.length - 1);

    ctx.beginPath();
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    losses.forEach((loss, i) => {
        const x = padding.left + i * xStep;
        const y = padding.top + (1 - loss / maxLoss) * chartH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Accuracy line
    if (accs.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        accs.forEach((acc, i) => {
            const x = padding.left + i * xStep;
            const y = padding.top + (1 - acc) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }
}

// ─── Neural Cache (3D Sphere Decision Making Viz) ──────────────

// DELETED Duplicate NeuralCacheSphere3D definition (moved to top)

// ─── Neural Cache 3D Visualization ────────────────────
// DELETED NeuralCacheSphere3D definition from here (moved to top)

let neuralCache = null;  // For backwards compatibility
let neuralCacheViz = null;

// ─── Toast Notifications ────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = '💡';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'error') icon = '❌';
    if (type === 'info') icon = '🔭';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-msg">${message}</span>
    `;

    container.appendChild(toast);

    // Fade in
    setTimeout(() => toast.classList.add('active'), 10);

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('active');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}


// ─── Periodic Status ────────────────────────────────
setInterval(fetchStatus, 30000);
// ─── Auto-Scout UI ────────────────────────────────────

// ─── Scout Initialization (Variables moved to top) ──────

function handleScoutAlert(data) {
    const findings = data.findings || [];
    const badge = document.getElementById('scoutBadge');
    const list = document.getElementById('scoutList');

    if (data.initial) {
        scoutFindings = findings;
    } else {
        findings.forEach(f => {
            if (!scoutFindings.find(existing => existing.id === f.id)) {
                scoutFindings.unshift(f);
                showNotification(`🔭 Scout found: ${f.name}`, 'info');
            }
        });
    }
    updateScoutUI();
}

function updateScoutUI() {
    const badge = document.getElementById('scoutBadge');
    const list = document.getElementById('scoutList');
    if (!badge || !list) return;

    if (scoutFindings.length > 0) {
        badge.textContent = scoutFindings.length;
        badge.style.display = 'flex';

        list.innerHTML = '';
        scoutFindings.forEach(f => {
            const item = document.createElement('div');
            item.className = 'scout-item';
            item.innerHTML = `
                <div class="scout-item-header">
                    <span class="scout-item-cat">${f.category}</span>
                    <span class="scout-item-stars">⭐ ${f.stars}</span>
                </div>
                <div class="scout-item-name">${f.name}</div>
                <div class="scout-item-desc">${f.description}</div>
                <div class="scout-item-actions">
                    <a href="${f.url}" target="_blank" class="btn-mini">View GitHub</a>
                    <button class="btn-mini primary" onclick="implementFinding('${f.url}', '${f.id}')" title="Ask AI to apply this optimization to its own code">
                        ✨ Apply & Improve
                    </button>
                    <button class="btn-mini secondary" onclick="dismissFinding('${f.id}')">Dismiss</button>
                </div>
            `;
            list.appendChild(item);
        });
    } else {
        badge.style.display = 'none';
        list.innerHTML = '<div class="scout-empty">No new optimizations found yet. NexusMind is scouting GitHub...</div>';
    }
}

async function implementFinding(url, id) {
    try {
        showNotification(`Initializing self-improvement for optimization...`, 'info');
        await fetch('/api/scout/implement', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        await dismissFinding(id);
    } catch (e) {
        console.error('Self-Improvement failed to start:', e);
        showNotification('Failed to start self-improvement protocol', 'error');
    }
}

async function dismissFinding(id) {
    try {
        await fetch('/api/scout/dismiss', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        scoutFindings = scoutFindings.filter(f => f.id !== id);
        updateScoutUI();
    } catch (e) {
        console.error('Dismiss failed:', e);
    }
}

async function dismissAllFindings() {
    for (const f of [...scoutFindings]) {
        await dismissFinding(f.id);
    }
}

function showNotification(text, type = 'info') {
    console.log(`[Scout] ${text}`);
    if (typeof showToast === 'function') {
        showToast(text, type);
    }
}

// ─── Bootstrap (FINAL STEP) ───────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // 1. Critical IO first
    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = (messageInput.scrollHeight) + 'px';
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    // Connect WebSocket
    connect();

    // 2. Load Session/User State
    loadUserSettings();
    loadSessions();
    loadWorkspace();

    // 3. UI Interactions
    if (newChatBtn) newChatBtn.addEventListener('click', createNewChat);

    if (setWorkspaceBtn) {
        setWorkspaceBtn.addEventListener('click', () => {
            const path = prompt('Enter workspace root path:');
            if (path) {
                fetch('/api/workspace', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path })
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        if (workspacePathDisplay) workspacePathDisplay.textContent = path;
                        fetchFileTree();
                    }
                });
            }
        });
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            if (sidebar) sidebar.classList.toggle('collapsed');
            if (openSidebar) {
                if (sidebar?.classList.contains('collapsed')) {
                    openSidebar.style.display = 'flex';
                } else {
                    openSidebar.style.display = 'none';
                }
            }
        });
    }

    if (openSidebar) {
        openSidebar.addEventListener('click', () => {
            if (sidebar) sidebar.classList.remove('collapsed');
            openSidebar.style.display = 'none';
        });
    }

    // 4. Overlays & Optional Features
    try {
        document.getElementById('openNeuralNet')?.addEventListener('click', () => {
            document.getElementById('nnOverlay')?.classList.add('active');
            isNNActive = true;
            pollNNState();
            if (nnState) {
                drawNeuralNetwork(nnState);
            } else {
                resetNeuralNetwork();
            }
        });

        document.getElementById('closeNeuralNet')?.addEventListener('click', () => {
            document.getElementById('nnOverlay')?.classList.remove('active');
            isNNActive = false;
        });

        neuralCacheViz = new NeuralCacheSphere3D('neuralCacheVisualizer');
        neuralCache = {
            addStep: (step) => neuralCacheViz?.addStep(step),
            clear: () => neuralCacheViz?.clear()
        };

        document.getElementById('toggleNeuralCache')?.addEventListener('click', () => {
            const overlay = document.getElementById('neuralCacheOverlay');
            if (overlay) {
                overlay.style.display = overlay.style.display === 'none' ? 'flex' : 'none';
            }
        });

        document.getElementById('closeNeuralCacheOverlay')?.addEventListener('click', () => {
            const overlay = document.getElementById('neuralCacheOverlay');
            if (overlay) overlay.style.display = 'none';
        });

        const zoomControl = document.getElementById('zoomControl');
        const speedControl = document.getElementById('speedControl');
        if (zoomControl) {
            zoomControl.addEventListener('input', (e) => {
                const zoom = parseFloat(e.target.value);
                const valDisp = document.getElementById('zoomValue');
                if (valDisp) valDisp.textContent = zoom.toFixed(1);
                neuralCacheViz?.setZoom(zoom);
            });
        }
        if (speedControl) {
            speedControl.addEventListener('input', (e) => {
                const speed = parseFloat(e.target.value);
                const valDisp = document.getElementById('speedValue');
                if (valDisp) valDisp.textContent = speed.toFixed(1);
                neuralCacheViz?.setSpeed(speed);
            });
        }

        document.getElementById('pauseCacheBtn')?.addEventListener('click', (e) => {
            if (neuralCacheViz) {
                neuralCacheViz.togglePause();
                e.target.textContent = neuralCacheViz.isPaused ? 'Resume' : 'Pause';
            }
        });

        document.getElementById('clearCacheBtn')?.addEventListener('click', () => {
            neuralCacheViz?.clear();
        });

        document.getElementById('openSettings')?.addEventListener('click', () => {
            populateSettingsForm();
            document.getElementById('settingsOverlay')?.classList.add('active');
        });
        document.getElementById('closeSettings')?.addEventListener('click', () => {
            document.getElementById('settingsOverlay')?.classList.remove('active');
        });

        document.getElementById('nnOverlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'nnOverlay') {
                e.target.classList.remove('active');
                isNNActive = false;
            }
        });
        document.getElementById('settingsOverlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'settingsOverlay') e.target.classList.remove('active');
        });

        document.getElementById('openTools')?.addEventListener('click', () => openToolsOverlay());
        document.getElementById('closeTools')?.addEventListener('click', () => {
            toolsOverlay?.classList.remove('active');
        });
        toolsOverlay?.addEventListener('click', (e) => {
            if (e.target.id === 'toolsOverlay') e.target.classList.remove('active');
        });

        document.querySelectorAll('.avatar-option').forEach(opt => {
            opt.addEventListener('click', () => {
                document.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
                opt.classList.add('selected');
            });
        });

        document.querySelectorAll('.theme-option').forEach(opt => {
            opt.addEventListener('click', () => {
                document.querySelectorAll('.theme-option').forEach(o => o.classList.remove('selected'));
                opt.classList.add('selected');
                const theme = opt.dataset.theme;
                if (theme) document.documentElement.setAttribute('data-theme', theme);
            });
        });

        const lrSlider = document.getElementById('nnLR');
        const lrValue = document.getElementById('nnLRValue');
        if (lrSlider && lrValue) {
            lrSlider.addEventListener('input', () => {
                lrValue.textContent = parseFloat(lrSlider.value).toFixed(2);
            });
        }

        if (fileUpload) {
            fileUpload.addEventListener('change', async (e) => {
                const files = e.target.files;
                for (const file of files) {
                    const formData = new FormData();
                    formData.append('file', file);
                    try {
                        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
                        const data = await resp.json();
                        uploadedFiles.push(data);
                        const tag = document.createElement('span');
                        tag.className = 'uploaded-file';
                        tag.innerHTML = `📄 ${file.name} <span class="remove">✕</span>`;
                        tag.querySelector('.remove').onclick = () => tag.remove();
                        if (uploadedFilesEl) uploadedFilesEl.appendChild(tag);
                    } catch (err) { console.error('Upload failed:', err); }
                }
                fileUpload.value = '';
            });
        }

        if (mobileMenu) mobileMenu.addEventListener('click', () => sidebar?.classList.toggle('open'));

        const scoutToggle = document.getElementById('scoutToggle');
        const scoutDropdown = document.getElementById('scoutDropdown');
        if (scoutToggle && scoutDropdown) {
            scoutToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                scoutDropdown.classList.toggle('active');
            });
            document.addEventListener('click', (e) => {
                if (!scoutToggle.contains(e.target)) scoutDropdown.classList.remove('active');
            });
        }

        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && sidebar?.classList.contains('open') &&
                !sidebar.contains(e.target) && !mobileMenu?.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    } catch (e) {
        console.error('Initialization of optional features failed:', e);
    }
});
