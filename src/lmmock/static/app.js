const $ = (id) => document.getElementById(id);
const state = { rules: [], activeRuleId: null, language: localStorage.getItem('lmmock-language') || (navigator.language.startsWith('zh') ? 'zh' : 'en') };
let toastTimer;

const messages = {
  en: {
    localWorkspace: 'local workspace', heroTitle: 'Shape the model response.', heroCopy: 'Create deterministic replies for OpenAI and Anthropic clients, then test the same application code without a model call.', copy: 'Copy',
    rules: 'Rules', rulesHelp: 'Lowest priority number wins.', newRule: 'New rule', startTemplate: 'Start from a template', templateHelp: 'Choose one, adjust it, then save.', savedRules: 'Saved rules', editorHelp: 'Match a request and return a fixed result.', enabled: 'Enabled',
    name: 'Name', namePlaceholder: 'Weather reply', scope: 'Scope', allEndpoints: 'All endpoints', priority: 'Priority', match: 'Match', everyRequest: 'Every request', contains: 'Contains', regex: 'Regex', text: 'Text', reply: 'Reply', jsonText: 'JSON text', toolCall: 'Tool call', httpError: 'HTTP error', delay: 'Delay (ms)', content: 'Content', captureHelp: 'Regex captures can be inserted as ${city} or ${1}.', toolName: 'Tool name', arguments: 'Arguments (JSON)', status: 'Status', errorMessage: 'Error message', saveRule: 'Save rule', delete: 'Delete',
    playgroundHelp: 'Send one request through the real endpoint.', endpoint: 'Endpoint', input: 'Input', sendRequest: 'Send request', noRequestYet: 'No request yet.', recentRequests: 'Recent requests', recentHelp: 'Select one to inspect its request and response.', clear: 'Clear', advanced: 'ADVANCED', providerForwarding: 'Provider forwarding', forwardHelp: 'When enabled, only requests that match no rule reach the real API.', configure: 'Configure', forwardUnmatched: 'Forward unmatched requests', baseUrl: 'Base URL', saveSettings: 'Save settings', requestDetail: 'REQUEST DETAIL', request: 'Request', response: 'Response',
    editRule: 'Edit rule', noRules: 'No saved rules yet. Pick a template or create a new rule.', noRequests: 'Requests will appear here after your app or the Playground calls LMMock.', noMatch: 'No match', emptyInput: 'Empty input', ruleUpdated: 'Rule updated', ruleCreated: 'Rule created', invalidArguments: 'Tool arguments must be valid JSON', deleteConfirm: 'Delete this rule?', ruleDeleted: 'Rule deleted', settingsSaved: 'Provider settings saved', requestFailed: 'request failed', listCleared: 'Request list cleared', copied: 'Base URL copied', keySet: 'key set', noKey: 'no key', keyStatus: 'Environment keys · OpenAI: {openai} · Anthropic: {anthropic}', templateLoaded: 'Template loaded — review it and save the rule.',
    templateSimple: 'Simple text', templateSimpleHelp: 'Reply to a matching phrase.', templateRegex: 'Regex variables', templateRegexHelp: 'Reuse captured text in the reply.', templateJson: 'JSON result', templateJsonHelp: 'Return structured JSON text.', templateTool: 'Tool call', templateToolHelp: 'Ask the client to call a function.', templateRate: 'Rate limit', templateRateHelp: 'Test provider error handling.', templateSlow: 'Slow reply', templateSlowHelp: 'Test loading and timeout states.'
  },
  zh: {
    localWorkspace: '本地工作台', heroTitle: '定义你的模型回复。', heroCopy: '为 OpenAI 和 Anthropic 客户端创建稳定可复现的回复，无需调用真实模型即可测试同一套应用代码。', copy: '复制',
    rules: '规则', rulesHelp: '优先级数字越小，越先匹配。', newRule: '新建规则', startTemplate: '从模板开始', templateHelp: '选择模板，按需修改，然后保存。', savedRules: '已保存规则', editorHelp: '匹配请求并返回固定结果。', enabled: '启用',
    name: '名称', namePlaceholder: '天气回复', scope: '接口范围', allEndpoints: '全部接口', priority: '优先级', match: '匹配方式', everyRequest: '所有请求', contains: '包含文本', regex: '正则表达式', text: '文本', reply: '回复类型', jsonText: 'JSON 文本', toolCall: '工具调用', httpError: 'HTTP 错误', delay: '延迟（毫秒）', content: '回复内容', captureHelp: '正则捕获内容可通过 ${city} 或 ${1} 插入回复。', toolName: '工具名称', arguments: '参数（JSON）', status: '状态码', errorMessage: '错误信息', saveRule: '保存规则', delete: '删除',
    playgroundHelp: '通过真实兼容接口发送一次请求。', endpoint: '接口', input: '输入', sendRequest: '发送请求', noRequestYet: '还没有发送请求。', recentRequests: '最近请求', recentHelp: '点击任意请求查看请求体和响应体。', clear: '清空', advanced: '高级设置', providerForwarding: '供应商转发', forwardHelp: '开启后，只有未匹配任何规则的请求才会转发到真实 API。', configure: '配置', forwardUnmatched: '转发未匹配的请求', baseUrl: '基础 URL', saveSettings: '保存设置', requestDetail: '请求详情', request: '请求', response: '响应',
    editRule: '编辑规则', noRules: '还没有保存规则。选择一个模板或新建规则即可开始。', noRequests: '你的应用或 Playground 调用 LMMock 后，请求会显示在这里。', noMatch: '未匹配', emptyInput: '空输入', ruleUpdated: '规则已更新', ruleCreated: '规则已创建', invalidArguments: '工具参数必须是有效的 JSON', deleteConfirm: '确定删除这条规则吗？', ruleDeleted: '规则已删除', settingsSaved: '供应商设置已保存', requestFailed: '请求失败', listCleared: '请求列表已清空', copied: '基础 URL 已复制', keySet: '已设置', noKey: '未设置', keyStatus: '环境变量密钥 · OpenAI：{openai} · Anthropic：{anthropic}', templateLoaded: '模板已载入，请检查并保存规则。',
    templateSimple: '简单文本', templateSimpleHelp: '命中指定短语后返回文本。', templateRegex: '正则变量', templateRegexHelp: '把捕获的内容复用到回复中。', templateJson: 'JSON 结果', templateJsonHelp: '返回结构化 JSON 文本。', templateTool: '工具调用', templateToolHelp: '让客户端调用指定函数。', templateRate: '限流错误', templateRateHelp: '测试应用的错误处理。', templateSlow: '慢速回复', templateSlowHelp: '测试加载和超时状态。'
  },
};

