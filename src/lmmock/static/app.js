const api = (path, options = {}) => fetch(`/__lmmock/api${path}`, { headers: { 'content-type': 'application/json', ...(options.headers || {}) }, ...options });
const $ = (id) => document.getElementById(id);
let rules = [];

function setForm(rule = null) {
  $('rule-id').value = rule?.id || '';
  $('editor-title').textContent = rule ? 'Edit rule' : 'New rule';
  $('name').value = rule?.name || '';
  $('scope').value = rule?.scopes?.[0] || '*';
  $('match-type').value = rule?.match_type || 'all';
  $('match-value').value = rule?.match_value || '';
  $('reply-type').value = rule?.reply_type || 'text';
  $('content').value = rule?.reply?.content || '';
  $('tool-name').value = rule?.reply?.tool_name || '';
  $('arguments').value = JSON.stringify(rule?.reply?.arguments || { city: 'Shanghai' }, null, 2);
  $('error-status').value = rule?.reply?.status_code || 500;
  $('error-message').value = rule?.reply?.message || 'Mock error';
  $('delete-rule').classList.toggle('hidden', !rule);
  updateFields();
}

function updateFields() {
  $('match-wrap').classList.toggle('hidden', $('match-type').value === 'all');
  const type = $('reply-type').value;
  $('content-wrap').classList.toggle('hidden', type === 'tool' || type === 'error');
  $('tool-wrap').classList.toggle('hidden', type !== 'tool');
  $('error-wrap').classList.toggle('hidden', type !== 'error');
}

function renderRules() {
  const node = $('rules'); node.replaceChildren();
  for (const rule of rules) {
    const button = document.createElement('button'); button.className = `rule ${rule.enabled ? '' : 'off'}`;
    button.innerHTML = `<div class="rule-name"></div><div class="rule-meta"></div>`;
    button.querySelector('.rule-name').textContent = rule.name;
    button.querySelector('.rule-meta').textContent = `${rule.reply_type} · ${rule.scopes.join(', ')} · ${rule.match_type}`;
    button.onclick = () => setForm(rule); node.append(button);
  }
}

async function load() {
  const response = await api('/rules'); rules = await response.json(); renderRules(); $('status').textContent = 'ready';
}

async function loadSettings() {
  const settings = await (await api('/settings')).json();
  $('openai-mode').value = settings.mode_openai || 'mock-only';
  $('openai-base').value = settings.openai_base_url || '';
  $('anthropic-mode').value = settings.mode_anthropic || 'mock-only';
  $('anthropic-base').value = settings.anthropic_base_url || '';
  $('key-status').textContent = `Keys: OpenAI ${settings.openai_api_key_configured ? 'configured' : 'not set'} · Anthropic ${settings.anthropic_api_key_configured ? 'configured' : 'not set'} (environment variables)`;
}

$('new-rule').onclick = () => setForm();
$('match-type').onchange = updateFields; $('reply-type').onchange = updateFields;
$('rule-form').onsubmit = async (event) => {
  event.preventDefault();
  const type = $('reply-type').value;
  const reply = type === 'tool' ? { tool_name: $('tool-name').value, arguments: JSON.parse($('arguments').value || '{}') } : type === 'error' ? { status_code: Number($('error-status').value), message: $('error-message').value } : { content: $('content').value };
  const payload = { name: $('name').value, enabled: true, priority: rules.find((r) => r.id === Number($('rule-id').value))?.priority || 100, scopes: [$('scope').value], match_type: $('match-type').value, match_value: $('match-value').value, reply_type: type, reply };
  const id = $('rule-id').value; const response = await api(id ? `/rules/${id}` : '/rules', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
  if (!response.ok) { $('status').textContent = 'save failed'; return; } await load(); setForm();
};
$('delete-rule').onclick = async () => { const id = $('rule-id').value; if (id) await api(`/rules/${id}`, { method: 'DELETE' }); await load(); setForm(); };
$('settings-form').onsubmit = async (event) => {
  event.preventDefault();
  const response = await api('/settings', { method: 'PUT', body: JSON.stringify({ mode_openai: $('openai-mode').value, openai_base_url: $('openai-base').value, mode_anthropic: $('anthropic-mode').value, anthropic_base_url: $('anthropic-base').value }) });
  $('status').textContent = response.ok ? 'saved' : 'save failed';
  if (response.ok) await loadSettings();
};
$('playground-send').onclick = async () => {
  const endpoint = $('playground-endpoint').value; const input = $('playground-input').value;
  const body = endpoint === 'chat' ? { model: 'mock-model', messages: [{ role: 'user', content: input }] } : endpoint === 'responses' ? { model: 'mock-model', input } : { model: 'mock-model', max_tokens: 128, messages: [{ role: 'user', content: input }] };
  const path = endpoint === 'chat' ? '/v1/chat/completions' : endpoint === 'responses' ? '/v1/responses' : '/v1/messages';
  const response = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer mock' }, body: JSON.stringify(body) });
  $('playground-output').textContent = JSON.stringify(await response.json(), null, 2);
};
Promise.all([load(), loadSettings()]).catch(() => { $('status').textContent = 'offline'; }); setForm();
