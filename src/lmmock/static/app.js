const $ = (id) => document.getElementById(id);
const state = { rules: [], activeRuleId: null };
let toastTimer;

async function api(path, options = {}) {
  const response = await fetch(`/__lmmock/api${path}`, {
    headers: { 'content-type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { message = (await response.json()).error || message; } catch (_) { /* keep status */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function setStatus(label, kind = '') {
  $('status').className = `status ${kind}`.trim();
  $('status').querySelector('span').textContent = label;
}

function toast(message) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').classList.add('show');
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2200);
}

function updateFields() {
  $('match-wrap').classList.toggle('hidden', $('match-type').value === 'all');
  const type = $('reply-type').value;
  $('content-wrap').classList.toggle('hidden', type === 'tool' || type === 'error');
  $('tool-wrap').classList.toggle('hidden', type !== 'tool');
  $('error-wrap').classList.toggle('hidden', type !== 'error');
}

function setForm(rule = null) {
  state.activeRuleId = rule?.id || null;
  $('rule-id').value = rule?.id || '';
  $('editor-title').textContent = rule ? 'Edit rule' : 'New rule';
  $('name').value = rule?.name || '';
  $('enabled').checked = rule?.enabled ?? true;
  $('priority').value = rule?.priority || 100;
  $('scope').value = rule?.scopes?.[0] || '*';
  $('match-type').value = rule?.match_type || 'all';
  $('match-value').value = rule?.match_value || '';
  $('reply-type').value = rule?.reply_type || 'text';
  $('delay').value = rule?.delay_ms || 0;
  $('content').value = rule?.reply?.content || '';
  $('tool-name').value = rule?.reply?.tool_name || '';
  $('arguments').value = JSON.stringify(rule?.reply?.arguments || { city: 'Shanghai' }, null, 2);
  $('error-status').value = rule?.reply?.status_code || 500;
  $('error-message').value = rule?.reply?.message || 'Mock error';
  $('delete-rule').classList.toggle('hidden', !rule);
  updateFields();
  renderRules();
}

function renderRules() {
  const node = $('rules');
  node.replaceChildren();
  if (!state.rules.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'No rules yet. Create one to return your first mock response.';
    node.append(empty);
    return;
  }
  for (const rule of state.rules) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `rule${rule.enabled ? '' : ' off'}${rule.id === state.activeRuleId ? ' active' : ''}`;
    const name = document.createElement('span');
    name.className = 'rule-name';
    name.textContent = rule.name;
    const priority = document.createElement('span');
    priority.className = 'rule-priority';
    priority.textContent = `#${rule.priority}`;
    const meta = document.createElement('span');
    meta.className = 'rule-meta';
    meta.textContent = `${rule.reply_type} · ${rule.scopes.join(', ')} · ${rule.match_type}${rule.delay_ms ? ` · ${rule.delay_ms}ms` : ''}`;
    button.append(name, priority, meta);
    button.addEventListener('click', () => setForm(rule));
    node.append(button);
  }
}

async function loadRules() {
  state.rules = await api('/rules');
  renderRules();
}

async function loadSettings() {
  const settings = await api('/settings');
  $('openai-mode').value = settings.mode_openai || 'mock-only';
  $('openai-base').value = settings.openai_base_url || '';
  $('anthropic-mode').value = settings.mode_anthropic || 'mock-only';
  $('anthropic-base').value = settings.anthropic_base_url || '';
  const openai = settings.openai_api_key_configured ? 'key set' : 'no key';
  const anthropic = settings.anthropic_api_key_configured ? 'key set' : 'no key';
  $('key-status').textContent = `Environment keys · OpenAI: ${openai} · Anthropic: ${anthropic}`;
}

function renderRequests(requests) {
  const node = $('requests');
  node.replaceChildren();
  if (!requests.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'Requests will appear here after your app or the Playground calls LMMock.';
    node.append(empty);
    return;
  }
  for (const request of requests) {
    const row = document.createElement('div');
    row.className = 'request';
    const provider = document.createElement('span');
    provider.className = 'request-provider';
    provider.textContent = request.provider;
    const main = document.createElement('span');
    main.className = 'request-main';
    const title = document.createElement('strong');
    title.textContent = `${request.operation} · ${request.rule || 'No match'}`;
    const input = document.createElement('small');
    input.textContent = request.input || 'Empty input';
    main.append(title, input);
    const timing = document.createElement('span');
    timing.className = 'request-time';
    timing.textContent = `${request.status} · ${request.duration_ms}ms`;
    row.append(provider, main, timing);
    node.append(row);
  }
}