const templates = [
  { icon: 'Aa', name: 'templateSimple', help: 'templateSimpleHelp', rule: { name: 'Hello reply', priority: 10, scopes: ['*'], match_type: 'contains', match_value: 'hello', reply_type: 'text', reply: { content: 'Hello from LMMock!' }, delay_ms: 0 } },
  { icon: '(.*)', name: 'templateRegex', help: 'templateRegexHelp', rule: { name: 'Weather by city', priority: 20, scopes: ['*'], match_type: 'regex', match_value: 'weather in (?P<city>.+)', reply_type: 'text', reply: { content: 'Weather in ${city}: sunny.' }, delay_ms: 0 } },
  { icon: '{}', name: 'templateJson', help: 'templateJsonHelp', rule: { name: 'Classification JSON', priority: 30, scopes: ['*'], match_type: 'contains', match_value: 'classify', reply_type: 'json', reply: { content: '{\n  "category": "support",\n  "confidence": 0.98\n}' }, delay_ms: 0 } },
  { icon: 'ƒ', name: 'templateTool', help: 'templateToolHelp', rule: { name: 'Weather tool', priority: 40, scopes: ['*'], match_type: 'contains', match_value: 'use weather tool', reply_type: 'tool', reply: { tool_name: 'get_weather', arguments: { city: 'Shanghai' } }, delay_ms: 0 } },
  { icon: '429', name: 'templateRate', help: 'templateRateHelp', rule: { name: 'Rate limit error', priority: 50, scopes: ['*'], match_type: 'contains', match_value: 'rate limit', reply_type: 'error', reply: { status_code: 429, message: 'Rate limit exceeded' }, delay_ms: 0 } },
  { icon: '…', name: 'templateSlow', help: 'templateSlowHelp', rule: { name: 'Slow response', priority: 60, scopes: ['*'], match_type: 'contains', match_value: 'slow', reply_type: 'text', reply: { content: 'This response arrived after a delay.' }, delay_ms: 1500 } },
];

function t(key, values = {}) {
  let text = messages[state.language][key] || messages.en[key] || key;
  for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
  return text;
}

