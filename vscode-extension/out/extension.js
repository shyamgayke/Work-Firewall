"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
const DASHBOARD_URL = 'http://localhost:8000';
const POLL_INTERVAL = 2000;
// ── Extension entry point ────────────────────────────────────────────────────
function activate(context) {
    // Register sidebar WebView provider
    const provider = new FirewallSidebarProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('workFirewall.dashboard', provider));
    // Commands
    context.subscriptions.push(vscode.commands.registerCommand('workFirewall.reset', async () => {
        await httpPost(`${DASHBOARD_URL}/api/reset`);
        vscode.window.showInformationMessage('Work Firewall: Session reset ✓');
        provider.refresh();
    }), vscode.commands.registerCommand('workFirewall.refresh', () => {
        provider.refresh();
    }));
    // ── GitHub Copilot Chat Participant (@firewall) ────────────────────────────
    // When user opens Copilot chat and types @firewall <question>, Work Firewall handles it!
    try {
        if (typeof vscode.chat?.createChatParticipant === 'function') {
            const participant = vscode.chat.createChatParticipant('workfirewall', async (request, _chatContext, response, _token) => {
                response.markdown(`*🔍 Checking Work Firewall institutional memory…*\n\n`);
                try {
                    const prompt = request.prompt;
                    const resJson = await httpPostJson(`${DASHBOARD_URL}/api/query`, JSON.stringify({ prompt }));
                    const data = JSON.parse(resJson);
                    if (data.matched) {
                        response.markdown(`### 🛡️ Work Firewall — Memory Hit! (Avoided)\n`);
                        response.markdown(`⚡ **Reused Fact #${data.fact?.id || ''}:**\n> ${data.statement}\n\n`);
                        response.markdown(`✅ **Tool call avoided!** Saved 1 tool execution and context window tokens.\n\n`);
                        if (data.files && data.files.length) {
                            const filenames = data.files.map((f) => f.split(/[\\/]/).pop()).join(', ');
                            response.markdown(`*Cryptographic Provenance:* \`${filenames}\` (SHA-256 verified)`);
                        }
                    }
                    else {
                        response.markdown(`### 🔧 Work Firewall — Real Tool Executed\n`);
                        response.markdown(`Investigated codebase and synthesized new institutional fact:\n> ${data.statement}\n\n`);
                        response.markdown(`💾 *Stored in institutional memory for future queries.*`);
                    }
                    provider.refresh();
                }
                catch (err) {
                    response.markdown(`⚠️ **Work Firewall Error:** ${err.message}\nMake sure dashboard is running: \`python run_all.py\``);
                }
            });
            context.subscriptions.push(participant);
        }
    }
    catch (err) {
        console.error('Chat Participant registration failed:', err);
    }
}
function deactivate() { }
// ── Sidebar WebView Provider ─────────────────────────────────────────────────
class FirewallSidebarProvider {
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = this._getHtml();
        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'query') {
                try {
                    const resStr = await httpPostJson(`${DASHBOARD_URL}/api/query`, JSON.stringify({ prompt: msg.prompt }));
                    const data = JSON.parse(resStr);
                    this._view?.webview.postMessage({
                        type: 'queryResult',
                        data,
                    });
                    this.refresh();
                }
                catch (e) {
                    this._view?.webview.postMessage({
                        type: 'queryResult',
                        data: { error: e.message },
                    });
                }
            }
            if (msg.command === 'invalidate') {
                await httpPost(`${DASHBOARD_URL}/api/facts/${msg.factId}/invalidate`);
                this.refresh();
            }
            if (msg.command === 'reset') {
                await httpPost(`${DASHBOARD_URL}/api/reset`);
                vscode.window.showInformationMessage('Work Firewall: Session reset ✓');
                this.refresh();
            }
        });
        // Start polling
        this._startPolling();
        webviewView.onDidDispose(() => this._stopPolling());
    }
    refresh() {
        this._pushUpdate();
    }
    _startPolling() {
        this._interval = setInterval(() => this._pushUpdate(), POLL_INTERVAL);
        this._pushUpdate(); // immediate first update
    }
    _stopPolling() {
        if (this._interval)
            clearInterval(this._interval);
    }
    async _pushUpdate() {
        if (!this._view)
            return;
        try {
            const [statsData, factsData, activityData] = await Promise.all([
                httpGet(`${DASHBOARD_URL}/api/stats`),
                httpGet(`${DASHBOARD_URL}/api/facts`),
                httpGet(`${DASHBOARD_URL}/api/activity`),
            ]);
            this._view.webview.postMessage({
                type: 'update',
                stats: JSON.parse(statsData),
                facts: JSON.parse(factsData),
                activity: JSON.parse(activityData),
            });
        }
        catch {
            this._view.webview.postMessage({ type: 'error' });
        }
    }
    _getHtml() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root {
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --green:  #22c55e;
      --red:    #f87171;
      --blue:   #38bdf8;
      --amber:  #fbbf24;
      --mono:   'Courier New', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-size: 12px;
      font-family: var(--vscode-font-family);
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background);
      padding: 8px;
    }

    /* Status bar */
    .status-bar {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      background: var(--vscode-statusBar-background);
      border-radius: 4px;
      margin-bottom: 8px;
      font-size: 11px;
      color: var(--vscode-statusBar-foreground);
    }
    .dot { width:6px; height:6px; border-radius:50%; background: var(--green); }
    .dot.offline { background: var(--red); }

    /* Interactive Prompt Box */
    .prompt-section {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 6px;
      padding: 8px;
      margin-bottom: 10px;
    }
    .prompt-title {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      opacity: 0.7;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .prompt-input-row {
      display: flex;
      gap: 4px;
      margin-bottom: 6px;
    }
    .prompt-input {
      flex: 1;
      background: var(--vscode-sideBar-background);
      border: 1px solid var(--vscode-input-border);
      color: var(--vscode-foreground);
      padding: 5px 7px;
      font-size: 11px;
      border-radius: 4px;
      outline: none;
    }
    .prompt-input:focus {
      border-color: var(--accent);
    }
    .btn-ask {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 0 10px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-ask:hover { background: var(--accent-hover); }

    .chips-row {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 6px;
    }
    .chip {
      font-size: 9px;
      background: rgba(99,102,241,0.12);
      border: 1px solid rgba(99,102,241,0.3);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 10px;
      cursor: pointer;
    }
    .chip:hover {
      background: rgba(99,102,241,0.25);
    }

    .query-banner {
      margin-top: 6px;
      padding: 6px 8px;
      border-radius: 4px;
      font-size: 11px;
      line-height: 1.4;
      display: none;
      animation: fadeIn 0.2s;
    }
    @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
    .query-banner.hit {
      background: rgba(34,197,94,0.12);
      border: 1px solid var(--green);
      color: var(--green);
    }
    .query-banner.miss {
      background: rgba(56,189,248,0.12);
      border: 1px solid var(--blue);
      color: var(--blue);
    }
    .query-banner-title { font-weight: 700; margin-bottom: 2px; }
    .query-banner-body { color: var(--vscode-foreground); font-size: 10.5px; margin-top: 2px; }

    /* Stats grid */
    .stats-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-bottom: 10px;
    }
    .stat-box {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 6px;
      padding: 8px 10px;
    }
    .stat-label { font-size: 10px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.4px; }
    .stat-value { font-size: 20px; font-weight: 700; font-family: var(--mono); margin-top: 2px; }
    .stat-value.green { color: var(--green); }
    .stat-value.indigo { color: var(--accent); }
    .stat-value.amber  { color: var(--amber); }
    .stat-value.blue   { color: var(--blue); }

    /* Rate bar */
    .rate-bar-bg { background: var(--vscode-input-border); height:3px; border-radius:2px; margin-top:4px; }
    .rate-bar-fill { height:100%; background: var(--green); border-radius:2px; transition: width 0.5s; }

    /* Section headings */
    .section-head {
      font-size: 10px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.6px; opacity: 0.5;
      margin: 10px 0 5px;
      display: flex; align-items: center; justify-content: space-between;
    }

    /* Activity items */
    .ev {
      display: flex; align-items: flex-start; gap: 6px;
      padding: 5px 4px;
      border-bottom: 1px solid var(--vscode-input-border);
      font-size: 11px;
    }
    .ev-icon { flex-shrink:0; font-size:12px; }
    .ev-call { font-family: var(--mono); opacity: 0.7; font-size: 10px; }
    .ev-statement { opacity: 0.9; font-size: 11px; }

    /* Facts */
    .fact {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 5px;
      padding: 7px 9px;
      margin-bottom: 5px;
    }
    .fact-id { font-size: 10px; opacity: 0.4; font-family: var(--mono); }
    .fact-stmt { font-size: 11px; margin: 3px 0; line-height: 1.4; }
    .fact-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .fact-file { font-size: 10px; color: var(--blue); font-family: var(--mono); }
    .fact-valid { font-size: 10px; color: var(--green); }
    .fact-stale { font-size: 10px; color: var(--red); }
    .btn-rm {
      margin-left:auto; font-size:9px; padding:2px 5px;
      border:1px solid rgba(248,113,113,0.4); background:transparent;
      color:var(--red); cursor:pointer; border-radius:3px;
    }

    /* Action btns */
    .actions { display:flex; gap:6px; margin-top:10px; }
    .action-btn {
      flex:1; padding:5px; font-size:11px; border-radius:5px;
      border:1px solid var(--vscode-input-border);
      background:var(--vscode-input-background);
      color:var(--vscode-foreground); cursor:pointer;
    }
    .action-btn:hover { border-color: var(--accent); }

    #offline-msg { text-align:center; padding:20px; opacity:0.5; font-size:12px; }
  </style>
</head>
<body>
  <div class="status-bar">
    <div class="dot" id="dot"></div>
    <span id="status-txt">Connecting to Work Firewall…</span>
  </div>

  <div id="content" style="display:none">
    <!-- Interactive Prompt Section -->
    <div class="prompt-section">
      <div class="prompt-title">💬 Ask Firewall / Agent Prompt</div>
      <div class="prompt-input-row">
        <input type="text" id="prompt-input" class="prompt-input" placeholder="e.g. Where is JWT verified?" />
        <button class="btn-ask" id="btn-ask" onclick="submitPrompt()">Ask</button>
      </div>
      <div class="chips-row">
        <span class="chip" onclick="quickAsk('Where is JWT validated?')">JWT Auth</span>
        <span class="chip" onclick="quickAsk('How are passwords secured?')">Passwords</span>
        <span class="chip" onclick="quickAsk('What database is used?')">Database</span>
        <span class="chip" onclick="quickAsk('What files exist?')">Files</span>
      </div>
      <div id="query-banner" class="query-banner">
        <div id="query-banner-title" class="query-banner-title"></div>
        <div id="query-banner-body" class="query-banner-body"></div>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-box">
        <div class="stat-label">Total</div>
        <div class="stat-value" id="s-total">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Avoided</div>
        <div class="stat-value green" id="s-avoided">0</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Rate</div>
        <div class="stat-value indigo" id="s-rate">0%</div>
        <div class="rate-bar-bg"><div class="rate-bar-fill" id="rate-fill" style="width:0%"></div></div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Saved</div>
        <div class="stat-value amber" id="s-latency">0.0s</div>
      </div>
    </div>

    <div class="section-head">
      <span>⚡ Activity</span>
      <span id="act-count" style="font-size:10px">0</span>
    </div>
    <div id="activity-list"></div>

    <div class="section-head">
      <span>🧠 Facts</span>
      <span id="fact-count" style="font-size:10px">0</span>
    </div>
    <div id="fact-list"></div>

    <div class="actions">
      <button class="action-btn" onclick="sendCmd('reset')">↺ Reset</button>
    </div>
  </div>

  <div id="offline-msg" style="display:none">🔌 Dashboard offline<br/>Start: <code>python run_all.py</code></div>

  <script>
    const vscode = acquireVsCodeApi();

    function sendCmd(command, factId) {
      vscode.postMessage({ command, factId });
    }

    function submitPrompt() {
      const input = document.getElementById('prompt-input');
      const val = input.value.trim();
      if (!val) return;
      document.getElementById('btn-ask').textContent = '...';
      vscode.postMessage({ command: 'query', prompt: val });
    }

    function quickAsk(text) {
      document.getElementById('prompt-input').value = text;
      submitPrompt();
    }

    document.getElementById('prompt-input')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') submitPrompt();
    });

    function esc(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    window.addEventListener('message', ev => {
      const msg = ev.data;

      if (msg.type === 'queryResult') {
        document.getElementById('btn-ask').textContent = 'Ask';
        const banner = document.getElementById('query-banner');
        const bTitle = document.getElementById('query-banner-title');
        const bBody = document.getElementById('query-banner-body');

        banner.style.display = 'block';
        if (msg.data.matched) {
          banner.className = 'query-banner hit';
          bTitle.innerHTML = '⚡ MEMORY HIT — Tool Call Avoided!';
          bBody.innerHTML = '<strong>Reused Fact #' + (msg.data.fact?.id || '') + ':</strong> ' + esc(msg.data.statement);
        } else if (msg.data.error) {
          banner.className = 'query-banner miss';
          bTitle.innerHTML = '⚠️ Error';
          bBody.innerHTML = esc(msg.data.error);
        } else {
          banner.className = 'query-banner miss';
          bTitle.innerHTML = '🔧 Real Tool Executed';
          bBody.innerHTML = esc(msg.data.statement || msg.data.message);
        }
      }

      if (msg.type === 'error') {
        document.getElementById('content').style.display = 'none';
        document.getElementById('offline-msg').style.display = 'block';
        document.getElementById('dot').classList.add('offline');
        document.getElementById('status-txt').textContent = 'Dashboard offline';
        return;
      }

      if (msg.type === 'update') {
        document.getElementById('content').style.display = 'block';
        document.getElementById('offline-msg').style.display = 'none';
        document.getElementById('dot').classList.remove('offline');
        document.getElementById('status-txt').textContent = 'Work Firewall — live';

        const s = msg.stats;
        document.getElementById('s-total').textContent = s.total_calls;
        document.getElementById('s-avoided').textContent = s.avoided;
        document.getElementById('s-rate').textContent = s.avoidance_rate + '%';
        document.getElementById('rate-fill').style.width = s.avoidance_rate + '%';
        document.getElementById('s-latency').textContent = s.latency_saved_s + 's';

        // Activity
        const events = (msg.activity.events || []).slice(0, 10);
        document.getElementById('act-count').textContent = events.length;
        document.getElementById('activity-list').innerHTML = events.length === 0
          ? '<div style="opacity:0.4;font-size:11px;padding:6px">No events yet</div>'
          : events.map(ev => {
            const icons = {avoided:'✅', executed:'🔧', stored:'💾'};
            return \`<div class="ev">
              <span class="ev-icon">\${icons[ev.type]||'•'}</span>
              <div>
                <div class="ev-call">\${esc(ev.call||'')}</div>
                \${ev.statement ? \`<div class="ev-statement">\${esc(ev.statement)}</div>\` : ''}
              </div>
            </div>\`;
          }).join('');

        // Facts
        const facts = (msg.facts.facts || []);
        document.getElementById('fact-count').textContent = facts.length;
        document.getElementById('fact-list').innerHTML = facts.length === 0
          ? '<div style="opacity:0.4;font-size:11px;padding:6px">No facts stored yet</div>'
          : facts.map(f => {
            const files = (f.files||[]).map(fp => {
              const nm = fp.split(/[\\\\/]/).pop();
              return \`<span class="fact-file">\${esc(nm)}</span>\`;
            }).join('');
            const badge = f.is_valid
              ? '<span class="fact-valid">✓ Valid</span>'
              : '<span class="fact-stale">⚠ Stale</span>';
            return \`<div class="fact">
              <div class="fact-id">#\${f.id}</div>
              <div class="fact-stmt">\${esc(f.statement)}</div>
              <div class="fact-meta">
                \${files}\${badge}
                <button class="btn-rm" onclick="sendCmd('invalidate', \${f.id})">🗑</button>
              </div>
            </div>\`;
          }).join('');
      }
    });
  </script>
</body>
</html>`;
    }
}
// ── HTTP helpers ─────────────────────────────────────────────────────────────
function httpGet(url) {
    return new Promise((resolve, reject) => {
        http.get(url, { timeout: 2000 }, (res) => {
            let data = '';
            res.on('data', c => data += c);
            res.on('end', () => resolve(data));
        }).on('error', reject).on('timeout', () => reject(new Error('timeout')));
    });
}
function httpPost(url) {
    return new Promise((resolve, reject) => {
        const req = http.request(url, { method: 'POST', timeout: 2000 }, () => resolve());
        req.on('error', reject);
        req.end();
    });
}
function httpPostJson(url, body) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const req = http.request(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body),
            },
            timeout: 5000,
        }, (res) => {
            let data = '';
            res.on('data', c => data += c);
            res.on('end', () => resolve(data));
        });
        req.on('error', reject);
        req.write(body);
        req.end();
    });
}
//# sourceMappingURL=extension.js.map