const $ = (id) => document.getElementById(id);
const state = {
  rules: [], groups: [], settings: null, activeRuleId: null, activeGroupId: null,
  language: localStorage.getItem('lmmock-language') || 'en',
};
let toastTimer;

const messages = {
  en: {
    localWorkspace: 'local workspace', heroTitle: 'Shape the model response.', heroCopy: 'Create deterministic replies for OpenAI and Anthropic clients, then test the same application code without a model call.', copy: 'Copy', apiKey: 'API key',
    rules: 'Rules', rulesHelp: 'Rules are isolated inside behavior groups.', newRule: 'New rule', behaviorGroup: 'Behavior group', newGroup: 'New group', startTemplate: 'Start from a template', templateHelp: 'Choose one, adjust it, then save.', savedRules: 'Saved rules', editorHelp: 'Match a request and return a fixed result.', enabled: 'Enabled',
    name: 'Name', description: 'Description', namePlaceholder: 'Weather reply', scope: 'Scope', allEndpoints: 'All endpoints', priority: 'Priority', match: 'Match', everyRequest: 'Every request', contains: 'Contains', regex: 'Regex', text: 'Text', reply: 'Reply', jsonText: 'JSON text', toolCall: 'Tool call', httpError: 'HTTP error', delay: 'Delay (ms)', content: 'Content', captureHelp: 'Regex captures can be inserted as ${city} or ${1}.', toolName: 'Tool name', arguments: 'Arguments (JSON)', status: 'Status', errorMessage: 'Error message', saveRule: 'Save rule', saveGroup: 'Save group', delete: 'Delete',
    playgroundHelp: 'Send one request through the selected model and behavior group.', endpoint: 'Endpoint', model: 'Model', input: 'Input', sendRequest: 'Send request', noRequestYet: 'No request yet.', recentRequests: 'Recent requests', recentHelp: 'Select one to inspect its request and response.', clear: 'Clear', configuration: 'CONFIGURATION', modelsInterfacesSecurity: 'Models, interfaces & security', configurationHelp: 'Control what LMMock exposes before configuring optional forwarding.', configure: 'Configure', mockSurface: 'Mock API surface', mockSurfaceHelp: 'One model per line. Disabled interfaces return 404.', modelNames: 'Model names', defaultModel: 'Default model', accessSecurity: 'Access security', accessSecurityHelp: 'Set the server key with --api-key or LMMOCK_API_KEY, then enter it in this browser session.', enterApiKey: 'Enter API key', browserKeyHelp: 'Stored only for this browser tab. Leave blank to clear it.', useApiKey: 'Use API key', providerForwarding: 'Provider forwarding', forwardHelp: 'When enabled, only requests that match no rule reach the real API.', forwardUnmatched: 'Forward unmatched requests', baseUrl: 'Base URL', saveSettings: 'Save settings', requestDetail: 'REQUEST DETAIL', request: 'Request', response: 'Response',
    editRule: 'Edit rule', createGroup: 'Create behavior group', editGroup: 'Edit behavior group', noRules: 'No rules in this group yet. Pick a template or create a rule.', noRequests: 'Requests will appear here after your app or the Playground calls LMMock.', noMatch: 'No match', emptyInput: 'Empty input', ruleUpdated: 'Rule updated', ruleCreated: 'Rule created', invalidArguments: 'Tool arguments must be valid JSON', deleteConfirm: 'Delete this rule?', ruleDeleted: 'Rule deleted', groupCreated: 'Behavior group created', groupUpdated: 'Behavior group updated', groupDeleted: 'Behavior group deleted', groupDeleteConfirm: 'Delete this behavior group?', settingsSaved: 'Configuration saved', requestFailed: 'request failed', listCleared: 'Request list cleared', copied: 'Base URL copied', keySet: 'key set', noKey: 'no key', providerKeyStatus: 'Forwarding keys · OpenAI: {openai} · Anthropic: {anthropic}', accessOn: 'Server protection is enabled. This browser session is authorized.', accessNeeded: 'Server protection is enabled. Enter its API key to continue.', accessOff: 'Server protection is off. Use --api-key when exposing LMMock to a network.', apiKeySaved: 'Browser API key updated', apiKeyRequired: 'Enter the LMMock API key to open the workspace.', templateLoaded: 'Template loaded — review it and save the rule.',
    templateSimple: 'Simple text', templateSimpleHelp: 'Reply to a matching phrase.', templateRegex: 'Regex variables', templateRegexHelp: 'Reuse captured text in the reply.', templateJson: 'JSON result', templateJsonHelp: 'Return structured JSON text.', templateTool: 'Tool call', templateToolHelp: 'Ask the client to call a function.', templateRate: 'Rate limit', templateRateHelp: 'Test provider error handling.', templateSlow: 'Slow reply', templateSlowHelp: 'Test loading and timeout states.'
  },
  zh: {
    localWorkspace: '本地工作台', heroTitle: '定义你的模型回复。', heroCopy: '为 OpenAI 和 Anthropic 客户端创建稳定可复现的回复，无需调用真实模型即可测试同一套应用代码。', copy: '复制', apiKey: 'API 密钥',
    rules: '规则', rulesHelp: '不同的行为组拥有相互隔离的规则。', newRule: '新建规则', behaviorGroup: '行为组', newGroup: '新建组', startTemplate: '从模板开始', templateHelp: '选择模板，按需修改，然后保存。', savedRules: '已保存规则', editorHelp: '匹配请求并返回固定结果。', enabled: '启用',
    name: '名称', description: '描述', namePlaceholder: '天气回复', scope: '接口范围', allEndpoints: '全部接口', priority: '优先级', match: '匹配方式', everyRequest: '所有请求', contains: '包含文本', regex: '正则表达式', text: '文本', reply: '回复类型', jsonText: 'JSON 文本', toolCall: '工具调用', httpError: 'HTTP 错误', delay: '延迟（毫秒）', content: '回复内容', captureHelp: '正则捕获内容可通过 ${city} 或 ${1} 插入回复。', toolName: '工具名称', arguments: '参数（JSON）', status: '状态码', errorMessage: '错误信息', saveRule: '保存规则', saveGroup: '保存行为组', delete: '删除',
    playgroundHelp: '使用选定模型和行为组发送一次真实兼容请求。', endpoint: '接口', model: '模型', input: '输入', sendRequest: '发送请求', noRequestYet: '还没有发送请求。', recentRequests: '最近请求', recentHelp: '点击任意请求查看请求体和响应体。', clear: '清空', configuration: '配置', modelsInterfacesSecurity: '模型、接口与安全', configurationHelp: '先配置 LMMock 暴露的能力，再按需开启上游转发。', configure: '配置', mockSurface: 'Mock API 能力', mockSurfaceHelp: '每行一个模型。关闭的接口会返回 404。', modelNames: '模型名称', defaultModel: '默认模型', accessSecurity: '访问安全', accessSecurityHelp: '通过 --api-key 或 LMMOCK_API_KEY 设置服务端密钥，再在当前网页会话中输入。', enterApiKey: '输入 API 密钥', browserKeyHelp: '仅保存在当前浏览器标签页；留空可清除。', useApiKey: '使用此密钥', providerForwarding: '供应商转发', forwardHelp: '开启后，只有未匹配任何规则的请求才会转发到真实 API。', forwardUnmatched: '转发未匹配的请求', baseUrl: '基础 URL', saveSettings: '保存配置', requestDetail: '请求详情', request: '请求', response: '响应',
    editRule: '编辑规则', createGroup: '新建行为组', editGroup: '编辑行为组', noRules: '这个行为组还没有规则。可以选择模板或新建规则。', noRequests: '你的应用或 Playground 调用 LMMock 后，请求会显示在这里。', noMatch: '未匹配', emptyInput: '空输入', ruleUpdated: '规则已更新', ruleCreated: '规则已创建', invalidArguments: '工具参数必须是有效的 JSON', deleteConfirm: '确定删除这条规则吗？', ruleDeleted: '规则已删除', groupCreated: '行为组已创建', groupUpdated: '行为组已更新', groupDeleted: '行为组已删除', groupDeleteConfirm: '确定删除这个行为组吗？', settingsSaved: '配置已保存', requestFailed: '请求失败', listCleared: '请求列表已清空', copied: '基础 URL 已复制', keySet: '已设置', noKey: '未设置', providerKeyStatus: '转发密钥 · OpenAI：{openai} · Anthropic：{anthropic}', accessOn: '服务端保护已开启，当前网页会话已通过验证。', accessNeeded: '服务端保护已开启，请输入 API 密钥。', accessOff: '服务端保护未开启。暴露到网络时请使用 --api-key。', apiKeySaved: '网页 API 密钥已更新', apiKeyRequired: '请输入 LMMock API 密钥以打开工作台。', templateLoaded: '模板已载入，请检查并保存规则。',
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

function authHeaders() {
  const key = sessionStorage.getItem('lmmock-api-key');
  return key ? { authorization: `Bearer ${key}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(`/__lmmock/api${path}`, { ...options, headers: { 'content-type': 'application/json', ...authHeaders(), ...(options.headers || {}) } });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = typeof data.error === 'string' ? data.error : data.error?.message || message;
    } catch (_) { /* keep status */ }
    const error = new Error(message); error.status = response.status; throw error;
  }
  return response.status === 204 ? null : response.json();
}

function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.add('show');
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2400);
}

function applyLanguage() {
  document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  $('language-toggle').textContent = state.language === 'en' ? 'EN' : 'ZH';
  $('language-toggle').setAttribute('aria-label', state.language === 'en' ? '切换到中文' : 'Switch to English');
  $('editor-title').textContent = state.activeRuleId ? t('editRule') : t('newRule');
  renderTemplates(); renderRules(); renderAccessStatus();
}

function updateFields() {
  $('match-wrap').classList.toggle('hidden', $('match-type').value === 'all');
  const type = $('reply-type').value;
  $('content-wrap').classList.toggle('hidden', type === 'tool' || type === 'error');
  $('tool-wrap').classList.toggle('hidden', type !== 'tool');
  $('error-wrap').classList.toggle('hidden', type !== 'error');
}

function fillGroupSelect(select, selected) {
  select.replaceChildren();
  for (const group of state.groups) {
    const option = document.createElement('option'); option.value = group.id; option.textContent = group.name; option.selected = Number(selected) === group.id; select.append(option);
  }
}

function renderGroups() {
  fillGroupSelect($('group-select'), state.activeGroupId);
  fillGroupSelect($('rule-group'), state.activeGroupId);
}

function setForm(rule = null) {
  state.activeRuleId = rule?.id || null; $('rule-id').value = rule?.id || ''; $('editor-title').textContent = rule?.id ? t('editRule') : t('newRule');
  $('name').value = rule?.name || ''; $('enabled').checked = rule?.enabled ?? true; $('priority').value = rule?.priority || 100; $('scope').value = rule?.scopes?.[0] || '*';
  $('rule-group').value = rule?.group_id || state.activeGroupId; $('match-type').value = rule?.match_type || 'all'; $('match-value').value = rule?.match_value || ''; $('reply-type').value = rule?.reply_type || 'text'; $('delay').value = rule?.delay_ms || 0;
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
    button.addEventListener('click', () => { setForm({ ...structuredClone(template.rule), enabled: true, group_id: state.activeGroupId }); toast(t('templateLoaded')); }); node.append(button);
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

async function loadRules() { state.rules = await api(`/rules?group_id=${state.activeGroupId}`); renderRules(); }

function syncModelOptions(selected) {
  const models = $('models').value.split(/\n|,/).map((item) => item.trim()).filter(Boolean);
  for (const id of ['default-model', 'playground-model']) {
    const select = $(id); const current = id === 'default-model' ? selected || select.value : select.value || selected;
    select.replaceChildren();
    for (const model of models) { const option = document.createElement('option'); option.value = model; option.textContent = model; option.selected = model === current; select.append(option); }
  }
}

function renderAccessStatus() {
  if (!state.settings) return;
  const configured = state.settings.lmmock_api_key_configured;
  const authorized = Boolean(sessionStorage.getItem('lmmock-api-key'));
  $('access-status').textContent = configured ? (authorized ? t('accessOn') : t('accessNeeded')) : t('accessOff');
  $('access-key-button').classList.toggle('protected', configured && authorized);
  $('access-key-button').classList.toggle('needed', configured && !authorized);
}

async function loadSettings() {
  const settings = await api('/settings'); state.settings = settings;
  state.activeGroupId = state.activeGroupId || settings.active_group_id;
  $('models').value = settings.models.join('\n'); syncModelOptions(settings.default_model); $('default-model').value = settings.default_model;
  for (const operation of ['chat', 'completions', 'responses', 'messages']) $(`operation-${operation}`).checked = settings.enabled_operations.includes(operation);
  for (const option of $('playground-endpoint').options) option.disabled = !settings.enabled_operations.includes(option.value);
  if ($('playground-endpoint').selectedOptions[0]?.disabled) $('playground-endpoint').value = settings.enabled_operations[0];
  $('openai-forward').checked = Boolean(settings.forward_openai); $('openai-base').value = settings.openai_base_url || '';
  $('anthropic-forward').checked = Boolean(settings.forward_anthropic); $('anthropic-base').value = settings.anthropic_base_url || '';
  $('key-status').textContent = t('providerKeyStatus', { openai: settings.openai_api_key_configured ? t('keySet') : t('noKey'), anthropic: settings.anthropic_api_key_configured ? t('keySet') : t('noKey') });
  renderAccessStatus();
}

function openRequest(request) {
  $('request-dialog-title').textContent = `${request.provider} · ${request.operation} · ${request.group || ''} · ${request.status}`;
  $('request-detail').textContent = JSON.stringify(request.request ?? {}, null, 2); $('response-detail').textContent = JSON.stringify(request.response ?? {}, null, 2); $('request-dialog').showModal();
}

function renderRequests(requests) {
  const node = $('requests'); node.replaceChildren();
  if (!requests.length) { const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = t('noRequests'); node.append(empty); return; }
  for (const request of requests) {
    const row = document.createElement('button'); row.type = 'button'; row.className = 'request';
    const provider = document.createElement('span'); provider.className = 'request-provider'; provider.textContent = request.provider;
    const main = document.createElement('span'); main.className = 'request-main'; const title = document.createElement('strong'); title.textContent = `${request.operation} · ${request.group || ''} · ${request.rule || t('noMatch')}`;
    const input = document.createElement('small'); input.textContent = request.input || t('emptyInput'); main.append(title, input);
    const timing = document.createElement('span'); timing.className = 'request-time'; timing.textContent = `${request.status} · ${request.duration_ms}ms  ›`;
    row.append(provider, main, timing); row.addEventListener('click', () => openRequest(request)); node.append(row);
  }
}

async function loadRequests() { renderRequests(await api('/requests')); }

async function initialize() {
  try {
    await loadSettings(); state.groups = await api('/groups');
    if (!state.groups.some((group) => group.id === state.activeGroupId)) state.activeGroupId = state.groups[0].id;
    renderGroups(); await Promise.all([loadRules(), loadRequests()]);
  } catch (error) {
    if (error.status === 401) { $('access-key-dialog').showModal(); toast(t('apiKeyRequired')); }
    else toast(error.message);
  }
}

$('language-toggle').addEventListener('click', () => { state.language = state.language === 'en' ? 'zh' : 'en'; localStorage.setItem('lmmock-language', state.language); applyLanguage(); loadSettings().catch(() => {}); loadRequests().catch(() => {}); });
$('access-key-button').addEventListener('click', () => $('access-key-dialog').showModal());
$('open-access-key').addEventListener('click', () => $('access-key-dialog').showModal());
$('close-access-key-dialog').addEventListener('click', () => $('access-key-dialog').close());
$('access-key-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const key = $('access-key').value.trim();
  if (key) sessionStorage.setItem('lmmock-api-key', key); else sessionStorage.removeItem('lmmock-api-key');
  $('access-key').value = ''; $('access-key-dialog').close(); toast(t('apiKeySaved')); await initialize();
});

$('group-select').addEventListener('change', async () => {
  state.activeGroupId = Number($('group-select').value); state.activeRuleId = null; renderGroups(); setForm();
  try { await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: state.activeGroupId }) }); await loadRules(); } catch (error) { toast(error.message); }
});
$('new-group').addEventListener('click', () => { $('group-id').value = ''; $('group-name').value = ''; $('group-description').value = ''; $('group-dialog-title').textContent = t('createGroup'); $('delete-group').classList.add('hidden'); $('group-dialog').showModal(); });
$('edit-group').addEventListener('click', () => { const group = state.groups.find((item) => item.id === state.activeGroupId); $('group-id').value = group.id; $('group-name').value = group.name; $('group-description').value = group.description; $('group-dialog-title').textContent = t('editGroup'); $('delete-group').classList.remove('hidden'); $('group-dialog').showModal(); });
$('close-group-dialog').addEventListener('click', () => $('group-dialog').close());
$('group-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const id = $('group-id').value;
  try {
    const saved = await api(id ? `/groups/${id}` : '/groups', { method: id ? 'PUT' : 'POST', body: JSON.stringify({ name: $('group-name').value, description: $('group-description').value }) });
    state.groups = await api('/groups'); state.activeGroupId = saved.id; renderGroups(); await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: saved.id }) }); await loadRules(); $('group-dialog').close(); toast(t(id ? 'groupUpdated' : 'groupCreated'));
  } catch (error) { toast(error.message); }
});
$('delete-group').addEventListener('click', async () => {
  const id = Number($('group-id').value); if (!id || !window.confirm(t('groupDeleteConfirm'))) return;
  try { await api(`/groups/${id}`, { method: 'DELETE' }); state.groups = await api('/groups'); state.activeGroupId = state.groups[0].id; renderGroups(); await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: state.activeGroupId }) }); await loadRules(); $('group-dialog').close(); toast(t('groupDeleted')); } catch (error) { toast(error.message); }
});

$('new-rule').addEventListener('click', () => setForm()); $('match-type').addEventListener('change', updateFields); $('reply-type').addEventListener('change', updateFields);
$('rule-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    const type = $('reply-type').value; let reply;
    if (type === 'tool') reply = { tool_name: $('tool-name').value, arguments: JSON.parse($('arguments').value || '{}') };
    else if (type === 'error') reply = { status_code: Number($('error-status').value), message: $('error-message').value };
    else reply = { content: $('content').value };
    const payload = { name: $('name').value, enabled: $('enabled').checked, priority: Number($('priority').value), group_id: Number($('rule-group').value), scopes: [$('scope').value], match_type: $('match-type').value, match_value: $('match-value').value, reply_type: type, reply, delay_ms: Number($('delay').value) };
    const id = $('rule-id').value; const saved = await api(id ? `/rules/${id}` : '/rules', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    if (saved.group_id !== state.activeGroupId) { state.activeGroupId = saved.group_id; renderGroups(); }
    await loadRules(); setForm(state.rules.find((rule) => rule.id === saved.id) || null); toast(t(id ? 'ruleUpdated' : 'ruleCreated'));
  } catch (error) { toast(error instanceof SyntaxError ? t('invalidArguments') : error.message); } finally { submit.disabled = false; }
});
$('delete-rule').addEventListener('click', async () => { const id = $('rule-id').value; if (!id || !window.confirm(t('deleteConfirm'))) return; try { await api(`/rules/${id}`, { method: 'DELETE' }); await loadRules(); setForm(); toast(t('ruleDeleted')); } catch (error) { toast(error.message); } });

$('models').addEventListener('input', () => syncModelOptions($('default-model').value));
$('settings-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    const models = $('models').value.split(/\n|,/).map((item) => item.trim()).filter(Boolean);
    const enabledOperations = ['chat', 'completions', 'responses', 'messages'].filter((operation) => $(`operation-${operation}`).checked);
    await api('/settings', { method: 'PUT', body: JSON.stringify({ models, default_model: $('default-model').value, enabled_operations: enabledOperations, forward_openai: $('openai-forward').checked, openai_base_url: $('openai-base').value, forward_anthropic: $('anthropic-forward').checked, anthropic_base_url: $('anthropic-base').value }) });
    await loadSettings(); toast(t('settingsSaved'));
  } catch (error) { toast(error.message); } finally { submit.disabled = false; }
});

$('playground-send').addEventListener('click', async () => {
  const button = $('playground-send'); button.disabled = true; const started = performance.now();
  try {
    const endpoint = $('playground-endpoint').value; const input = $('playground-input').value; const model = $('playground-model').value;
    const body = endpoint === 'chat' ? { model, messages: [{ role: 'user', content: input }] } : endpoint === 'completions' ? { model, prompt: input } : endpoint === 'responses' ? { model, input } : { model, max_tokens: 128, messages: [{ role: 'user', content: input }] };
    const paths = { chat: '/v1/chat/completions', completions: '/v1/completions', responses: '/v1/responses', messages: '/v1/messages' };
    const response = await fetch(paths[endpoint], { method: 'POST', headers: { 'content-type': 'application/json', ...authHeaders(), 'x-lmmock-group': String(state.activeGroupId) }, body: JSON.stringify(body) });
    const data = await response.json(); $('playground-output').textContent = JSON.stringify(data, null, 2); $('playground-meta').textContent = `${response.status} · ${Math.round(performance.now() - started)}ms`; await loadRequests();
  } catch (error) { $('playground-output').textContent = error.message; $('playground-meta').textContent = t('requestFailed'); } finally { button.disabled = false; }
});

$('refresh-requests').addEventListener('click', () => loadRequests().catch((error) => toast(error.message)));
$('clear-requests').addEventListener('click', async () => { try { await api('/requests', { method: 'DELETE' }); await loadRequests(); toast(t('listCleared')); } catch (error) { toast(error.message); } });
$('close-request-dialog').addEventListener('click', () => $('request-dialog').close());
$('request-dialog').addEventListener('click', (event) => { if (event.target === $('request-dialog')) $('request-dialog').close(); });
for (const button of document.querySelectorAll('[data-copy]')) button.addEventListener('click', async () => { try { await navigator.clipboard.writeText(button.dataset.copy); toast(t('copied')); } catch (_) { toast(button.dataset.copy); } });

setForm(); applyLanguage(); initialize();
setInterval(() => loadRequests().catch(() => {}), 5000);