async function api(path, options = {}) {
  const response = await fetch(`/__lmmock/api${path}`, { headers: { 'content-type': 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { message = (await response.json()).error || message; } catch (_) { /* keep status */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.add('show');
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2200);
}

function applyLanguage() {
  document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  $('language-toggle').textContent = state.language === 'en' ? '中文' : 'EN';
  $('language-toggle').setAttribute('aria-label', state.language === 'en' ? '切换到中文' : 'Switch to English');
  $('editor-title').textContent = state.activeRuleId ? t('editRule') : t('newRule');
  renderTemplates(); renderRules(); loadSettings().catch(() => {});
}

function updateFields() {
  $('match-wrap').classList.toggle('hidden', $('match-type').value === 'all');
  const type = $('reply-type').value;
  $('content-wrap').classList.toggle('hidden', type === 'tool' || type === 'error');
  $('tool-wrap').classList.toggle('hidden', type !== 'tool');
  $('error-wrap').classList.toggle('hidden', type !== 'error');
}

function setForm(rule = null) {
  state.activeRuleId = rule?.id || null; $('rule-id').value = rule?.id || ''; $('editor-title').textContent = rule?.id ? t('editRule') : t('newRule');
  $('name').value = rule?.name || ''; $('enabled').checked = rule?.enabled ?? true; $('priority').value = rule?.priority || 100; $('scope').value = rule?.scopes?.[0] || '*';
  $('match-type').value = rule?.match_type || 'all'; $('match-value').value = rule?.match_value || ''; $('reply-type').value = rule?.reply_type || 'text'; $('delay').value = rule?.delay_ms || 0;
  $('content').value = rule?.reply?.content || ''; $('tool-name').value = rule?.reply?.tool_name || ''; $('arguments').value = JSON.stringify(rule?.reply?.arguments || { city: 'Shanghai' }, null, 2);
  $('error-status').value = rule?.reply?.status_code || 500; $('error-message').value = rule?.reply?.message || 'Mock error'; $('delete-rule').classList.toggle('hidden', !rule?.id);
  updateFields(); renderRules();
}

function renderTemplates() {
  const node = $('templates'); node.replaceChildren();
  for (const template of templates) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'template-card';
    const icon = document.createElement('b'); icon.textContent = template.icon;
    const copy = document.createElement('span'); const name = document.createElement('strong'); name.textContent = t(template.name); const help = document.createElement('small'); help.textContent = t(template.help);
    copy.append(name, help); button.append(icon, copy);
    button.addEventListener('click', () => { setForm({ ...structuredClone(template.rule), enabled: true }); toast(t('templateLoaded')); }); node.append(button);
  }
}

function renderRules() {
  const node = $('rules'); node.replaceChildren();
  if (!state.rules.length) { const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = t('noRules'); node.append(empty); return; }
  for (const rule of state.rules) {
    const button = document.createElement('button'); button.type = 'button'; button.className = `rule${rule.enabled ? '' : ' off'}${rule.id === state.activeRuleId ? ' active' : ''}`;
    const name = document.createElement('span'); name.className = 'rule-name'; name.textContent = rule.name;
    const priority = document.createElement('span'); priority.className = 'rule-priority'; priority.textContent = `#${rule.priority}`;
    const meta = document.createElement('span'); meta.className = 'rule-meta'; meta.textContent = `${rule.reply_type} · ${rule.scopes.join(', ')} · ${rule.match_type}${rule.delay_ms ? ` · ${rule.delay_ms}ms` : ''}`;
    button.append(name, priority, meta); button.addEventListener('click', () => setForm(rule)); node.append(button);
  }
}

async function loadRules() { state.rules = await api('/rules'); renderRules(); }

async function loadSettings() {
  const settings = await api('/settings');
  $('openai-forward').checked = Boolean(settings.forward_openai); $('openai-base').value = settings.openai_base_url || '';
  $('anthropic-forward').checked = Boolean(settings.forward_anthropic); $('anthropic-base').value = settings.anthropic_base_url || '';
  $('key-status').textContent = t('keyStatus', { openai: settings.openai_api_key_configured ? t('keySet') : t('noKey'), anthropic: settings.anthropic_api_key_configured ? t('keySet') : t('noKey') });
}

function openRequest(request) {
  $('request-dialog-title').textContent = `${request.provider} · ${request.operation} · ${request.status}`;
  $('request-detail').textContent = JSON.stringify(request.request ?? {}, null, 2); $('response-detail').textContent = JSON.stringify(request.response ?? {}, null, 2); $('request-dialog').showModal();
}

function renderRequests(requests) {
  const node = $('requests'); node.replaceChildren();
  if (!requests.length) { const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = t('noRequests'); node.append(empty); return; }
  for (const request of requests) {
    const row = document.createElement('button'); row.type = 'button'; row.className = 'request';
    const provider = document.createElement('span'); provider.className = 'request-provider'; provider.textContent = request.provider;
    const main = document.createElement('span'); main.className = 'request-main'; const title = document.createElement('strong'); title.textContent = `${request.operation} · ${request.rule || t('noMatch')}`;
    const input = document.createElement('small'); input.textContent = request.input || t('emptyInput'); main.append(title, input);
    const timing = document.createElement('span'); timing.className = 'request-time'; timing.textContent = `${request.status} · ${request.duration_ms}ms  ›`;
    row.append(provider, main, timing); row.addEventListener('click', () => openRequest(request)); node.append(row);
  }
}

async function loadRequests() { renderRequests(await api('/requests')); }

$('language-toggle').addEventListener('click', () => { state.language = state.language === 'en' ? 'zh' : 'en'; localStorage.setItem('lmmock-language', state.language); applyLanguage(); loadRequests().catch(() => {}); });
$('new-rule').addEventListener('click', () => setForm()); $('match-type').addEventListener('change', updateFields); $('reply-type').addEventListener('change', updateFields);

$('rule-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    const type = $('reply-type').value; let reply;
    if (type === 'tool') reply = { tool_name: $('tool-name').value, arguments: JSON.parse($('arguments').value || '{}') };
    else if (type === 'error') reply = { status_code: Number($('error-status').value), message: $('error-message').value };
    else reply = { content: $('content').value };
    const payload = { name: $('name').value, enabled: $('enabled').checked, priority: Number($('priority').value), scopes: [$('scope').value], match_type: $('match-type').value, match_value: $('match-value').value, reply_type: type, reply, delay_ms: Number($('delay').value) };
    const id = $('rule-id').value; const saved = await api(id ? `/rules/${id}` : '/rules', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    await loadRules(); setForm(state.rules.find((rule) => rule.id === saved.id) || null); toast(t(id ? 'ruleUpdated' : 'ruleCreated'));
  } catch (error) { toast(error instanceof SyntaxError ? t('invalidArguments') : error.message); } finally { submit.disabled = false; }
});

$('delete-rule').addEventListener('click', async () => {
  const id = $('rule-id').value; if (!id || !window.confirm(t('deleteConfirm'))) return;
  try { await api(`/rules/${id}`, { method: 'DELETE' }); await loadRules(); setForm(); toast(t('ruleDeleted')); } catch (error) { toast(error.message); }
});

$('settings-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    await api('/settings', { method: 'PUT', body: JSON.stringify({ forward_openai: $('openai-forward').checked, openai_base_url: $('openai-base').value, forward_anthropic: $('anthropic-forward').checked, anthropic_base_url: $('anthropic-base').value }) });
    await loadSettings(); toast(t('settingsSaved'));
  } catch (error) { toast(error.message); } finally { submit.disabled = false; }
});