async function loadRequests() {
  renderRequests(await api('/requests'));
}

$('new-rule').addEventListener('click', () => setForm());
$('match-type').addEventListener('change', updateFields);
$('reply-type').addEventListener('change', updateFields);

$('rule-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  try {
    const type = $('reply-type').value;
    let reply;
    if (type === 'tool') {
      reply = { tool_name: $('tool-name').value, arguments: JSON.parse($('arguments').value || '{}') };
    } else if (type === 'error') {
      reply = { status_code: Number($('error-status').value), message: $('error-message').value };
    } else {
      reply = { content: $('content').value };
    }
    const payload = {
      name: $('name').value,
      enabled: $('enabled').checked,
      priority: Number($('priority').value),
      scopes: [$('scope').value],
      match_type: $('match-type').value,
      match_value: $('match-value').value,
      reply_type: type,
      reply,
      delay_ms: Number($('delay').value),
    };
    const id = $('rule-id').value;
    const saved = await api(id ? `/rules/${id}` : '/rules', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    await loadRules();
    setForm(state.rules.find((rule) => rule.id === saved.id) || null);
    toast(id ? 'Rule updated' : 'Rule created');
  } catch (error) {
    toast(error instanceof SyntaxError ? 'Tool arguments must be valid JSON' : error.message);
  } finally {
    submit.disabled = false;
  }
});

$('delete-rule').addEventListener('click', async () => {
  const id = $('rule-id').value;
  if (!id || !window.confirm('Delete this rule?')) return;
  try {
    await api(`/rules/${id}`, { method: 'DELETE' });
    await loadRules();
    setForm();
    toast('Rule deleted');
  } catch (error) { toast(error.message); }
});

$('settings-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  try {
    await api('/settings', {
      method: 'PUT',
      body: JSON.stringify({
        mode_openai: $('openai-mode').value,
        openai_base_url: $('openai-base').value,
        mode_anthropic: $('anthropic-mode').value,
        anthropic_base_url: $('anthropic-base').value,
      }),
    });
    await loadSettings();
    toast('Provider settings saved');
  } catch (error) { toast(error.message); }
  finally { submit.disabled = false; }
});

$('playground-send').addEventListener('click', async () => {
  const button = $('playground-send');
  button.disabled = true;
  const started = performance.now();
  try {
    const endpoint = $('playground-endpoint').value;
    const input = $('playground-input').value;
    const body = endpoint === 'chat'
      ? { model: 'mock-model', messages: [{ role: 'user', content: input }] }
      : endpoint === 'responses'
        ? { model: 'mock-model', input }
        : { model: 'mock-model', max_tokens: 128, messages: [{ role: 'user', content: input }] };
    const path = endpoint === 'chat' ? '/v1/chat/completions' : endpoint === 'responses' ? '/v1/responses' : '/v1/messages';
    const response = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer mock' }, body: JSON.stringify(body) });
    const data = await response.json();
    $('playground-output').textContent = JSON.stringify(data, null, 2);
    $('playground-meta').textContent = `${response.status} · ${Math.round(performance.now() - started)}ms`;
    await loadRequests();
  } catch (error) {
    $('playground-output').textContent = error.message;
    $('playground-meta').textContent = 'request failed';
  } finally { button.disabled = false; }
});

$('refresh-requests').addEventListener('click', () => loadRequests().catch((error) => toast(error.message)));
$('clear-requests').addEventListener('click', async () => {
  try { await api('/requests', { method: 'DELETE' }); await loadRequests(); toast('Request list cleared'); }
  catch (error) { toast(error.message); }
});

for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(button.dataset.copy); toast('Base URL copied'); }
    catch (_) { toast(button.dataset.copy); }
  });
}

setForm();
Promise.all([loadRules(), loadSettings(), loadRequests()])
  .then(() => setStatus('Ready · mock-first', 'ready'))
  .catch((error) => { setStatus('Offline', 'offline'); toast(error.message); });
setInterval(() => loadRequests().catch(() => {}), 5000);
