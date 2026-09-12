import * as vscode from 'vscode';
import * as http from 'http';

const DASHBOARD_URL = 'http://localhost:8000';
const POLL_INTERVAL = 2000;

// ── Extension entry point ────────────────────────────────────────────────────
export function activate(context: vscode.ExtensionContext) {
  // Register sidebar WebView provider
  const provider = new FirewallSidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('workFirewall.dashboard', provider)
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand('workFirewall.reset', async () => {
      await httpPost(`${DASHBOARD_URL}/api/reset`);
      vscode.window.showInformationMessage('Work Firewall: Session reset ✓');
      provider.refresh();
    }),
    vscode.commands.registerCommand('workFirewall.refresh', () => {
      provider.refresh();
    })
  );
}

export function deactivate() {}

// ── Sidebar WebView Provider ─────────────────────────────────────────────────
class FirewallSidebarProvider implements vscode.WebviewViewProvider {
  private _view?: vscode.WebviewView;
  private _interval?: NodeJS.Timer;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._getHtml();

    // Handle messages from webview
    webviewView.webview.onDidReceiveMessage(async (msg) => {
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

  private _startPolling() {
    this._interval = setInterval(() => this._pushUpdate(), POLL_INTERVAL);
    this._pushUpdate(); // immediate first update
  }

  private _stopPolling() {
    if (this._interval) clearInterval(this._interval as NodeJS.Timeout);
  }

  private async _pushUpdate() {
    if (!this._view) return;
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
    } catch {
      this._view.webview.postMessage({ type: 'error' });
    }
  }

  private _getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root {
      --accent: #6366f1;
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
      margin-bottom: 10px;
      font-size: 11px;
      color: var(--vscode-statusBar-foreground);
    }
    .dot { width:6px; height:6px; border-radius:50%; background: var(--green); }
    .dot.offline { background: var(--red); }

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

  <div id="offline-msg" style="display:none">🔌 Dashboard offline<br/>Start: <code>uvicorn dashboard.server:app --port 8000</code></div>

  <script>
    const vscode = acquireVsCodeApi();

    function sendCmd(command, factId) {
      vscode.postMessage({ command, factId });
    }

    function esc(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    window.addEventListener('message', ev => {
      const msg = ev.data;

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
function httpGet(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    http.get(url, { timeout: 2000 }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(data));
    }).on('error', reject).on('timeout', () => reject(new Error('timeout')));
  });
}

function httpPost(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method: 'POST', timeout: 2000 }, () => resolve());
    req.on('error', reject);
    req.end();
  });
}