$('playground-send').addEventListener('click', async () => {
  const button = $('playground-send'); button.disabled = true; const started = performance.now();
  try {
    const endpoint = $('playground-endpoint').value; const input = $('playground-input').value;
    const body = endpoint === 'chat' ? { model: 'mock-model', messages: [{ role: 'user', content: input }] } : endpoint === 'responses' ? { model: 'mock-model', input } : { model: 'mock-model', max_tokens: 128, messages: [{ role: 'user', content: input }] };
    const path = endpoint === 'chat' ? '/v1/chat/completions' : endpoint === 'responses' ? '/v1/responses' : '/v1/messages';
    const response = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer mock' }, body: JSON.stringify(body) });
    const data = await response.json(); $('playground-output').textContent = JSON.stringify(data, null, 2); $('playground-meta').textContent = `${response.status} · ${Math.round(performance.now() - started)}ms`; await loadRequests();
  } catch (error) { $('playground-output').textContent = error.message; $('playground-meta').textContent = t('requestFailed'); } finally { button.disabled = false; }
});

$('refresh-requests').addEventListener('click', () => loadRequests().catch((error) => toast(error.message)));
$('clear-requests').addEventListener('click', async () => { try { await api('/requests', { method: 'DELETE' }); await loadRequests(); toast(t('listCleared')); } catch (error) { toast(error.message); } });
$('close-request-dialog').addEventListener('click', () => $('request-dialog').close());
$('request-dialog').addEventListener('click', (event) => { if (event.target === $('request-dialog')) $('request-dialog').close(); });

for (const button of document.querySelectorAll('[data-copy]')) button.addEventListener('click', async () => { try { await navigator.clipboard.writeText(button.dataset.copy); toast(t('copied')); } catch (_) { toast(button.dataset.copy); } });

setForm(); applyLanguage();
Promise.all([loadRules(), loadSettings(), loadRequests()]).catch((error) => toast(error.message));
setInterval(() => loadRequests().catch(() => {}), 5000);
